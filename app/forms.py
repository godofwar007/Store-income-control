from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, DateField, IntegerField, SelectField, HiddenField
from wtforms.validators import DataRequired


class EmployeeForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired()])
    shop_id = SelectField('Магазин', coerce=int, validators=[DataRequired()])
    hours_worked = IntegerField('Отработанные часы', default=0)
    salary = IntegerField('Ставка', default=0)
    motivation = IntegerField('Мотивация', default=0)
    total_salary = IntegerField('Общая зарплата', default=0)
    month = HiddenField('Месяц')
    submit = SubmitField('Добавить')


class ShopForm(FlaskForm):
    name = StringField('Название магазина', validators=[DataRequired()])
    location = StringField('Расположение', validators=[DataRequired()])
    submit = SubmitField('Добавить')


class IncomeForm(FlaskForm):
    amount = FloatField('Сумма дохода', validators=[DataRequired()])
    description = StringField('Описание', validators=[DataRequired()])
    date = DateField('Дата', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Добавить')

# новое
