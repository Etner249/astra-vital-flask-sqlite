from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from sqlalchemy import MetaData

# Naming convention keeps constraint names stable and readable in SQLite
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})
db = SQLAlchemy(metadata=metadata)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access ASTRA VITAL."
login_manager.login_message_category = "info"
csrf = CSRFProtect()
