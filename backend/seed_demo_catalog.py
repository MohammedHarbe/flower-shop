from backend.database import SessionLocal
from backend.seed_catalog import seed_demo_products
from backend.settings import Settings


def main() -> None:
    settings = Settings()
    with SessionLocal() as db:
        seed_demo_products(db, app_env=settings.app_env)
        db.commit()


if __name__ == "__main__":
    main()