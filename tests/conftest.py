import os


def pytest_configure(config):
    os.environ["TESTING"] = "1"
