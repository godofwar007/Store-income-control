from app import db
from datetime import datetime
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
    # Наименование товара
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
