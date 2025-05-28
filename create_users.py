from app import create_app, db
from app.models import User, bcrypt

app = create_app()

with app.app_context():
    users = [
        {"username": "shop1_manager", "password": "Sun12345",
            "access_level": "shop_manager", "shop_id": 1},
        {"username": "shop2_manager", "password": "Tree2023",
            "access_level": "shop_manager", "shop_id": 2},
        {"username": "shop3_manager", "password": "Sky9876",
            "access_level": "shop_manager", "shop_id": 3},
        {"username": "shop4_manager", "password": "Moon4567",
            "access_level": "shop_manager", "shop_id": 4},
        {"username": "mariupol_shop", "password": "Triathlon2025",
            "access_level": "admin", "shop_id": None}
    ]

    # Добавление пользователей в базу данных
    for user_data in users:
        password_hash = bcrypt.generate_password_hash(
            user_data['password']).decode('utf-8')
        user = User(
            username=user_data['username'],
            password_hash=password_hash,
            access_level=user_data['access_level'],
            shop_id=user_data['shop_id']
        )
        db.session.add(user)

    # Сохранение транзакции
    db.session.commit()
    print("Пользователи добавлены!")
