from backend.database import SessionLocal
from backend.seed_catalog import remove_demo_products


def main() -> None:
    with SessionLocal() as db:
        removed = remove_demo_products(db)
        db.commit()
        print(f"Removed {removed} demo products")


if __name__ == "__main__":
    main()