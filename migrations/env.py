from alembic import context
from sqlalchemy import create_engine, pool

from backend.database import Base
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.settings import Settings


target_metadata = Base.metadata


def run_migrations_online() -> None:
    engine = create_engine(Settings().database_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline migrations are not supported; use alembic upgrade head")
run_migrations_online()
