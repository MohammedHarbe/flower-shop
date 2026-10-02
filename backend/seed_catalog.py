from decimal import Decimal

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.delivery_region import DeliveryGovernorate
from backend.models.delivery_zone import DeliveryZone
import backend.models.order
from backend.models.product import Product
from backend.settings import Settings


DELIVERY_ZONES = (
    {
        "governorate": DeliveryGovernorate.cairo,
        "name_en": "Cairo",
        "name_ar": "القاهرة",
        "sort_order": 1,
    },
    {
        "governorate": DeliveryGovernorate.giza,
        "name_en": "Giza",
        "name_ar": "الجيزة",
        "sort_order": 2,
    },
)

DEMO_PRODUCTS = (
    ("DEMO - Red Rose Bouquet", "باقة ورد جوري أحمر تجريبية", "Classic Red Roses", "ورود حمراء كلاسيكية", "flowers", "anniversary", "850.00"),
    ("DEMO - Blush Peony Mix", "باقة بيوني وردية تجريبية", "Soft Blush Peonies", "زهور بيوني وردية ناعمة", "flowers", "birthday", "1250.00"),
    ("DEMO - White Lily Vase", "مزهرية زنبق أبيض تجريبية", "Elegant White Lilies", "زنابق بيضاء أنيقة", "arrangements", "thank-you", "990.00"),
    ("DEMO - Sunshine Gerberas", "باقة جربيرا بلون الشمس تجريبية", "Bright Yellow Gerberas", "زهور جربيرا صفراء مبهجة", "flowers", "congratulations", "720.00"),
    ("DEMO - Lavender Garden", "باقة حديقة بنفسجية تجريبية", "Seasonal Purple Blooms", "زهور موسمية بنفسجية", "bouquets", "just-because", "1080.00"),
    ("DEMO - Peach Rose Box", "صندوق ورد خوخي تجريبي", "Peach Roses in a Gift Box", "ورود خوخية في صندوق هدايا", "gifts", "birthday", "1150.00"),
    ("DEMO - Mixed Spring Bouquet", "باقة زهور الربيع المختلطة التجريبية", "A Colourful Seasonal Mix", "تشكيلة موسمية بألوان متنوعة", "bouquets", "get-well", "890.00"),
    ("DEMO - Pink Carnation Bunch", "باقة قرنفل وردي تجريبية", "Soft Pink Carnations", "زهور قرنفل وردية ناعمة", "flowers", "thank-you", "650.00"),
)


def seed_delivery_zones(db: Session) -> None:
    for zone_data in DELIVERY_ZONES:
        zone = (
            db.query(DeliveryZone)
            .filter(
                DeliveryZone.governorate == zone_data["governorate"],
                DeliveryZone.name_en == zone_data["name_en"],
            )
            .one_or_none()
        )
        if zone is None:
            zone = DeliveryZone(**zone_data, fee=Decimal("50.00"), active=True)
            db.add(zone)
        else:
            zone.name_ar = zone_data["name_ar"]
            zone.fee = Decimal("50.00")
            zone.active = True
            zone.sort_order = zone_data["sort_order"]


def seed_demo_products(db: Session) -> None:
    for index, (name, name_ar, description, description_ar, category, occasion, price) in enumerate(DEMO_PRODUCTS):
        existing = db.query(Product).filter(Product.name == name).one_or_none()
        if existing is not None:
            continue
        db.add(
            Product(
                name=name,
                name_ar=name_ar,
                description=f"Temporary demo listing; replace this sample before launch. {description}.",
                description_ar=f"منتج تجريبي مؤقت؛ استبدل هذه البيانات قبل الإطلاق. {description_ar}.",
                price=Decimal(price),
                stock=10,
                active=True,
                image_url=None,
                category=category,
                occasion=occasion,
                featured=index % 4 == 0,
                best_seller=index % 3 == 0,
            )
        )


def seed_catalog(db: Session, *, app_env: str) -> None:
    seed_delivery_zones(db)
    if app_env in {"development", "staging"}:
        seed_demo_products(db)


def main() -> None:
    settings = Settings()
    with SessionLocal() as db:
        seed_catalog(db, app_env=settings.app_env)
        db.commit()


if __name__ == "__main__":
    main()