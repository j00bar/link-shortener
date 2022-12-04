import os


def pytest_configure(config):
    os.environ["TESTING"] = "1"
    from lnkshrtnr.app import migrate_db

    migrate_db()
