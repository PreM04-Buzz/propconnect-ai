from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ai, appointments, auth, clients, health, leads, offers, properties, users
from app.core.config import check_production_settings, get_settings

settings = get_settings()
check_production_settings(settings)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")
api.include_router(health.router)
api.include_router(auth.router)
api.include_router(users.router)
api.include_router(clients.router)
api.include_router(properties.router)
api.include_router(leads.router)
api.include_router(appointments.router)
api.include_router(offers.router)
api.include_router(ai.router)
app.include_router(api)
