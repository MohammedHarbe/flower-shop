from alembic import context
from sqlalchemy import create_engine, pool

from backend.database import Base
from backend.models.order import Order, OrderItem
from backend.models.product import Product
from backend.settings import Settings


target_metadata = Base.metadata


def migrate_connection(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=connection.dialect.name == "sqlite",
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Tests supply a connection to their own temporary schema/database.
    connection = context.config.attributes.get("connection")
    if connection is not None:
        migrate_connection(connection)
        return
    engine = create_engine(Settings().database_url, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            migrate_connection(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline migrations are not supported; use alembic upgrade head")
run_migrations_online()
