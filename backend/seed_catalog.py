from decimal import Decimal

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.delivery_region import DeliveryGovernorate
from backend.models.delivery_zone import DeliveryZone
from backend.models.order import OrderItem
from backend.models.product import Product


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
    ("DEMO - Red Rose Bouquet", "تجريبي - بوكيه ورد أحمر", "A classic red rose bouquet for a romantic gesture.", "بوكيه ورد أحمر كلاسيكي لمناسبة مميزة.", "roses", "anniversary", "799.00"),
    ("DEMO - White Rose Bouquet", "تجريبي - بوكيه ورد أبيض", "Elegant white roses in a soft seasonal arrangement.", "ورود بيضاء أنيقة بتنسيق موسمي هادئ.", "roses", "wedding", "899.00"),
    ("DEMO - Sunflower Bouquet", "تجريبي - بوكيه عباد الشمس", "Bright sunflowers arranged for a cheerful surprise.", "زهور عباد الشمس لتقديم مفاجأة مبهجة.", "bouquets", "congratulations", "749.00"),
    ("DEMO - Lily Arrangement", "تجريبي - تنسيق ليليوم", "A refined lily arrangement in a simple vase.", "تنسيق أنيق من زهور الليليوم في مزهرية بسيطة.", "arrangements", "thank-you", "1099.00"),
    ("DEMO - Gerbera Mix", "تجريبي - بوكيه جربيرا", "A colourful mix of fresh-looking gerberas.", "تشكيلة ملونة من زهور الجربيرا.", "bouquets", "birthday", "699.00"),
    ("DEMO - Tulip Bouquet", "تجريبي - بوكيه توليب", "Seasonal tulips gathered in a bright bouquet.", "زهور توليب موسمية مجمعة في بوكيه مشرق.", "flowers", "anniversary", "1199.00"),
    ("DEMO - Gypsophila Bouquet", "تجريبي - بوكيه جيبسوفيليا", "Airy gypsophila stems for a delicate gift.", "أغصان جيبسوفيليا رقيقة كهدية بسيطة.", "flowers", "just-because", "599.00"),
    ("DEMO - Orchid Arrangement", "تجريبي - تنسيق أوركيد", "A graceful orchid arrangement for a thoughtful occasion.", "تنسيق أوركيد أنيق لمناسبة مميزة.", "arrangements", "birthday", "1399.00"),
)

LEGACY_DEMO_NAMES = (
    "DEMO - Blush Peony Mix",
    "DEMO - White Lily Vase",
    "DEMO - Sunshine Gerberas",
    "DEMO - Lavender Garden",
    "DEMO - Peach Rose Box",
    "DEMO - Mixed Spring Bouquet",
    "DEMO - Pink Carnation Bunch",
)
DEMO_PRODUCT_NAMES = tuple(product[0] for product in DEMO_PRODUCTS) + LEGACY_DEMO_NAMES


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


def seed_demo_products(db: Session, *, app_env: str) -> None:
    if app_env not in {"development", "staging"}:
        raise ValueError("Demo products may only be seeded in development or staging")
    for index, (name, name_ar, description, description_ar, category, occasion, price) in enumerate(DEMO_PRODUCTS):
        existing = db.query(Product).filter(Product.name == name).one_or_none()
        if existing is None:
            existing = Product(name=name)
            db.add(existing)
        existing.name_ar = name_ar
        existing.description = f"DEMO SAMPLE; replace before launch. {description}"
        existing.description_ar = f"بيانات تجريبية؛ استبدلها قبل الإطلاق. {description_ar}"
        existing.price = Decimal(price)
        existing.active = True
        existing.image_url = None
        existing.category = category
        existing.occasion = occasion
        existing.featured = index % 3 == 0
        existing.best_seller = index in {0, 3, 5}


def seed_catalog(db: Session, *, app_env: str) -> None:
    seed_delivery_zones(db)


def remove_demo_products(db: Session) -> int:
    products = db.query(Product).filter(Product.name.in_(DEMO_PRODUCT_NAMES)).all()
    if not products:
        return 0
    product_ids = [product.id for product in products]
    referenced = db.query(OrderItem.product_id).filter(OrderItem.product_id.in_(product_ids)).first()
    if referenced is not None:
        raise ValueError("Demo products referenced by orders cannot be removed safely")
    for product in products:
        db.delete(product)
    return len(products)


def main() -> None:
    with SessionLocal() as db:
        seed_catalog(db, app_env="bootstrap")
        db.commit()


if __name__ == "__main__":
    main()