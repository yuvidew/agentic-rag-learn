from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.app_logging import configure_logging
from app.core.config import get_settings
from app.services.audit import init_db

configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
