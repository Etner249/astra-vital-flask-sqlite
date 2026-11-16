from urllib.parse import urlsplit
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from .extensions import db
from .forms import LoginForm, RegisterForm, ChangePasswordForm
from .models import User, utcnow
from .services import log_action

bp = Blueprint("auth", __name__)


def _safe_next(target):
    if target and not urlsplit(target).netloc and target.startswith("/"):
        return target
    return url_for("main.dashboard")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.is_active_account and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            user.last_login_at = utcnow()
            log_action("login", "user", user.id, user=user)
            db.session.commit()
            flash(f"Welcome, {user.full_name}.", "success")
            return redirect(_safe_next(request.args.get("next")))
        log_action("login_failed", "user", details=form.email.data[:160])
        db.session.commit()
        flash("Invalid email or password.", "danger")  # same message for unknown user / wrong password
    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            form.email.errors.append("An account with this email already exists.")
        else:
            user = User(full_name=form.full_name.data.strip(), email=email, role="operator")  # least privilege
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            log_action("create", "user", user.id, "self-registration (operator)", user=user)
            db.session.commit()
            flash("Account created with the Operator role. An administrator can change your role.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_action("logout", "user", current_user.id)
    db.session.commit()
    logout_user()
    flash("You have signed out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current.data):
            form.current.errors.append("Current password is incorrect.")
        else:
            current_user.set_password(form.password.data)
            log_action("update", "user", current_user.id, "password changed")
            db.session.commit()
            flash("Password updated.", "success")
            return redirect(url_for("auth.settings"))
    return render_template("auth/settings.html", form=form)
