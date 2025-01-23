from flask import Flask, render_template, redirect, url_for, request, jsonify
from app.models import db, Shop, Employee, Income, Expense, Workday, Return
from app.forms import EmployeeForm, ShopForm, IncomeForm  # Импорт формы
from datetime import datetime
from calendar import monthrange
from sqlalchemy import text


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
        # Заполняем варианты магазинов
        form.shop_id.choices = [(shop.id, shop.name)
                                for shop in Shop.query.all()]

        if form.validate_on_submit():
            current_month = datetime.now().strftime('%Y-%m')
            selected_month = request.args.get('month', current_month)

            new_employee = Employee(
                name=form.name.data,
                shop_id=form.shop_id.data,
                hours_worked=form.hours_worked.data,
                salary=form.salary.data,
                motivation=form.motivation.data,
                total_salary=form.total_salary.data,
                month=selected_month
            )

            try:
                db.session.add(new_employee)
                db.session.commit()
                print(f"Добавлен новый сотрудник для месяца {selected_month}.")
            except Exception as e:
                print(f"Ошибка при добавлении: {e}")
                db.session.rollback()
                return {"message": "Ошибка при добавлении сотрудника"}, 500

            # Редирект на страницу сотрудников конкретного магазина
            shop_id = form.shop_id.data
            return redirect(url_for('shop_employees', shop_id=shop_id))

        return render_template('add_employee.html', form=form)

    @app.route('/')
    def index():
        # Получаем параметры фильтрации
        start_date = request.args.get('start_date', datetime.now().strftime(
            '%Y-%m-01'))  # Первый день текущего месяца
        end_date = request.args.get(
            'end_date', datetime.now().strftime('%Y-%m-%d'))  # Текущая дата

        # Фильтрация доходов, расходов и зарплат по дате
        total_income = db.session.query(
            db.func.sum(Income.amount)
        ).filter(Income.date.between(start_date, end_date)).scalar() or 0

        total_expenses = db.session.query(
            db.func.sum(Expense.amount)
        ).filter(Expense.date.between(start_date, end_date)).scalar() or 0

        total_salary = db.session.query(
            db.func.sum(Employee.total_salary)
        ).scalar() or 0

        # Учитываем зарплату в общих расходах
        total_expenses += total_salary

        # Общая прибыль
        total_profit = total_income - total_expenses

        # Данные для кнопок магазинов
        shops = [
            {"id": 1, "address": "Пр. Строителей 132", "name": "Магазин № 1"},
            {"id": 2, "address": "Пр. Ленина 66/39", "name": "Магазин № 2"},
            {"id": 3, "address": "Пр. Строителей, 100", "name": "Магазин № 3"},
            {"id": 4, "address": "Пр. Строителей", "name": "Магазин № 4"}
        ]

        return render_template(
            'index.html',
            shops=shops,
            total_income=total_income,
            total_expenses=total_expenses,
            total_profit=total_profit,
            total_salary=total_salary,
            start_date=start_date,
            end_date=end_date
        )

    @app.route('/incomes', methods=['GET'])
    def all_incomes():
        # Фильтрация по месяцу или диапазону дат
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date and end_date:
            incomes = Income.query.filter(
                Income.date.between(start_date, end_date)).all()
        elif start_date:
            incomes = Income.query.filter(Income.date >= start_date).all()
        elif end_date:
            incomes = Income.query.filter(Income.date <= end_date).all()
        else:
            incomes = Income.query.all()

        return render_template('incomes.html', incomes=incomes)

    @app.route('/employees', methods=['GET'])
    def employees():
        # Получаем текущий месяц
        current_month = datetime.now().strftime('%Y-%m')
        selected_month = request.args.get(
            'month', current_month)  # Месяц из формы или текущий

        # Фильтруем сотрудников по выбранному месяцу
        employees = Employee.query.filter_by(month=selected_month).all()

        # Подсчет общей зарплаты за выбранный месяц
        total_salary = sum(employee.total_salary for employee in employees)

        return render_template(
            'employees.html',
            employees=employees,
            selected_month=selected_month,
            current_month=current_month,
            total_salary=total_salary
        )

    @app.route('/employee/<int:employee_id>/delete', methods=['POST'])
    def delete_employee(employee_id):
        employee = Employee.query.get_or_404(employee_id)
        shop_id = employee.shop_id  # Получаем ID магазина до удаления

        try:
            db.session.delete(employee)
            db.session.commit()
            print(f"Сотрудник ID {employee_id} успешно удалён.")
        except Exception as e:
            print(f"Ошибка при удалении сотрудника: {e}")
            db.session.rollback()
            return {"message": "Ошибка при удалении сотрудника"}, 500

        # Редирект на страницу сотрудников магазина
        return redirect(url_for('shop_employees', shop_id=shop_id))

    @app.route('/shop/<int:shop_id>/employees', methods=['GET'])
    def shop_employees(shop_id):
        # Получаем магазин по его ID
        shop = Shop.query.get_or_404(shop_id)

        # Получаем текущий месяц или выбранный
        current_month = datetime.now().strftime('%Y-%m')
        selected_month = request.args.get('month', current_month)

        # Фильтруем сотрудников по магазину и месяцу
        employees = Employee.query.filter_by(
            shop_id=shop_id, month=selected_month).all()

        # Суммируем зарплаты сотрудников за выбранный месяц
        total_salary = sum(
            employee.total_salary or 0 for employee in employees)

        # Передаем данные в шаблон
        return render_template(
            'shop_employees.html',
            shop=shop,
            employees=employees,
            total_salary=total_salary,
            selected_month=selected_month,
            current_month=current_month
        )

    @app.route('/employee/<int:employee_id>/update', methods=['POST'])
    def update_employee(employee_id):
        employee = Employee.query.get_or_404(employee_id)
        data = request.form

        try:
            # Обновляем данные сотрудника
            employee.name = data.get('name', employee.name)
            employee.hours_worked = int(data.get('hours_worked', 0) or 0)
            employee.salary = int(data.get('salary', 0) or 0)
            employee.motivation = int(data.get('motivation', 0) or 0)
            employee.total_salary = int(data.get('total_salary', 0) or 0)

            # Обновляем месяц, если передан в запросе
            selected_month = request.args.get('month')
            if selected_month:
                employee.month = selected_month

            db.session.commit()
            print(f"Сотрудник ID {employee_id} успешно обновлён.")
        except Exception as e:
            print(f"Ошибка при сохранении: {e}")
            db.session.rollback()
            return {"message": "Ошибка при сохранении данных"}, 500

        # Редирект на страницу сотрудников магазина
        return redirect(url_for('shop_employees', shop_id=employee.shop_id))

    @app.route('/employee/<int:employee_id>/workdays', methods=['GET', 'POST'])
    def employee_workdays(employee_id):

        employee = Employee.query.get_or_404(employee_id)
        selected_month = request.args.get(
            'month', datetime.now().strftime('%Y-%m'))
        year, month = map(int, selected_month.split('-'))

        # Генерируем список дней месяца
        days_in_month = monthrange(year, month)[1]
        days = [
            f"{year}-{month:02d}-{day:02d}" for day in range(1, days_in_month + 1)]

        # Получаем рабочие дни из базы
        workdays = {workday.date.strftime('%Y-%m-%d'): workday.worked
                    for workday in Workday.query.filter_by(employee_id=employee.id).filter(
                        db.extract('year', Workday.date) == year,
                        db.extract('month', Workday.date) == month
        ).all()}

        if request.method == 'POST':
            submitted_workdays = request.form.getlist('workdays')

            for day in days:
                worked = day in submitted_workdays
                workday = Workday.query.filter_by(
                    employee_id=employee.id, date=day).first()

                if not workday:
                    workday = Workday(employee_id=employee.id, date=day)
                    db.session.add(workday)

                workday.worked = worked

            db.session.commit()
            return redirect(url_for('employee_workdays', employee_id=employee.id, month=selected_month))

        return render_template(
            'employee_workdays.html',
            employee=employee,
            days=days,
            selected_month=selected_month,
            workdays=workdays
        )

    @app.route('/shop/<int:shop_id>/incomes', methods=['GET', 'POST'])
    def shop_incomes(shop_id):
        shop = Shop.query.get_or_404(shop_id)
        current_date = datetime.now().strftime('%Y-%m-%d')
        if request.method == 'POST':
            data = request.form
            print("Полученные данные:", data)

            # Если это добавление новой записи
            if 'new_record' in data:
                try:
                    # Проверка и обработка данных
                    date = data.get('new_date')
                    if not date:
                        date = datetime.utcnow().date()

                    operation_type = data.get('new_operation_type')
                    if not operation_type:
                        raise ValueError("Тип операции не может быть пустым.")

                    item_name = data.get('new_item_name')
                    if not item_name:
                        raise ValueError("Наименование не может быть пустым.")

                    employee_id = data.get('new_employee_id')
                    if not employee_id or not employee_id.isdigit():
                        raise ValueError("Некорректный ID сотрудника.")

                    amount = data.get('new_amount')
                    if not amount or not amount.replace('.', '', 1).isdigit():
                        raise ValueError("Сумма должна быть числом.")

                    # Создаем новую запись
                    new_income = Income(
                        shop_id=shop_id,
                        date=date,
                        operation_type=operation_type,
                        item_name=item_name,
                        employee_id=int(employee_id),
                        amount=float(amount),
                        notes=data.get('new_notes')
                    )
                    db.session.add(new_income)
                    db.session.commit()
                    print("Новая запись успешно добавлена.")
                except ValueError as ve:
                    print(f"Ошибка при добавлении записи: {ve}")
                    return {"message": str(ve)}, 400
                except Exception as e:
                    print(f"Ошибка при добавлении записи: {e}")
                    db.session.rollback()
                    return {"message": "Ошибка при добавлении записи"}, 500

            return redirect(url_for('shop_incomes', shop_id=shop_id))

        # Фильтрация записей по датам
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if start_date and end_date:
            incomes = Income.query.filter(
                Income.shop_id == shop_id, Income.date.between(start_date, end_date)).all()
        elif start_date:
            incomes = Income.query.filter(
                Income.shop_id == shop_id, Income.date >= start_date).all()
        elif end_date:
            incomes = Income.query.filter(
                Income.shop_id == shop_id, Income.date <= end_date).all()
        else:
            incomes = Income.query.filter_by(shop_id=shop_id).all()

        # Общая сумма доходов
        total_amount = sum(income.amount for income in incomes)

        return render_template(
            'shop_incomes.html',
            shop=shop,
            incomes=incomes,
            employees=Employee.query.filter_by(shop_id=shop_id).all(),
            total_amount=total_amount,
            current_date=current_date
        )

    @app.route('/shop/<int:shop_id>/returns', methods=['GET', 'POST'])
    def shop_returns(shop_id):
        shop = Shop.query.get_or_404(shop_id)

        # Фильтрация по датам
        start_date = request.args.get(
            'start_date', datetime.now().strftime('%Y-%m-01'))
        end_date = request.args.get(
            'end_date', datetime.now().strftime('%Y-%m-%d'))

        returns = Return.query.filter(
            Return.shop_id == shop_id,
            Return.date.between(start_date, end_date)
        ).all()

        if request.method == 'POST':
            data = request.form
            if 'new_record' in data:
                try:
                    date = data.get(
                        'new_date', datetime.utcnow().strftime('%Y-%m-%d'))
                    item_name = data.get('new_item_name')
                    employee_id = data.get('new_employee_id')
                    amount = data.get('new_amount')
                    notes = data.get('new_notes')

                    if not item_name:
                        raise ValueError(
                            "Наименование товара не может быть пустым.")
                    if not employee_id:
                        raise ValueError("Не выбран сотрудник.")
                    if not amount or not amount.replace('.', '', 1).isdigit():
                        raise ValueError("Сумма возврата должна быть числом.")

                    new_return = Return(
                        shop_id=shop_id,
                        date=date,
                        item_name=item_name,
                        employee_id=int(employee_id),
                        amount=float(amount),
                        notes=notes
                    )
                    db.session.add(new_return)
                    db.session.commit()
                    print("Новая запись возврата успешно добавлена.")
                except Exception as e:
                    print(f"Ошибка при добавлении записи: {e}")
                    db.session.rollback()
                    return {"message": "Ошибка при добавлении записи"}, 500

                return redirect(url_for('shop_returns', shop_id=shop_id))

        employees = Employee.query.filter_by(shop_id=shop_id).all()
        return render_template(
            'shop_returns.html',
            shop=shop,
            returns=returns,
            employees=employees,
            start_date=start_date,
            end_date=end_date,
            datetime=datetime  # Передаём объект datetime в шаблон
        )

    @app.route('/shop/<int:shop_id>/delete_return/<int:return_id>', methods=['POST'])
    def delete_return(shop_id, return_id):
        try:
            return_record = Return.query.get_or_404(return_id)
            if return_record.shop_id != shop_id:
                raise ValueError("Запись не принадлежит текущему магазину.")

            db.session.delete(return_record)
            db.session.commit()
            print(f"Запись возврата ID {return_id} успешно удалена.")
        except Exception as e:
            print(f"Ошибка при удалении записи: {e}")
            db.session.rollback()
            return {"message": "Ошибка при удалении записи"}, 500

        return redirect(url_for('shop_returns', shop_id=shop_id))

    @app.route('/returns', methods=['GET'])
    def all_returns():

        # Фильтрация по датам
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-01')  # Первый день текущего месяца
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')  # Текущая дата

        returns = Return.query.filter(
            Return.date.between(start_date, end_date)).all()
        total_amount = sum(return_record.amount for return_record in returns)
        return render_template('all_returns.html', returns=returns, start_date=start_date, end_date=end_date, total_amount=total_amount)

    @app.route('/shop/<int:shop_id>/expenses', methods=['GET', 'POST'])
    def shop_expenses(shop_id):
        shop = Shop.query.get_or_404(shop_id)

        # Фильтрация по датам
        start_date = request.args.get('start_date', datetime.now().strftime(
            '%Y-%m-01'))  # Первый день текущего месяца
        end_date = request.args.get(
            'end_date', datetime.now().strftime('%Y-%m-%d'))  # Текущая дата

        expenses = Expense.query.filter(
            Expense.shop_id == shop_id,
            Expense.date.between(start_date, end_date)
        ).all()

        if request.method == 'POST':
            data = request.form
            print("Полученные данные:", data)

            if 'new_record' in data:  # Добавление новой записи
                try:
                    # Устанавливаем текущую дату по умолчанию
                    date = data.get('new_date', datetime.utcnow().date())
                    category = data.get('new_category')
                    amount = data.get('new_amount')
                    notes = data.get('new_notes')

                    if not category:
                        raise ValueError(
                            "Категория расходов не может быть пустой.")
                    if not amount or not amount.replace('.', '', 1).isdigit():
                        raise ValueError("Сумма должна быть числом.")

                    # Создание новой записи
                    new_expense = Expense(
                        shop_id=shop_id,
                        date=date,
                        category=category,
                        amount=float(amount),
                        notes=notes
                    )
                    db.session.add(new_expense)
                    db.session.commit()
                    print("Новая запись расходов успешно добавлена.")
                except ValueError as ve:
                    print(f"Ошибка при добавлении новой записи: {ve}")
                    return {"message": str(ve)}, 400
                except Exception as e:
                    print(f"Ошибка при добавлении новой записи: {e}")
                    db.session.rollback()
                    return {"message": "Ошибка при добавлении новой записи"}, 500

                return redirect(url_for('shop_expenses', shop_id=shop_id))

        total_amount = sum(expense.amount for expense in expenses)
        return render_template(
            'shop_expenses.html',
            shop=shop,
            expenses=expenses,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount,
            datetime=datetime  # Передаём datetime в шаблон
        )

    @app.route('/shop/<int:shop_id>/delete_expense/<int:expense_id>', methods=['POST'])
    def delete_expense(shop_id, expense_id):
        try:
            # Получаем запись для удаления
            expense = Expense.query.get_or_404(expense_id)

            # Проверяем принадлежность записи магазину
            if expense.shop_id != shop_id:
                raise ValueError("Запись не принадлежит текущему магазину.")

            # Удаляем запись
            db.session.delete(expense)
            db.session.commit()
            print(f"Запись расходов ID {expense_id} успешно удалена.")
        except Exception as e:
            print(f"Ошибка при удалении записи: {e}")
            db.session.rollback()
            return {"message": "Ошибка при удалении записи"}, 500

        return redirect(url_for('shop_expenses', shop_id=shop_id))

    @app.route('/expenses', methods=['GET'])
    def all_expenses():
        # Фильтрация по датам
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-01')  # Первый день текущего месяца
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')  # Текущая дата

        expenses = Expense.query.filter(
            Expense.date.between(start_date, end_date)).all()

        # Рассчитываем общую сумму расходов
        total_amount = sum(expense.amount for expense in expenses)
        return render_template(
            'all_expenses.html',
            expenses=expenses,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount
        )

    @app.route('/shop/<int:shop_id>/delete_income/<int:income_id>', methods=['POST'])
    def delete_income(shop_id, income_id):
        try:
            print(
                f"Попытка удалить запись с ID {income_id} для магазина {shop_id}")

            # Проверяем, существует ли запись
            income = Income.query.get_or_404(income_id)
            if income.shop_id != shop_id:
                raise ValueError("Запись не принадлежит текущему магазину.")

            # Удаление записи через сырой SQL с использованием sqlalchemy.text
            sql = text("DELETE FROM income WHERE id = :id")
            db.session.execute(sql, {'id': income_id})
            db.session.commit()
            print(f"Запись ID {income_id} успешно удалена.")
        except Exception as e:
            print(f"Ошибка при удалении записи: {e}")
            db.session.rollback()
            return {"message": "Ошибка при удалении записи"}, 500

        return redirect(url_for('shop_incomes', shop_id=shop_id))
