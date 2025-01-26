from app import create_app, db
from app.models import Shop

app = create_app()

shops = [
    {"id": 1, "name": "Магазин № 1", "location": "Пр. Строителей 132"},
    {"id": 2, "name": "Магазин № 2", "location": "Пр. Ленина 66/39"},
    {"id": 3, "name": "Магазин № 3", "location": "Пр. Строителей, 100"},
    {"id": 4, "name": "Магазин № 4", "location": ""},
]

with app.app_context():
    for shop in shops:
        existing_shop = Shop.query.get(shop["id"])
        if not existing_shop:
            new_shop = Shop(
                id=shop["id"], name=shop["name"], location=shop["location"])
            db.session.add(new_shop)
    db.session.commit()
    print("Магазины успешно добавлены в базу данных!")
