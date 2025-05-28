from app import db
from datetime import datetime
from flask_bcrypt import Bcrypt
from flask_login import UserMixin


# Модель для магазинов

class Shop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    employees = db.relationship(
        'Employee', backref='shop', lazy=True)  # Односторонний backref


class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    hours_worked = db.Column(db.Integer, default=0)
    salary = db.Column(db.Integer, default=0)
    motivation = db.Column(db.Integer, default=0)
    total_salary = db.Column(db.Integer, default=0)
    month = db.Column(db.String(7), nullable=False,
                      default=lambda: datetime.now().strftime('%Y-%m'))


# Модель для доходов

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey(
        'shop.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    # Тип операции (например, продажа, ремонт)
    operation_type = db.Column(db.String(50), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)      # Наименование
    employee_id = db.Column(db.Integer, db.ForeignKey(
        'employee.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)               # Сумма
    notes = db.Column(db.Text, nullable=True)                  # Заметки

    shop = db.relationship('Shop', backref=db.backref(
        'incomes', lazy=True, cascade='all, delete-orphan'))
    employee = db.relationship(
        'Employee', backref=db.backref('incomes', lazy=True))


# Модель для расходов


class Workday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey(
        'employee.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    worked = db.Column(db.Boolean, default=False)


class Return(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey(
        'employee.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)  # Сумма возврата
    notes = db.Column(db.Text, nullable=True)  # Заметки

    shop = db.relationship('Shop', backref=db.backref('returns', lazy=True))
    employee = db.relationship(
        'Employee', backref=db.backref('returns', lazy=True))


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Категория расходов
    amount = db.Column(db.Float, nullable=False)  # Сумма расходов
    notes = db.Column(db.Text, nullable=True)  # Заметки

    shop = db.relationship('Shop', backref=db.backref('expenses', lazy=True))

# flask db migrate -m "Исправление"
# flask db upgrade


class SalesReturn(db.Model):
    __tablename__ = 'sales_returns'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, nullable=False)  # Привязка к магазину
    sale = db.Column(db.String(255), nullable=True)  # Продажа (текст)
    return_item = db.Column(db.String(255), nullable=True)  # Возврат (текст)
    retail_sale_amount = db.Column(
        db.Float, nullable=True)  # Сумма продаж в розницу
    # Сумма продаж по закупочной цене
    wholesale_sale_amount = db.Column(db.Float, nullable=True)
    return_amount = db.Column(db.Float, nullable=True)  # Сумма возвратов
    date = db.Column(db.Date, default=datetime.utcnow)  # Дата
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow)  # Время создания


class ShopExpense(db.Model):
    __tablename__ = 'shop_expenses'
    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, nullable=False)  # Привязка к магазину
    purchase_desc = db.Column(
        db.String(255), nullable=True)  # Описание закупки
    purchase = db.Column(db.Float, nullable=True)  # Сумма закупки
    store_needs_desc = db.Column(
        db.String(255), nullable=True)  # Описание нужд магазина
    store_needs = db.Column(db.Float, nullable=True)  # Сумма нужд магазина
    salary_desc = db.Column(db.String(255), nullable=True)  # Описание зарплаты
    salary = db.Column(db.Float, nullable=True)  # Сумма зарплаты
    rent_desc = db.Column(db.String(255), nullable=True)  # Описание аренды
    rent = db.Column(db.Float, nullable=True)  # Сумма аренды
    repair_desc = db.Column(db.String(255), nullable=True)  # Описание ремонта
    repair = db.Column(db.Float, nullable=True)  # Сумма ремонта
    marketing_desc = db.Column(
        db.String(255), nullable=True)  # Описание маркетинга
    marketing = db.Column(db.Float, nullable=True)  # Сумма маркетинга
    date = db.Column(db.Date, default=datetime.utcnow)  # Дата


# авторизация
bcrypt = Bcrypt()


class User(UserMixin, db.Model):  # Наследуемся от UserMixin
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    # Уровень доступа ("admin", "shop_manager")
    access_level = db.Column(db.String(50), nullable=False)
    # NULL = полный доступ, иначе ID магазина
    shop_id = db.Column(db.Integer, nullable=True)

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
