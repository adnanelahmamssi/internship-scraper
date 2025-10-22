from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    submit = SubmitField('Se connecter')


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('Prénom', validators=[DataRequired(), Length(min=2, max=100)])
    last_name = StringField('Nom', validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    password_confirm = PasswordField('Confirmer le mot de passe', 
                                   validators=[DataRequired(), 
                                             EqualTo('password', message='Les mots de passe doivent correspondre')])
    submit = SubmitField("S'inscrire")