from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, DateField, IntegerField, SelectField
from wtforms.validators import DataRequired


class EmployeeForm(FlaskForm):
    name = StringField('ФИО сотрудника', validators=[DataRequired()])
    shop_id = SelectField('Магазин', coerce=int)
    hours_worked = IntegerField(
        'Отработанные часы', validators=[DataRequired()])
    salary = FloatField('Ставка (руб.)', validators=[DataRequired()])
    motivation = FloatField('Мотивация (руб.)', validators=[DataRequired()])
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
