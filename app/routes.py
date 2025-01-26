from flask import Flask, render_template, redirect, url_for, request, jsonify, Blueprint, flash
from app.models import db, Shop, Employee, Income, Expense, Workday, Return, SalesReturn, ShopExpense
from app.forms import EmployeeForm, ShopForm, IncomeForm
from datetime import datetime, date, timedelta
from calendar import monthrange
from sqlalchemy import text, func, asc, desc
from jinja2 import Environment, FileSystemLoader
from flask_login import login_user, logout_user, login_required, current_user
from .auth import auth_bp
import calendar


def has_access_to_shop(shop_id):
    """
    Проверяет, имеет ли пользователь доступ к указанному магазину.
    """
    return current_user.shop_id is None or current_user.shop_id == shop_id


shops = [
    {"id": 1, "address": "Пр. Строителей 132", "name": "Магазин № 1"},
    {"id": 2, "address": "Пр. Ленина 66/39", "name": "Магазин № 2"},
    {"id": 3, "address": "Пр. Строителей, 100", "name": "Магазин № 3"},
    {"id": 4, "address": "Пр. Строителей", "name": "Магазин № 4"}
]


def init_routes(app: Flask):
    app.register_blueprint(auth_bp)

    @app.errorhandler(404)
    def not_found(error):
        return 'Oops! Ты зашёл куда-то не туда =(\n', 404

    @app.route('/add_employee', methods=['GET', 'POST'])
    @login_required
    def add_employee():

        form = EmployeeForm()
        # Заполняем варианты магазинов
        form.shop_id.choices = [(shop.id, shop.name)
                                for shop in Shop.query.order_by(asc(Shop.id)).all()]

        # Получаем shop_id из query-параметров (если есть)
        # Если не нужен в GET, можно убрать, но тогда не будет "Назад" до сабмита
        shop_id = request.args.get('shop_id', type=int)

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

            # После успешного добавления — делаем редирект на страницу "shop_employees"
            # Теперь shop_id берём напрямую из формы
            return redirect(url_for('shop_employees', shop_id=form.shop_id.data))

        # Если GET-запрос (или валидация не пройдена), рендерим шаблон,
        # при этом передаём shop_id (если он есть) в шаблон
        return render_template('add_employee.html', form=form, shop_id=shop_id)

    @app.template_filter('format_date')
    @login_required
    def format_date(value):
        """Принимает datetime/date и возвращает строку вида 'дд.мм'."""
        if isinstance(value, (datetime, date)):
            return value.strftime('%d.%m')
        return value  # Если не дата

    # ---------------------------------------------
    # Обработчик главной страницы ( / )
    # ---------------------------------------------
    @app.route('/', methods=['GET'])
    @login_required
    def index():
        """
        Главная страница: выводит магазины, форму для фильтра,
        агрегированную статистику по расходам/продажам/возвратам
        и динамические таблицы по датам.
        """
        # 1. Получаем даты из GET-параметров
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        # Парсим их, если заданы
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(
                    start_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                end_date = None

        # По умолчанию: последняя неделя
        if not start_date or not end_date:
            end_date = date.today()
            start_date = end_date - timedelta(days=6)

        # 2. Формируем список дней (для динамических столбцов в таблицах)
        days_range = []
        current_day = start_date
        while current_day <= end_date:
            days_range.append(current_day)
            current_day += timedelta(days=1)

        # 3. Запрашиваем из БД суммарные расходы за период по дням
        expenses_query = db.session.query(
            ShopExpense.date,
            func.sum(ShopExpense.purchase).label('total_purchase'),
            func.sum(ShopExpense.store_needs).label('total_store_needs'),
            func.sum(ShopExpense.salary).label('total_salary'),
            func.sum(ShopExpense.rent).label('total_rent'),
            func.sum(ShopExpense.repair).label('total_repair'),
            func.sum(ShopExpense.marketing).label('total_marketing'),
        ).filter(
            ShopExpense.date >= start_date,
            ShopExpense.date <= end_date
        ).group_by(ShopExpense.date).all()

        # Инициализируем словари для расходов
        expenses = {
            'purchase': {},
            'store_needs': {},
            'salary': {},
            'rent': {},
            'repair': {},
            'marketing': {},
            'total_expenses_all': {}
        }

        # Заполняем словари данными
        for row in expenses_query:
            expenses['purchase'][row.date] = row.total_purchase or 0
            expenses['store_needs'][row.date] = row.total_store_needs or 0
            expenses['salary'][row.date] = row.total_salary or 0
            expenses['rent'][row.date] = row.total_rent or 0
            expenses['repair'][row.date] = row.total_repair or 0
            expenses['marketing'][row.date] = row.total_marketing or 0
            expenses['total_expenses_all'][row.date] = (
                (row.total_purchase or 0) +
                (row.total_store_needs or 0) +
                (row.total_salary or 0) +
                (row.total_rent or 0) +
                (row.total_repair or 0) +
                (row.total_marketing or 0)
            )

        # Инициализируем итоговые суммы
        expenses_totals = {
            'purchase': 0,
            'store_needs': 0,
            'salary': 0,
            'rent': 0,
            'repair': 0,
            'marketing': 0,
            'total_expenses_all': 0
        }

        # Вычисляем итоговые суммы
        for day in days_range:
            expenses_totals['purchase'] += expenses['purchase'].get(day, 0)
            expenses_totals['store_needs'] += expenses['store_needs'].get(
                day, 0)
            expenses_totals['salary'] += expenses['salary'].get(day, 0)
            expenses_totals['rent'] += expenses['rent'].get(day, 0)
            expenses_totals['repair'] += expenses['repair'].get(day, 0)
            expenses_totals['marketing'] += expenses['marketing'].get(day, 0)
            expenses_totals['total_expenses_all'] += expenses['total_expenses_all'].get(
                day, 0)

        # 4. Запрашиваем из БД суммарные продажи/возвраты за период по дням
        sales_query = db.session.query(
            SalesReturn.date,
            func.sum(SalesReturn.retail_sale_amount).label(
                'total_retail_sale'),
            func.sum(SalesReturn.wholesale_sale_amount).label(
                'total_wholesale_sale'),
            func.sum(SalesReturn.return_amount).label('total_return_amount'),
        ).filter(
            SalesReturn.date >= start_date,
            SalesReturn.date <= end_date
        ).group_by(SalesReturn.date).all()

        # Инициализируем словари для продаж и возвратов
        sales_returns = {
            'retail_sale_amount': {},
            'wholesale_sale_amount': {},
            'return_amount': {},
            'net_sales': {},
            'margin': {}
        }

        # Заполняем словари данными
        for row in sales_query:
            sales_returns['retail_sale_amount'][row.date] = row.total_retail_sale or 0
            sales_returns['wholesale_sale_amount'][row.date] = row.total_wholesale_sale or 0
            sales_returns['return_amount'][row.date] = row.total_return_amount or 0
            sales_returns['net_sales'][row.date] = (
                row.total_retail_sale or 0) - (row.total_return_amount or 0)
            sales_returns['margin'][row.date] = (
                row.total_retail_sale or 0) - (row.total_wholesale_sale or 0)

        # Инициализируем итоговые суммы для продаж и возвратов
        sales_returns_totals = {
            'retail_sale_amount': 0,
            'wholesale_sale_amount': 0,
            'return_amount': 0,
            'net_sales': 0,
            'margin': 0
        }

        # Вычисляем итоговые суммы
        for day in days_range:
            sales_returns_totals['retail_sale_amount'] += sales_returns['retail_sale_amount'].get(
                day, 0)
            sales_returns_totals['wholesale_sale_amount'] += sales_returns['wholesale_sale_amount'].get(
                day, 0)
            sales_returns_totals['return_amount'] += sales_returns['return_amount'].get(
                day, 0)
            sales_returns_totals['net_sales'] += sales_returns['net_sales'].get(
                day, 0)
            sales_returns_totals['margin'] += sales_returns['margin'].get(
                day, 0)

        # 5. Считаем итоговую чистую прибыль
        net_profit = sales_returns_totals['net_sales'] - \
            expenses_totals['total_expenses_all']

        # 6. Список магазинов (замените на ваш источник данных)
        shops = [
            {"id": 1, "address": "Пр. Строителей 132", "name": "Магазин № 1"},
            {"id": 2, "address": "Пр. Ленина 66/39", "name": "Магазин № 2"},
            {"id": 3, "address": "Пр. Строителей, 100", "name": "Магазин № 3"},
            {"id": 4, "address": "Пр. Строителей", "name": "Магазин № 4"},
        ]

        # 7. Сумма зарплат из Employee
        employee_query = db.session.query(
            func.sum(Employee.total_salary).label('emp_salary_sum')
        ).filter(
            Employee.id != None  # Добавьте условия фильтрации, если необходимо
        ).one()
        employee_salary_sum = employee_query.emp_salary_sum or 0

        # 8. Передаём всё в шаблон
        return render_template(
            'index.html',
            start_date=start_date_str,
            end_date=end_date_str,
            shops=shops,
            expenses=expenses,
            expenses_totals=expenses_totals,
            sales_returns=sales_returns,
            sales_returns_totals=sales_returns_totals,
            net_profit=net_profit,
            days_range=days_range,
            employee_salary_sum=employee_salary_sum,
        )
# ОБЩАЯ ТАБЛИЦА ВСЕХ ПОКУПОК

    @app.route('/incomes', methods=['GET'])
    @login_required
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

# ОБЩАЯ ТАБЛИЦА ВСЕХ сотрудников

    @app.route('/employees', methods=['GET'])
    @login_required
    def employees():
        # Получаем текущий месяц
        current_month = datetime.now().strftime('%Y-%m')
        selected_month = request.args.get(
            'month', current_month)  # Месяц из формы или текущий

        # Получаем параметры сортировки
        sort = request.args.get('sort', 'total_salary')  # Поле для сортировки
        # Порядок сортировки: 'asc' или 'desc'
        order = request.args.get('order', 'desc')

        # Список разрешенных полей для сортировки
        sortable_columns = {
            'name': Employee.name,
            'shop': Employee.shop_id,  # Предполагается, что сортировка по ID магазина
            'hours_worked': Employee.hours_worked,
            'salary': Employee.salary,
            'motivation': Employee.motivation,
            'total_salary': Employee.total_salary
        }

        # Получаем столбец для сортировки или используем по умолчанию
        sort_column = sortable_columns.get(sort, Employee.total_salary)

        # Определяем порядок сортировки
        if order == 'asc':
            order_by = asc(sort_column)
        else:
            order_by = desc(sort_column)

        # Запрос с сортировкой
        employees_query = Employee.query.filter_by(
            month=selected_month).order_by(order_by)
        employees = employees_query.all()

        # Подсчет общей зарплаты за выбранный месяц
        total_salary = sum(employee.total_salary for employee in employees)

        return render_template(
            'employees.html',
            employees=employees,
            selected_month=selected_month,
            current_month=current_month,
            total_salary=total_salary,
            sort=sort,
            order=order
        )

    @app.route('/employee/<int:employee_id>/delete', methods=['POST'])
    @login_required
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

    @app.template_filter('month_name')
    def month_name_filter(month_number):
        return calendar.month_name[int(month_number)]

    @app.route('/shop/<int:shop_id>/employees', methods=['GET'])
    @login_required
    def shop_employees(shop_id):
        if not has_access_to_shop(shop_id):
            flash('У вас нет доступа к этому магазину.', 'danger')
            return redirect(url_for('index'))

        # Получаем магазин по его ID
        shop = Shop.query.get_or_404(shop_id)

        # Получаем текущий месяц и год
        now = datetime.now()
        current_year = now.year
        current_month = now.strftime('%Y-%m')

        # Получаем выбранный месяц из запроса или используем текущий
        selected_month = request.args.get('month', current_month)

        # Проверка формата selected_month
        try:
            datetime.strptime(selected_month, '%Y-%m')
        except ValueError:
            flash('Неверный формат месяца.', 'danger')
            selected_month = current_month

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
    @login_required
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
    @login_required
    def employee_workdays(employee_id):
        # Получаем сотрудника
        employee = Employee.query.get_or_404(employee_id)

        # Предположим, у объекта employee есть поле shop_id (FK или что-то ещё)
        shop_id = employee.shop_id
        if not has_access_to_shop(shop_id):
            flash('У вас нет доступа к этому магазину.', 'danger')
            return redirect(url_for('index'))
        # Определяем выбранный месяц
        selected_month = request.args.get(
            'month', datetime.now().strftime('%Y-%m')
        )
        year, month = map(int, selected_month.split('-'))

        # Генерируем список дней месяца
        days_in_month = monthrange(year, month)[1]
        days = [
            f"{year}-{month:02d}-{day:02d}" for day in range(1, days_in_month + 1)]

        # Получаем рабочие дни из базы
        workdays = {
            w.date.strftime('%Y-%m-%d'): w.worked
            for w in Workday.query.filter_by(employee_id=employee.id)
            .filter(db.extract('year', Workday.date) == year,
                    db.extract('month', Workday.date) == month).all()
        }

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
            return redirect(url_for('employee_workdays',
                                    employee_id=employee.id,
                                    month=selected_month))

        # ВАЖНО: передаём shop_id в контекст шаблона
        return render_template(
            'employee_workdays.html',
            employee=employee,
            days=days,
            selected_month=selected_month,
            workdays=workdays,
            shop_id=shop_id
        )

    @app.route('/shop/<int:shop_id>/incomes', methods=['GET', 'POST'])
    @login_required
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
    @login_required
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
    @login_required
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
    @login_required
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
    @login_required
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
    @login_required
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
    @login_required
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
    @login_required
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

# дальше будет бред
    @app.route('/shop/<int:shop_id>/sales_returns', methods=['GET', 'POST'])
    @login_required
    def shop_sales_returns(shop_id):
        if not has_access_to_shop(shop_id):
            flash('У вас нет доступа к этому магазину.', 'danger')
            return redirect(url_for('index'))
        """
        Просмотр и сохранение продаж/возвратов.
        """
        start_date = request.args.get(
            'start_date', datetime.now().strftime('%Y-%m-01'))
        end_date = request.args.get(
            'end_date', datetime.now().strftime('%Y-%m-%d'))

        # Фильтруем данные по дате
        records = SalesReturn.query.filter(
            SalesReturn.shop_id == shop_id,
            SalesReturn.date.between(start_date, end_date)
        ).all()

        if request.method == 'POST':
            data = request.form
            print("Полученные данные:", data)  # Логируем входные данные
            try:
                for key in data.keys():
                    if key.startswith('sale_') or key.startswith('is_new_'):
                        # Пример ключа: sale_0, return_item_0, date_0...
                        # Индекс -- это часть после "_"
                        index = key.split('_')[1]

                        sale = data.get(f'sale_{index}')
                        return_item = data.get(f'return_item_{index}')
                        date_str = data.get(f'date_{index}')
                        retail = data.get(f'retail_sale_amount_{index}')
                        wholesale = data.get(f'wholesale_sale_amount_{index}')
                        ret = data.get(f'return_amount_{index}')
                        record_id = data.get(f'id_{index}')

                        # Если все поля в строке пустые — пропускаем
                        if not any([sale, return_item, retail, wholesale, ret]):
                            print(
                                f"Пропущена строка {index}: все поля пустые.")
                            continue

                        # Если отметка, что это новая запись
                        if data.get(f'is_new_{index}') == 'true':
                            new_record = SalesReturn(
                                shop_id=shop_id,
                                # Если дата не указана — подставим текущую
                                date=datetime.strptime(
                                    date_str, '%Y-%m-%d') if date_str else datetime.utcnow(),
                                sale=sale or None,
                                return_item=return_item or None,
                                retail_sale_amount=float(
                                    retail) if retail else None,
                                wholesale_sale_amount=float(
                                    wholesale) if wholesale else None,
                                return_amount=float(ret) if ret else None
                            )
                            db.session.add(new_record)
                        # Иначе обновляем существующую запись (если есть ID)
                        elif record_id:
                            record = SalesReturn.query.get(int(record_id))
                            if record:
                                record.date = (datetime.strptime(date_str, '%Y-%m-%d')
                                               if date_str else record.date)
                                record.sale = sale or None
                                record.return_item = return_item or None
                                record.retail_sale_amount = float(
                                    retail) if retail else None
                                record.wholesale_sale_amount = float(
                                    wholesale) if wholesale else None
                                record.return_amount = float(
                                    ret) if ret else None

                db.session.commit()
                print("Изменения успешно сохранены.")
            except Exception as e:
                db.session.rollback()
                print(f"Ошибка сохранения данных: {e}")
                return "Ошибка сохранения данных", 500

            return redirect(url_for('shop_sales_returns', shop_id=shop_id))

        # Подсчет итогов
        totals = {
            "retail_sale_amount": sum(r.retail_sale_amount or 0 for r in records),
            "wholesale_sale_amount": sum(r.wholesale_sale_amount or 0 for r in records),
            "return_amount": sum(r.return_amount or 0 for r in records),
        }

        return render_template(
            'shop_sales_returns.html',
            shop_id=shop_id,
            records=records,
            totals=totals,
            start_date=start_date,
            end_date=end_date
        )

    @app.route('/shop/<int:shop_id>/expenses_table', methods=['GET', 'POST'])
    @login_required
    def shop_expenses_table(shop_id):
        if not has_access_to_shop(shop_id):
            flash('У вас нет доступа к этому магазину.', 'danger')
            return redirect(url_for('index'))
        # Получаем стартовую и конечную даты из GET-параметров (для фильтра)
        start_date = request.args.get(
            'start_date', datetime.now().strftime('%Y-%m-01'))
        end_date = request.args.get(
            'end_date', datetime.now().strftime('%Y-%m-%d'))

        # Получаем текущие расходы из базы
        expenses = ShopExpense.query.filter(
            ShopExpense.shop_id == shop_id,
            ShopExpense.date.between(start_date, end_date)
        ).all()

        # Обработка формы (POST)
        if request.method == 'POST':
            data = request.form
            print("Полученные данные из формы:", data)

            # Собираем все индексы строк, которые пришли в форме
            # (любое поле, у которого есть суффикс "_число")
            indexes = set()
            for field_name in data.keys():
                if '_' in field_name:
                    # Разбиваем, берём последний кусок как индекс
                    prefix, idx = field_name.rsplit('_', 1)
                    if idx.isdigit():  # Убедимся, что это действительно число
                        indexes.add(idx)

            try:
                # Перебираем все индексы (строки), которые нашли
                for idx in sorted(indexes, key=int):
                    # Считываем значения из формы
                    expense_id = data.get(f'id_{idx}')
                    date_str = data.get(
                        f'date_{idx}', datetime.utcnow().strftime('%Y-%m-%d'))

                    purchase_desc = data.get(f'purchase_desc_{idx}')
                    purchase = data.get(f'purchase_{idx}')
                    store_needs_desc = data.get(f'store_needs_desc_{idx}')
                    store_needs = data.get(f'store_needs_{idx}')
                    salary_desc = data.get(f'salary_desc_{idx}')
                    salary = data.get(f'salary_{idx}')
                    rent_desc = data.get(f'rent_desc_{idx}')
                    rent = data.get(f'rent_{idx}')
                    repair_desc = data.get(f'repair_desc_{idx}')
                    repair = data.get(f'repair_{idx}')
                    marketing_desc = data.get(f'marketing_desc_{idx}')
                    marketing = data.get(f'marketing_{idx}')

                    # Преобразуем суммы в float (если заполнены)
                    purchase_val = float(purchase) if purchase else None
                    store_needs_val = float(
                        store_needs) if store_needs else None
                    salary_val = float(salary) if salary else None
                    rent_val = float(rent) if rent else None
                    repair_val = float(repair) if repair else None
                    marketing_val = float(marketing) if marketing else None

                    # --- Логика пропуска пустых строк (необязательно) ---
                    # Если все поля (и описания, и суммы) пусты, то не сохраняем эту строку
                    if not any([
                        purchase_desc, store_needs_desc, salary_desc,
                        rent_desc, repair_desc, marketing_desc,
                        purchase_val, store_needs_val, salary_val,
                        rent_val, repair_val, marketing_val
                    ]):
                        print(f"Пропущена строка {idx}: нет данных.")
                        continue

                    # Если есть хотя бы что-то, добавляем или обновляем запись
                    if expense_id:
                        # Пытаемся обновить существующую запись
                        expense = ShopExpense.query.get(expense_id)
                        if expense:
                            expense.date = date_str
                            expense.purchase_desc = purchase_desc or None
                            expense.purchase = purchase_val
                            expense.store_needs_desc = store_needs_desc or None
                            expense.store_needs = store_needs_val
                            expense.salary_desc = salary_desc or None
                            expense.salary = salary_val
                            expense.rent_desc = rent_desc or None
                            expense.rent = rent_val
                            expense.repair_desc = repair_desc or None
                            expense.repair = repair_val
                            expense.marketing_desc = marketing_desc or None
                            expense.marketing = marketing_val
                    else:
                        # Создаём новую запись
                        new_expense = ShopExpense(
                            shop_id=shop_id,
                            date=date_str,
                            purchase_desc=purchase_desc or None,
                            purchase=purchase_val,
                            store_needs_desc=store_needs_desc or None,
                            store_needs=store_needs_val,
                            salary_desc=salary_desc or None,
                            salary=salary_val,
                            rent_desc=rent_desc or None,
                            rent=rent_val,
                            repair_desc=repair_desc or None,
                            repair=repair_val,
                            marketing_desc=marketing_desc or None,
                            marketing=marketing_val
                        )
                        db.session.add(new_expense)

                # Сохраняем все изменения
                db.session.commit()
                print("Изменения сохранены успешно!")

            except Exception as e:
                db.session.rollback()
                print(f"Ошибка сохранения данных: {e}")
                return "Ошибка сохранения данных", 500

            # После POST-запроса делаем редирект, чтобы избежать повторной отправки формы
            return redirect(url_for('shop_expenses_table', shop_id=shop_id))

        # Если это просто GET, считаем итоги
        totals = {
            "purchase": sum(e.purchase or 0 for e in expenses),
            "store_needs": sum(e.store_needs or 0 for e in expenses),
            "salary": sum(e.salary or 0 for e in expenses),
            "rent": sum(e.rent or 0 for e in expenses),
            "repair": sum(e.repair or 0 for e in expenses),
            "marketing": sum(e.marketing or 0 for e in expenses),
        }

        return render_template(
            'shop_expenses_table.html',
            shop_id=shop_id,
            expenses=expenses,
            totals=totals,
            start_date=start_date,
            end_date=end_date
        )

    @app.route('/shop/<int:shop_id>/delete_expensee/<int:expense_id>', methods=['POST'])
    @login_required
    def delete_expensee(shop_id, expense_id):
        try:
            expense = ShopExpense.query.get_or_404(expense_id)
            if expense.shop_id != shop_id:
                return "Запись не принадлежит текущему магазину", 403

            db.session.delete(expense)
            db.session.commit()
            print(f"Строка с ID {expense_id} успешно удалена.")
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при удалении строки: {e}")
            return "Ошибка при удалении строки", 500

        return redirect(url_for('shop_expenses_table', shop_id=shop_id))

    @app.route('/shop/<int:shop_id>/sales_returns/delete/<int:record_id>', methods=['POST'])
    @login_required
    def delete_sales_return(shop_id, record_id):
        """
        Удаление записи по ID.
        """
        try:
            record = SalesReturn.query.get(record_id)
            if record:
                db.session.delete(record)
                db.session.commit()
                print(f"Запись с ID {record_id} успешно удалена.")
            else:
                print(f"Запись с ID {record_id} не найдена.")
                return "Запись не найдена", 404
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка удаления записи: {e}")
            return "Ошибка при удалении", 500

        return "Успешно", 200
