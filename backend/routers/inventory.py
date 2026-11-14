import hashlib
import math
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from lib.dates import today_iso
from lib.db import db
from models.inventory import (
    ABCItem,
    DashboardResponse,
    ForecastItem,
    ForecastResponse,
    ImportProductsRequest,
    ImportProductsResponse,
    Movement,
    MovementCreate,
    Product,
    ProductCreate,
    Role,
    SupplierAlert,
    SupplierAlertProduct,
    UserLogin,
    UserOut,
)

router = APIRouter()
SESSION_COOKIE = "stokos_session"


def hash_password(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def public_user(document: dict) -> UserOut:
    return UserOut(
        id=document["id"],
        name=document["name"],
        email=document["email"],
        role=document["role"],
        last_access=document.get("last_access"),
    )


async def current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Sessão necessária")
    session = await db.sessions.find_one({"token": token})
    expires_at = session.get("expires_at", datetime.now(timezone.utc)) if session else datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not session or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sessão expirada")
    user = await db.users.find_one({"id": session["user_id"]})
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


async def admin_user(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores podem realizar esta ação")
    return user


# ---------------------------------------------------------------------------
# Forecast model: weighted moving average (WMA) of DAILY outgoing quantity
# with a bounded trend factor.
#   1. Build the daily series of "saida" quantities for the last WINDOW_DAYS
#      days (days without sales count as 0), ordered oldest -> newest.
#   2. WMA with linear weights 1..N: the most recent day weighs N, the oldest 1.
#   3. Trend factor = 1 + 0.2 * (mean(last 7 days) - mean(previous 21)) / mean(previous 21),
#      clamped to [0.8, 1.25] so a single atypical week cannot explode the forecast.
#   forecast_daily_demand = WMA * trend
# ---------------------------------------------------------------------------
WINDOW_DAYS = 28
TREND_RECENT_DAYS = 7
TREND_SENSITIVITY = 0.2
TREND_MIN, TREND_MAX = 0.8, 1.25
BACKTEST_DAYS = 7


def wma_trend_forecast(daily: list[float]) -> float:
    """Daily demand forecast from a daily series ordered oldest -> newest."""
    if not daily or not any(daily):
        return 0.0
    weights = range(1, len(daily) + 1)
    weighted = sum(quantity * weight for quantity, weight in zip(daily, weights)) / sum(weights)
    recent = daily[-TREND_RECENT_DAYS:]
    older = daily[:-TREND_RECENT_DAYS]
    recent_mean = sum(recent) / len(recent)
    older_mean = sum(older) / len(older) if older else recent_mean
    if older_mean > 0:
        trend = 1 + TREND_SENSITIVITY * (recent_mean - older_mean) / older_mean
    else:
        trend = TREND_MAX if recent_mean > 0 else 1.0
    trend = max(TREND_MIN, min(TREND_MAX, trend))
    return round(weighted * trend, 2)


def utc_day(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).date()


async def daily_outgoing(days_back: int) -> dict[str, dict[date, int]]:
    """{product_id: {day: total 'saida' quantity}} for the last `days_back` days."""
    start = datetime.now(timezone.utc) - timedelta(days=days_back + 1)
    documents = await db.movements.find({"type": "saida", "created_at": {"$gte": start}}).to_list(100000)
    result: dict[str, dict[date, int]] = {}
    for item in documents:
        per_day = result.setdefault(item["product_id"], {})
        day = utc_day(item["created_at"])
        per_day[day] = per_day.get(day, 0) + int(item["quantity"])
    return result


def series_ending(per_day: dict[date, int], end_day: date, length: int = WINDOW_DAYS) -> list[float]:
    """Daily series of `length` days ending at `end_day` (inclusive), oldest -> newest."""
    return [float(per_day.get(end_day - timedelta(days=offset), 0)) for offset in range(length - 1, -1, -1)]


def stock_status(stock: int, min_stock: int) -> str:
    if stock <= 0:
        return "Crítico"
    if stock <= min_stock:
        return "Baixo"
    if stock > min_stock * 4:
        return "Excesso"
    return "Saudável"


async def forecast_items(days: int) -> list[ForecastItem]:
    products = await db.products.find().sort("name", 1).to_list(1000)
    outgoing = await daily_outgoing(WINDOW_DAYS)
    today = datetime.now(timezone.utc).date()
    items: list[ForecastItem] = []
    for raw in products:
        product = Product(**raw)
        avg_daily = wma_trend_forecast(series_ending(outgoing.get(product.id, {}), today))
        demand = math.ceil(avg_daily * days)
        target_stock = math.ceil(avg_daily * 14) + product.min_stock
        reorder = max(0, target_stock - product.stock)
        days_of_stock = math.floor(product.stock / avg_daily) if avg_daily > 0 else None
        if product.stock <= 0 or (days_of_stock is not None and days_of_stock < 7):
            priority = "Urgente"
        elif reorder > 0:
            priority = "Normal"
        else:
            priority = "Baixa"
        items.append(
            ForecastItem(
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                category=product.category,
                stock=product.stock,
                avg_daily_demand=avg_daily,
                forecast_days=days,
                forecast_demand=demand,
                days_of_stock=days_of_stock,
                reorder_quantity=reorder,
                estimated_cost=round(reorder * product.unit_cost, 2),
                priority=priority,
                status=stock_status(product.stock, product.min_stock),
            )
        )
    return items


@router.post("/auth/login", response_model=UserOut)
async def login(payload: UserLogin, response: Response):
    user = await db.users.find_one({"email": payload.email.lower().strip(), "password_hash": hash_password(payload.password)})
    if not user:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(32)
    await db.sessions.insert_one({"token": token, "user_id": user["id"], "expires_at": now + timedelta(days=7)})
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_access": now}})
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 7)
    user["last_access"] = now
    return public_user(user)


@router.get("/auth/me", response_model=UserOut)
async def me(user: dict = Depends(current_user)):
    return public_user(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await db.sessions.delete_one({"token": token})
    response.delete_cookie(SESSION_COOKIE)


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(user: dict = Depends(current_user)):
    del user
    products = [Product(**item) for item in await db.products.find().to_list(1000)]
    forecasts = await forecast_items(7)
    movements = [Movement(**item) for item in await db.movements.find().sort("created_at", -1).to_list(8)]
    distribution = {"Saudável": 0, "Baixo": 0, "Crítico": 0, "Excesso": 0}
    categories: dict[str, dict[str, float]] = {}
    for product in products:
        state = stock_status(product.stock, product.min_stock)
        distribution[state] += 1
        if product.category not in categories:
            categories[product.category] = {"products": 0, "stock": 0, "minimum": 0, "value": 0}
        categories[product.category]["products"] += 1
        categories[product.category]["stock"] += product.stock
        categories[product.category]["minimum"] += product.min_stock
        categories[product.category]["value"] += product.stock * product.unit_cost
    # Backtest over the last BACKTEST_DAYS COMPLETE days (today is still in progress): "actual" is the
    # real total outgoing quantity that day; "forecast" is what the model predicted using ONLY data before it.
    outgoing_by_product = await daily_outgoing(WINDOW_DAYS + BACKTEST_DAYS + 1)
    today = datetime.now(timezone.utc).date()
    series = []
    for offset in range(BACKTEST_DAYS, 0, -1):
        day = today - timedelta(days=offset)
        actual = sum(per_day.get(day, 0) for per_day in outgoing_by_product.values())
        predicted = sum(
            wma_trend_forecast(series_ending(per_day, day - timedelta(days=1)))
            for per_day in outgoing_by_product.values()
        )
        series.append({"date": day.strftime("%d/%m"), "actual": int(actual), "forecast": int(round(predicted))})
    return DashboardResponse(
        total_inventory_value=round(sum(item.stock * item.unit_cost for item in products), 2),
        total_products=len(products),
        critical_stock_count=distribution["Crítico"] + distribution["Baixo"],
        forecast_shortage_count=sum(1 for item in forecasts if item.reorder_quantity > 0),
        turnover_rate=round(sum(item.avg_daily_demand for item in forecasts) / max(1, len(products)), 1),
        stock_distribution=distribution,
        category_summary=[{"category": key, **value} for key, value in categories.items()],
        demand_series=series,
        critical_products=[item for item in forecasts if item.priority == "Urgente"][:5],
        recent_movements=movements,
        as_of_date=today_iso(),
    )


@router.get("/products", response_model=list[Product])
async def list_products(user: dict = Depends(current_user)):
    del user
    documents = await db.products.find().sort("name", 1).to_list(1000)
    return [Product(**item) for item in documents]


@router.post("/products", response_model=Product)
async def create_product(payload: ProductCreate, user: dict = Depends(admin_user)):
    del user
    existing = await db.products.find_one({"sku": payload.sku.upper().strip()})
    if existing:
        raise HTTPException(status_code=409, detail="SKU já cadastrado")
    product_data = payload.model_dump()
    product_data["sku"] = payload.sku.upper().strip()
    product = Product(**product_data)
    await db.products.insert_one(product.model_dump())
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: str, user: dict = Depends(admin_user)):
    del user
    result = await db.products.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Produto não encontrado")


@router.get("/movements", response_model=list[Movement])
async def list_movements(user: dict = Depends(current_user)):
    del user
    documents = await db.movements.find().sort("created_at", -1).to_list(1000)
    return [Movement(**item) for item in documents]


@router.post("/movements", response_model=Movement)
async def create_movement(payload: MovementCreate, user: dict = Depends(current_user)):
    product_raw = await db.products.find_one({"id": payload.product_id})
    if not product_raw:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    product = Product(**product_raw)
    next_stock = product.stock
    if payload.type == "entrada":
        next_stock += payload.quantity
    elif payload.type == "saida":
        next_stock -= payload.quantity
        if next_stock < 0:
            raise HTTPException(status_code=422, detail="A saída não pode deixar o estoque negativo")
    else:
        next_stock = payload.quantity
    now = datetime.now(timezone.utc)
    movement = Movement(
        product_id=product.id,
        product_sku=product.sku,
        product_name=product.name,
        type=payload.type,
        quantity=payload.quantity,
        reason=payload.reason,
        user_name=user["name"],
        user_role=user["role"],
        stock_before=product.stock,
        stock_after=next_stock,
        sale_price_at_movement=product.sale_price,
        created_at=now,
    )
    # A conditional write rejects operations calculated from a stale balance.
    updated = await db.products.update_one(
        {"id": product.id, "stock": product.stock, "updated_at": product_raw.get("updated_at")},
        {"$set": {"stock": next_stock, "updated_at": now, "last_movement_id": movement.id}},
    )
    if not updated.matched_count:
        raise HTTPException(status_code=409, detail="O saldo mudou. Atualize e tente novamente.")
    try:
        await db.movements.insert_one(movement.model_dump())
    except Exception:
        # Preserve subsequent updates if another operation has already changed the product.
        await db.products.update_one(
            {"id": product.id, "last_movement_id": movement.id, "updated_at": now},
            {"$set": {"stock": product.stock, "updated_at": now}, "$unset": {"last_movement_id": ""}},
        )
        raise
    return movement


@router.get("/analytics/abc", response_model=list[ABCItem])
async def sales_abc(user: dict = Depends(current_user)):
    start = datetime.now(timezone.utc) - timedelta(days=90)
    products = await db.products.find({}, {"id": 1, "sku": 1, "name": 1, "sale_price": 1}).to_list(None)
    totals = {
        p["id"]: dict(sku=p["sku"], name=p["name"], units_sold=0, cents=0, estimated_units=0)
        for p in products
    }
    prices = {p["id"]: p["sale_price"] for p in products}
    async for row in db.movements.find({"type": "saida", "created_at": {"$gte": start}}):
        product_id = row["product_id"]
        item = totals.get(product_id)
        price = row.get("sale_price_at_movement")
        if item is None:
            if price is None:
                continue
            item = totals.setdefault(product_id, dict(
                sku=row["product_sku"], name=row["product_name"], units_sold=0, cents=0, estimated_units=0
            ))
        quantity = row["quantity"]
        if price is None:
            price = prices[product_id]
            item["estimated_units"] += quantity
        item["units_sold"] += quantity
        item["cents"] += quantity * round(price * 100)

    ordered = sorted(totals.values(), key=lambda item: (-item["cents"], item["sku"]))
    total = sum(item["cents"] for item in ordered)
    cumulative = 0
    result = []
    for item in ordered:
        cents = item["cents"]
        classification = "C"
        if cents:
            if cumulative * 100 < total * 80:
                classification = "A"
            elif cumulative * 100 < total * 95:
                classification = "B"
        cumulative += cents
        result.append(ABCItem(
            sku=item["sku"], name=item["name"], units_sold=item["units_sold"],
            sales_value=cents / 100, cumulative_percent=round(100 * cumulative / total, 2) if total else 0,
            classification=classification, estimated_units=item["estimated_units"],
        ))
    return result


@router.get("/forecast", response_model=ForecastResponse)
async def forecast(days: int = 7, user: dict = Depends(current_user)):
    del user
    if days not in {7, 15, 30, 60}:
        raise HTTPException(status_code=422, detail="Período deve ser 7, 15, 30 ou 60 dias")
    return ForecastResponse(days=days, model_name="Média móvel ponderada + tendência", generated_at=datetime.now(timezone.utc), items=await forecast_items(days))


@router.get("/alerts/suppliers", response_model=list[SupplierAlert])
async def supplier_alerts(user: dict = Depends(current_user)):
    """Products at or below their reorder point, grouped by supplier (most urgent first)."""
    del user
    products = [Product(**item) for item in await db.products.find().to_list(1000)]
    forecasts = {item.product_id: item for item in await forecast_items(7)}
    groups: dict[str, list[SupplierAlertProduct]] = {}
    for product in products:
        if product.stock > product.reorder_point:
            continue
        forecast_item = forecasts.get(product.id)
        suggested = max(
            forecast_item.reorder_quantity if forecast_item else 0,
            product.reorder_point - product.stock + product.min_stock,
            1,
        )
        urgent = product.stock <= product.min_stock or (forecast_item is not None and forecast_item.priority == "Urgente")
        groups.setdefault(product.supplier or "Fornecedor não informado", []).append(
            SupplierAlertProduct(
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                stock=product.stock,
                reorder_point=product.reorder_point,
                min_stock=product.min_stock,
                suggested_quantity=suggested,
                estimated_cost=round(suggested * product.unit_cost, 2),
                priority="Urgente" if urgent else "Normal",
            )
        )
    alerts = [
        SupplierAlert(
            supplier=supplier,
            product_count=len(items),
            urgent_count=sum(1 for item in items if item.priority == "Urgente"),
            total_estimated_cost=round(sum(item.estimated_cost for item in items), 2),
            products=sorted(items, key=lambda item: (item.priority != "Urgente", item.stock)),
        )
        for supplier, items in groups.items()
    ]
    return sorted(alerts, key=lambda alert: (-alert.urgent_count, -alert.product_count, alert.supplier))


@router.post("/import/products", response_model=ImportProductsResponse)
async def import_products(payload: ImportProductsRequest, user: dict = Depends(admin_user)):
    del user
    imported = 0
    updated = 0
    errors: list[str] = []
    for product_payload in payload.products:
        try:
            sku = product_payload.sku.upper().strip()
            existing = await db.products.find_one({"sku": sku})
            if existing:
                await db.products.update_one({"sku": sku}, {"$set": {**product_payload.model_dump(exclude={"sku"}), "sku": sku, "updated_at": datetime.now(timezone.utc)}})
                updated += 1
            else:
                product_data = product_payload.model_dump()
                product_data["sku"] = sku
                product = Product(**product_data)
                await db.products.insert_one(product.model_dump())
                imported += 1
        except Exception as exc:
            errors.append(f"{product_payload.sku}: {exc}")
    return ImportProductsResponse(imported=imported, updated=updated, errors=errors)
