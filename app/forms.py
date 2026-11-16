from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SelectField, IntegerField, FloatField, TextAreaField,
                     DateField, DateTimeLocalField, BooleanField, SubmitField)
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, EqualTo, Regexp, ValidationError

PASSWORD_RULES = [DataRequired(), Length(min=10, max=128, message="Use at least 10 characters."),
                  Regexp(r"^(?=.*[A-Za-z])(?=.*\d).+$", message="Use letters and numbers.")]


class LoginForm(FlaskForm):
    email = StringField("Correo electrónico · Email", validators=[DataRequired(), Email(), Length(max=160)])
    password = PasswordField("Contraseña · Password", validators=[DataRequired(), Length(max=128)])
    remember = BooleanField("Keep me signed in")
    submit = SubmitField("Sign in")


class RegisterForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=160)])
    password = PasswordField("Password", validators=PASSWORD_RULES)
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")])
    submit = SubmitField("Create account")


class UserForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=160)])
    role = SelectField("Role", choices=[("operator", "Operator"), ("doctor", "Doctor / Specialist"), ("admin", "Administrator")])
    is_active_account = BooleanField("Account active", default=True)
    password = PasswordField("Password (leave blank to keep current)", validators=[Optional(), Length(min=10, max=128),
                             Regexp(r"^(?=.*[A-Za-z])(?=.*\d).+$", message="Use letters and numbers.")])
    submit = SubmitField("Save user")


class ChangePasswordForm(FlaskForm):
    current = PasswordField("Current password", validators=[DataRequired()])
    password = PasswordField("New password", validators=PASSWORD_RULES)
    confirm = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")])
    submit = SubmitField("Change password")


class MissionForm(FlaskForm):
    code = StringField("Mission code", validators=[DataRequired(), Length(max=30), Regexp(r"^[A-Z0-9-]+$", message="Uppercase letters, digits and hyphens only.")])
    name = StringField("Name", validators=[DataRequired(), Length(max=120)])
    environment = SelectField("Environment", choices=[("station", "Space station (LEO)"), ("spacecraft", "Deep-space spacecraft"),
                                                      ("moon", "Lunar surface base"), ("mars", "Mars surface base"), ("analog", "Earth analog habitat")])
    start_date = DateField("Start date", validators=[DataRequired()])
    duration_days = IntegerField("Duration (days)", validators=[DataRequired(), NumberRange(1, 1500)])
    status = SelectField("Status", choices=[("planned", "Planned"), ("active", "Active"), ("completed", "Completed")])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Save mission")


class AstronautForm(FlaskForm):
    code = StringField("Astronaut code", validators=[DataRequired(), Length(max=30), Regexp(r"^[A-Z0-9-]+$", message="Uppercase letters, digits and hyphens only.")])
    full_name = StringField("Full name (fictional for demos)", validators=[DataRequired(), Length(min=3, max=120)])
    demo_age = IntegerField("Age (demo)", validators=[Optional(), NumberRange(18, 80)])
    role_on_board = StringField("Role on board", validators=[Optional(), Length(max=60)])
    mission_id = SelectField("Mission", coerce=int, validators=[Optional()])
    status = SelectField("Status", choices=[("active", "Active"), ("inactive", "Inactive"), ("returned", "Returned to Earth")])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Save astronaut")


class MeasurementForm(FlaskForm):
    astronaut_id = SelectField("Astronaut", coerce=int, validators=[DataRequired()])
    measured_at = DateTimeLocalField("Date and time (UTC)", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    heart_rate = IntegerField("Heart rate (bpm)", validators=[Optional(), NumberRange(25, 230)])
    systolic_bp = IntegerField("Systolic BP (mmHg)", validators=[Optional(), NumberRange(60, 260)])
    diastolic_bp = IntegerField("Diastolic BP (mmHg)", validators=[Optional(), NumberRange(30, 160)])
    spo2 = FloatField("SpO2 (%)", validators=[Optional(), NumberRange(50, 100)])
    temperature = FloatField("Body temperature (°C)", validators=[Optional(), NumberRange(32, 43)])
    respiratory_rate = IntegerField("Respiratory rate (breaths/min)", validators=[Optional(), NumberRange(4, 60)])
    notes = TextAreaField("Observations", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Save measurement")

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        vals = [self.heart_rate.data, self.systolic_bp.data, self.diastolic_bp.data, self.spo2.data, self.temperature.data, self.respiratory_rate.data]
        if all(v is None for v in vals):
            self.heart_rate.errors.append("Enter at least one vital sign.")
            ok = False
        if (self.systolic_bp.data is None) != (self.diastolic_bp.data is None):
            self.diastolic_bp.errors.append("Enter both systolic and diastolic values.")
            ok = False
        elif self.systolic_bp.data is not None and self.diastolic_bp.data >= self.systolic_bp.data:
            self.diastolic_bp.errors.append("Diastolic pressure must be lower than systolic.")
            ok = False
        return ok


class AlertReviewForm(FlaskForm):
    status = SelectField("Status", choices=[("open", "Open"), ("acknowledged", "Acknowledged"), ("resolved", "Resolved")])
    review_notes = TextAreaField("Review notes", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Update alert")


class DeleteForm(FlaskForm):
    """Empty form used only to carry the CSRF token on delete actions."""
    submit = SubmitField("Delete")
