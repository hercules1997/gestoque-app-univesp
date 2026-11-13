import asyncio
import hashlib
import random
import uuid
from datetime import datetime, timedelta, timezone

from lib.db import db, ensure_indexes


def password_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def seed() -> None:
    await ensure_indexes()
    users = [
        {"id": "user-admin-demo", "name": "Rafael Luiz", "email": "admin@stokos.demo", "password_hash": password_hash("Admin123!"), "role": "admin", "last_access": None},
        {"id": "user-operator-demo", "name": "Rafael Lima", "email": "operador@stokos.demo", "password_hash": password_hash("Operador123!"), "role": "operator", "last_access": None},
    ]
    for user in users:
        await db.users.update_one({"id": user["id"]}, {"$set": user}, upsert=True)
    products = [
        {"id": "prod-fone", "sku": "ELEC-001", "name": "Fone Bluetooth Pulse", "category": "Eletrônicos", "unit_cost": 48.9, "sale_price": 119.9, "stock": 6, "min_stock": 10, "reorder_point": 14, "supplier": "Tech Distribuidora"},
        {"id": "prod-camiseta", "sku": "VEST-014", "name": "Camiseta Algodão Basic", "category": "Vestuário", "unit_cost": 22.5, "sale_price": 59.9, "stock": 84, "min_stock": 24, "reorder_point": 35, "supplier": "Moda Sul"},
        {"id": "prod-oleo", "sku": "AUTO-220", "name": "Óleo Motor 5W30", "category": "Autopeças", "unit_cost": 31.7, "sale_price": 74.9, "stock": 18, "min_stock": 12, "reorder_point": 20, "supplier": "Auto Center Brasil"},
        {"id": "prod-cafe", "sku": "ALIM-008", "name": "Café Torrado 500g", "category": "Alimentos", "unit_cost": 11.2, "sale_price": 22.9, "stock": 0, "min_stock": 18, "reorder_point": 30, "supplier": "Armazém Central"},
        {"id": "prod-cabo", "sku": "ELEC-044", "name": "Cabo USB-C Reforçado", "category": "Eletrônicos", "unit_cost": 9.8, "sale_price": 29.9, "stock": 46, "min_stock": 15, "reorder_point": 24, "supplier": "Tech Distribuidora"},
        {"id": "prod-jaqueta", "sku": "VEST-031", "name": "Jaqueta Corta-Vento", "category": "Vestuário", "unit_cost": 86, "sale_price": 189.9, "stock": 9, "min_stock": 5, "reorder_point": 8, "supplier": "Moda Sul"},
    ]
    now = datetime.now(timezone.utc)
    for product in products:
        product["created_at"] = now - timedelta(days=90)
        product["updated_at"] = now
        await db.products.update_one({"id": product["id"]}, {"$set": product}, upsert=True)
    # Demo history: 60 days of daily sales per product, reproducible (fixed seed).
    # Each run replaces only the seed-generated rows, never the user's own movements.
    seed_reasons = ["Histórico de vendas", "Compra do fornecedor"]
    await db.movements.delete_many({"reason": {"$in": seed_reasons}})
    # product_id: (base units/day, total trend over the 60 days: +0.4 = +40% by today)
    demand_profile = {
        "prod-fone": (0.7, 0.6),        # rising demand
        "prod-camiseta": (1.6, 0.0),    # stable
        "prod-oleo": (0.8, 0.1),
        "prod-cafe": (2.0, 0.2),
        "prod-cabo": (0.9, 0.0),
        "prod-jaqueta": (0.6, -0.5),    # falling (end of season)
    }
    rng = random.Random(42)
    product_map = {row["id"]: row for row in products}
    history_days = 60
    rows = []
    for product_id, (base, trend) in demand_profile.items():
        product = product_map[product_id]
        for days_ago in range(history_days, 0, -1):
            day = now - timedelta(days=days_ago)
            progress = (history_days - days_ago) / history_days
            rate = base * (1 + trend * progress) * (1.35 if day.weekday() >= 5 else 1.0)
            quantity = max(0, round(rng.gauss(rate, rate ** 0.5)))
            if quantity:
                rows.append((product, "saida", quantity, "Histórico de vendas", day.replace(hour=rng.randint(9, 19), minute=rng.randint(0, 59))))
            if days_ago % 21 == 0:
                rows.append((product, "entrada", max(10, round(base * 21)), "Compra do fornecedor", day.replace(hour=8, minute=0)))
    for product, movement_type, quantity, reason, created_at in rows:
        await db.movements.insert_one({
            "id": str(uuid.uuid4()), "product_id": product["id"], "product_sku": product["sku"], "product_name": product["name"],
            "type": movement_type, "quantity": quantity, "reason": reason, "user_name": "Rafael Luiz", "user_role": "admin",
            "created_at": created_at,
        })
    print(f"Seed concluído: {len(products)} produtos, {len(rows)} movimentações históricas")


if __name__ == "__main__":
    asyncio.run(seed())