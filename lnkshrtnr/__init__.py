import logging
import os

import woodchipper
from flask import Flask
from woodchipper import configs
from woodchipper.http.flask import WoodchipperFlask

woodchipper.configure(
    config=configs.DevLogToStdout if os.getenv("DEBUG") else configs.JSONLogToStdout,
    facilities={
        "lnkshrtnr": logging.DEBUG if os.getenv("DEBUG") else logging.INFO,
        "flask": logging.INFO,
        "werkzeug": logging.INFO,
    },
)


def setup_app():
    app = Flask("lnkshrtnr")
    WoodchipperFlask(app).chipperize()

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite://" if os.getenv("TESTING") else os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
    )
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = dict(pool_recycle=600)
    return app
