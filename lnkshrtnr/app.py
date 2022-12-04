import datetime
import logging
import os
import random
import re
import string

import validators.url
import woodchipper
from flask import Flask, abort, redirect, request
from flask_alembic import Alembic
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, DateTime, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from woodchipper import configs
from woodchipper.http.awslambda import WoodchipperLambda
from woodchipper.http.flask import WoodchipperFlask

from .auth import write_requires_psk

woodchipper.configure(
    config=configs.DevLogToStdout if os.getenv("DEBUG") else configs.JSONLogToStdout,
    facilities={
        "lnkshrtnr": logging.DEBUG if os.getenv("DEBUG") else logging.INFO,
        "flask": logging.INFO,
        "werkzeug": logging.INFO,
    },
)

logger = woodchipper.get_logger(__name__)

app = Flask("lnkshrtnr")
app.wsgi_app = WoodchipperLambda(app.wsgi_app)
WoodchipperFlask(app).chipperize()

db = SQLAlchemy()
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "sqlite://" if os.getenv("TESTING") else os.getenv("DATABASE_URL").replace("postgres://", "postgresql://")
)
db.init_app(app)
alembic = Alembic()
alembic.init_app(app)


class ShortenedLink(db.Model):
    code = Column(String, primary_key=True, nullable=False)
    default_parameter = Column(String, nullable=True)
    redirect_to = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)


@app.before_first_request
def migrate_db():
    with app.app_context():
        alembic.upgrade()


REDIRECT_EVENT = "Shortened link redirect requested."
UPDATE_EVENT = "Shortened link update request."
DELETE_EVENT = "Shortened link delete requested."
CREATE_EVENT = "Shortened link create requested."
PARAMETER_PLACEHOLDER = "{}"
VALID_CODE_RE = re.compile(r"^[a-z0-9_\.-]+$")


@app.route("/<code>", methods=["GET", "PUT", "DELETE"])
@write_requires_psk
def simple_redirect(code):
    code = code.lower()
    if request.method == "GET":
        link = (
            db.session.query(ShortenedLink)
            .filter(ShortenedLink.code == code, ShortenedLink.deleted_at == None)  # noqa: E711
            .first()
        )
        if link is None:
            logger.info(REDIRECT_EVENT, code=code, parameter=None, result="not_found")
            abort(404)
        if PARAMETER_PLACEHOLDER in link.redirect_to:
            if link.default_parameter:
                redirect_to = link.redirect_to.replace(PARAMETER_PLACEHOLDER, link.default_parameter, 1)
            else:
                logger.info(REDIRECT_EVENT, code=code, parameter=None, result="not_found")
                abort(404)
        else:
            redirect_to = link.redirect_to
        logger.info(REDIRECT_EVENT, code=code, parameter=None, result="success")
        return redirect(redirect_to)
    elif request.method == "PUT":
        redirect_to = request.json.get("redirect_to", "")
        if not validators.url(redirect_to.replace(PARAMETER_PLACEHOLDER, "foo", 1)):
            logger.info(UPDATE_EVENT, code=code, redirect_to=redirect_to, result="invalid_url")
            return "Invalid redirect URL", 400
        link = (
            db.session.query(ShortenedLink)
            .filter(ShortenedLink.code == code, ShortenedLink.deleted_at == None)  # noqa: E711
            .first()
        )
        if link is None:
            logger.info(UPDATE_EVENT, code=code, redirect_to=redirect_to, result="not_found")
            abort(404)
        link.redirect_to = redirect_to
        if "default_parameter" in request.json:
            link.default_parameter = request.form["default_parameter"]
        db.session.add(link)
        db.session.flush()
        logger.info(UPDATE_EVENT, code=code, redirect_to=redirect_to, result="success")
        return "", 204
    elif request.method == "DELETE":
        link = (
            db.session.query(ShortenedLink)
            .filter(ShortenedLink.code == code, ShortenedLink.deleted_at == None)  # noqa: E711
            .with_for_update()
            .first()
        )
        if link is None:
            logger.info(DELETE_EVENT, code=code, result="not_found")
            abort(404)
        link.deleted_at = datetime.datetime.now(datetime.timezone.utc)
        db.session.add(link)
        db.session.flush()
        logger.info(DELETE_EVENT, code=code, result="success")
        return "", 204


@app.route("/<code>/<parameter>")
def redirect_with_parameter(code, parameter):
    code = code.lower()
    link = (
        db.session.query(ShortenedLink)
        .filter(ShortenedLink.code == code, ShortenedLink.deleted_at == None)  # noqa: E711
        .first()
    )
    if link is None:
        logger.info(REDIRECT_EVENT, code=code, parameter=parameter, result="not_found")
        abort(404)
    if PARAMETER_PLACEHOLDER not in link.redirect_to:
        logger.info(REDIRECT_EVENT, code=code, parameter=parameter, result="not_found")
        abort(404)
    else:
        redirect_to = link.redirect_to.replace(PARAMETER_PLACEHOLDER, parameter, 1)
    logger.info(REDIRECT_EVENT, code=code, parameter=parameter, result="success")
    return redirect(redirect_to)


def id_gen():
    digits = string.digits + string.ascii_lowercase
    id_int = random.randint(0, (36**8) - 1)
    id_str = ""
    power = 7
    while power >= 0:
        placevalue = id_int // (36**power)
        id_str += digits[placevalue]
        id_int -= placevalue * (36**power)
        power -= 1
    return id_str


@app.route("/", methods=["POST"])
@write_requires_psk
def create_redirect():
    try:
        code = request.json.get("code", "").lower()
        if not code:
            code = id_gen()
        redirect_to = request.json["redirect_to"]
        if not VALID_CODE_RE.match(code):
            logger.info(CREATE_EVENT, code=code, redirect_to=redirect_to, result="bad_code")
            return "Unacceptable code.", 400
        if not validators.url(redirect_to.replace(PARAMETER_PLACEHOLDER, "foo", 1)):
            logger.info(CREATE_EVENT, code=code, redirect_to=redirect_to, result="invalid_url")
            return "Invalid URL.", 400
        default_parameter = request.json.get("default_parameter")
        created_by = request.json["created_by"]
        link = ShortenedLink(
            code=code, redirect_to=redirect_to, default_parameter=default_parameter, created_by=created_by
        )
        db.session.add(link)
        db.session.flush()
        logger.info(CREATE_EVENT, code=code, redirect_to=redirect_to, result="success")
        return code, 201
    except KeyError as e:
        logger.info(CREATE_EVENT, code=code, redirect_to=redirect_to, result="missing_arg")
        return str(e), 400
    except IntegrityError:
        logger.info(CREATE_EVENT, code=code, redirect_to=redirect_to, result="duplicate")
        return "Code already in use.", 400
