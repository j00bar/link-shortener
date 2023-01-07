from flask_alembic import Alembic
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def setup_database(app):
    db.init_app(app)

    alembic = Alembic()
    alembic.init_app(app)

    with app.app_context():
        alembic.upgrade()
