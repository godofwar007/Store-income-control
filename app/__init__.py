import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
import logging

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Загружаем переменные окружения
load_dotenv()

# Инициализация базы данных
db = SQLAlchemy()
migrate = Migrate()

# Инициализация Flask-Login
login_manager = LoginManager()


def create_app():
    # Инициализация приложения Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "4815162342")

    # Подключение базы данных
    db.init_app(app)
    migrate.init_app(app, db)

    # Настройка Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'  # Указать маршрут для страницы входа

    # Регистрация маршрутов
    from .routes import init_routes
    init_routes(app)
    with app.app_context():
        from app import models

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User  # Импорт модели пользователя
    return User.query.get(int(user_id))
