import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime
from routers.inventory import router as inventory_router


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
from lib.db import client, db, ensure_indexes


async def migrate_demo_emails() -> None:
    for role in ("admin", "operator"):
        account = f"{role}@gestoque.com" if role == "admin" else "operador@gestoque.com"
        old_email = account.replace("@gestoque.com", "@stokos.demo")
        await db.users.update_one(
            {"id": f"user-{role}-demo", "email": old_email, "role": role},
            {"$set": {"email": account}},
        )


async def seed_if_empty() -> None:
    """A fresh database (e.g. the first production deploy) gets the demo users, products and history.
    Never runs when users already exist, so real data is never overwritten."""
    try:
        await migrate_demo_emails()
        if await db.users.count_documents({}) == 0:
            from seed import seed
            await seed()
            logging.getLogger(__name__).info("Empty database: demo data seeded")
    except Exception as exc:  # never block boot on seeding
        logging.getLogger(__name__).error("seed_if_empty failed: %s", exc)


# Startup runs before the yield, shutdown after it. Add your own setup/teardown here.
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.index_task = asyncio.create_task(ensure_indexes())  # background: a big index build must not block boot
    app.state.seed_task = asyncio.create_task(seed_if_empty())
    yield
    client.close()


# Create the main app without a prefix
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Gestoque API", "status": "online"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.model_dump())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

api_router.include_router(inventory_router)

# Include the router in the main app as the final registration statement.
app.include_router(api_router)

static_dir = ROOT_DIR / "static"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
