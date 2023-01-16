import os

import pytest

from lnkshrtnr.app import app
from lnkshrtnr.database import db


def pytest_configure(config):
    os.environ["TESTING"] = "1"


@pytest.fixture(scope="function")
def app_ctx():
    with app.app_context():
        db.session.begin()
        os.environ["BYPASS_AUTH"] = "1"
        yield
        del os.environ["BYPASS_AUTH"]
        db.session.rollback()
        db.session.expunge_all()
        db.session.expire_all()
