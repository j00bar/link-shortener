import os
import random
import re
import string
from io import BytesIO

import pyqrcode
import validators.url
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from .database import db
from .exceptions import LinkShortenerException
from .models import ShortenedLink

VALID_CODE_RE = re.compile(r"^[a-z0-9_\.-]+$")
PARAMETER_PLACEHOLDER = "{}"


def qrcode_for_link(format, code, param=None):
    url = f"https://{os.getenv('HOSTNAME')}/{code}{'/'+param if param else ''}"
    qr = pyqrcode.create(url, error="H")
    buffer = BytesIO()
    if format == "png":
        qr.png(buffer, scale=10)
        content_type = "image/png"
    if format == "eps":
        qr.eps(buffer, scale=10)
        content_type = "application/postscript"
    if format == "svg":
        qr.svg(buffer, scale=10)
        content_type = "image/svg+xml"
    buffer.seek(0)
    return content_type, buffer


def record_click(shortened_link):
    db.session.execute(
        update(ShortenedLink)
        .where(ShortenedLink.code == shortened_link.code)
        .values(clicks=(ShortenedLink.clicks + 1))
    )


def get_link_by_code(code):
    return (
        db.session.query(ShortenedLink)
        .filter(ShortenedLink.code == code, ShortenedLink.deleted_at == None)  # noqa: E711
        .first()
    )


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


def create_redirect(code, redirect_to, created_by, default_parameter=None):
    if not VALID_CODE_RE.match(code):
        raise LinkShortenerException("Unacceptable code", "bad_code")
    if not validators.url(redirect_to.replace(PARAMETER_PLACEHOLDER, "foo", 1)):
        raise LinkShortenerException("Bad URL", "invalid_url")
    try:
        link = ShortenedLink(
            code=code, redirect_to=redirect_to, default_parameter=default_parameter, created_by=created_by
        )
        db.session.add(link)
    except IntegrityError:
        raise LinkShortenerException("Code already in use.", "already_exists")
