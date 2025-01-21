from flask import Flask, render_template, redirect, url_for, request
from app.models import db, Shop, Employee, Income, Expense
from app.forms import EmployeeForm, ShopForm, IncomeForm  # Импорт формы
from datetime import datetime

shops = [
    {"id": 1, "address": "Пр. Строителей 132", "name": "Магазин № 1"},
    {"id": 2, "address": "Пр. Ленина 66/39", "name": "Магазин № 2"},
    {"id": 3, "address": "Пр. Строителей, 100", "name": "Магазин № 3"},
    {"id": 4, "address": "Пр. Строителей", "name": "Магазин № 4"}
]


def init_routes(app: Flask):

    @app.route('/add_employee', methods=['GET', 'POST'])
    def add_employee():
        form = EmployeeForm()
        form.shop_id.choices = [(shop["id"], shop["name"]) for shop in shops]

        if form.validate_on_submit():
            new_employee = Employee(
                name=form.name.data,
                shop_id=form.shop_id.data,
                hours_worked=form.hours_worked.data,
                salary=form.salary.data,
                motivation=form.motivation.data
            )
            db.session.add(new_employee)
            db.session.commit()
            return redirect(url_for('employees'))
        return render_template('add_employee.html', form=form)

    @app.route('/add_shop', methods=['GET', 'POST'])
    def add_shop():
        form = ShopForm()
        if form.validate_on_submit():
            new_shop = Shop(name=form.name.data, location=form.location.data)
            db.session.add(new_shop)
            db.session.commit()
            return redirect(url_for('shops'))
        return render_template('add_shop.html', form=form)

    @app.route('/')
    def index():
        # Получаем данные из базы
        total_income = db.session.query(
            db.func.sum(Income.amount)).scalar() or 0
        total_expenses = db.session.query(
            db.func.sum(Expense.amount)).scalar() or 0
        total_profit = total_income - total_expenses
        shops = [
            {"id": 1, "address": "Пр. Строителей 132", "name": "Магазин № 1"},
            {"id": 2, "address": "Пр. Ленина 66/39", "name": "Магазин № 2"},
            {"id": 3, "address": "Пр. Строителей, 100", "name": "Магазин № 3"},
            {"id": 4, "address": "Пр. Строителей", "name": "Магазин № 4"}
        ]
    # Данные для кнопок магазинов

        return render_template('index.html', shops=shops, total_income=total_income, total_expenses=total_expenses, total_profit=total_profit)

    @app.route('/shop/<int:shop_id>/income', methods=['GET', 'POST'])
    def shop_income(shop_id):
        shop = Shop.query.get_or_404(shop_id)
        form = IncomeForm()
        if form.validate_on_submit():
            new_income = Income(
                amount=form.amount.data,
                description=form.description.data,
                date=form.date.data,
                shop_id=shop_id
            )
            db.session.add(new_income)
            db.session.commit()
            return redirect(url_for('shop_income', shop_id=shop_id))
        incomes = Income.query.filter_by(shop_id=shop_id).all()
        return render_template('income.html', shop=shop, incomes=incomes, form=form)

    @app.route('/employees', methods=['GET', 'POST'])
    def employees():
        # Получение текущего месяца
        current_month = datetime.now().strftime('%Y-%m')
        selected_month = request.args.get('month', current_month)

    # Фильтрация сотрудников по месяцу (здесь предполагается, что у сотрудника есть поле даты)
        # Вы можете добавить логику фильтрации по дате, если нужно
        employees = Employee.query.all()

    # Подсчёт общей суммы заработной платы
        total_salary = sum((emp.salary or 0) + (emp.motivation or 0)
                           for emp in employees)

        return render_template(
            'employees.html',
            employees=employees,
            selected_month=selected_month,
            total_salary=total_salary
        )

    @app.route('/employee/<int:employee_id>/update', methods=['POST'])
    def update_employee(employee_id):
        employee = Employee.query.get_or_404(employee_id)
        form = EmployeeForm(obj=employee)
        form.shop_id.choices = [(shop.id, shop.name)
                                for shop in Shop.query.all()]  # Установка магазинов

        if form.validate_on_submit():
            employee.name = form.name.data
            employee.shop_id = form.shop_id.data
            employee.hours_worked = form.hours_worked.data
            employee.salary = form.salary.data
            employee.motivation = form.motivation.data
            db.session.commit()
            return redirect(url_for('employees'))
        return render_template('edit_employee.html', form=form, employee=employee)

    @app.route('/employee/<int:employee_id>/delete', methods=['POST'])
    def delete_employee(employee_id):
        employee = Employee.query.get_or_404(employee_id)
        db.session.delete(employee)
        db.session.commit()
        return redirect(url_for('employees'))

    @app.route('/shop/<int:shop_id>/employees', methods=['GET'])
    def shop_employees(shop_id):
        # Получаем магазин по ID
        shop = Shop.query.get_or_404(shop_id)

    # Получаем сотрудников этого магазина
        employees = Employee.query.filter_by(shop_id=shop_id).all()

    # Вычисляем общую сумму зарплат сотрудников магазина
        total_salary = sum((emp.salary or 0) + (emp.motivation or 0)
                           for emp in employees)

        return render_template(
            'shop_employees.html',
            shop=shop,
            employees=employees,
            total_salary=total_salary
        )
