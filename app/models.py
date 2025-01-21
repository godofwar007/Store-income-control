from app import db

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
    shop_id = db.Column(db.Integer, db.ForeignKey(
        'shop.id'), nullable=False)  # Ссылка на Shop
    hours_worked = db.Column(db.Integer, default=0)
    salary = db.Column(db.Float, nullable=False)
    motivation = db.Column(db.Float, default=0)


# Модель для доходов


class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)

# Модель для расходов


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.Date, nullable=False)
    shop_id = db.Column(db.Integer, db.ForeignKey('shop.id'), nullable=False)
