import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.database import get_db
from backend.logging_utils import log_failure
from backend.payment_method import PaymentMethod
from backend.routers.admin import router as admin_router
from backend.routers.orders import router as orders_router
from backend.routers.products import router as products_router
from backend.settings import Settings


logger = logging.getLogger(__name__)
settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings.validate_runtime()
    logger.info("ToneFlowers API starting (environment=%s)", settings.app_env)
    if not settings.admin_api_key.get_secret_value():
        logger.warning("Admin routes are disabled until ADMIN_API_KEY is configured")
    yield
    logger.info("ToneFlowers API stopping")


class SafeErrorsMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        response_started = False

        async def tracked_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, tracked_send)
        except Exception as error:
            log_failure(logger, "Unexpected request failure", error)
            if response_started:
                # An already-sent response cannot be replaced. Let the server
                # close it, without logging the original sensitive exception.
                raise RuntimeError("Response interrupted by an internal server error") from None
            response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
            await response(scope, receive, send)


app = FastAPI(title="ToneFlowers API", lifespan=lifespan, debug=False)
app.add_middleware(SafeErrorsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-Admin-Key", "X-Requested-With"],
)
app.include_router(admin_router)
app.include_router(orders_router)
app.include_router(products_router)


@app.get("/public-config", tags=["config"])
def public_config() -> dict[str, object]:
    return {
        "whatsapp_number": settings.whatsapp_number,
        "vodafone_cash_number": settings.vodafone_cash_number,
        "supported_payment_methods": [
            PaymentMethod.vodafone_cash.value,
            PaymentMethod.cash_on_delivery.value,
        ],
    }


@app.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        log_failure(logger, "Database health check failed", error)
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}
