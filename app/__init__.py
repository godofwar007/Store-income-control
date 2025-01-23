import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Загружаем переменные окружения
load_dotenv()

# Инициализация базы данных
db = SQLAlchemy()
migrate = Migrate()


def create_app():
    # Инициализация приложения Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "4815162342")
    # Подключение базы данных
    db.init_app(app)
    migrate.init_app(app, db)

    # Регистрация маршрутов
    from .routes import init_routes
    init_routes(app)
    with app.app_context():
        from app import models
    return app
