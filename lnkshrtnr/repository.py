import os
import random
import re
import string
import uuid
from io import BytesIO
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import pyqrcode
import validators.url
from flask import request
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from user_agents import parse

from .database import db
from .exceptions import LinkShortenerException
from .models import ShortenedLink, ShortenedLinkClick

VALID_CODE_RE = re.compile(r"^[a-z0-9_\.-]+$")
PARAMETER_PLACEHOLDER = "{}"


def merge_utm_tags(url, utm_tags):
    if utm_tags:
        url_parts = urlparse(url)
        qs = parse_qs(url_parts.query)
        for utm_tag in ["source", "medium", "campaign", "term", "content"]:
            if utm_tag in utm_tags:
                qs[f"utm_{utm_tag}"] = utm_tags[utm_tag]
        new_query = urlencode(qs, doseq=True)
        url = urlunparse(url_parts._replace(query=new_query))
    return url


def qrcode_for_link(format, code, param=None, **utm_tags):
    url = f"https://{os.getenv('HOSTNAME')}/{code}{'/'+param if param else ''}"
    url = merge_utm_tags(url, utm_tags)
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
    try:
        user_agent = request.headers.get("user-agent")
        if parse(user_agent).is_bot:
            return
    except RuntimeError:
        pass
    db.session.execute(
        update(ShortenedLink)
        .where(ShortenedLink.code == shortened_link.code)
        .values(clicks=(ShortenedLink.clicks + 1))
    )
    clicker = request.cookies.get("clicker")
    if clicker:
        try:
            clicker = uuid.UUID(clicker)
        except ValueError:
            clicker = None
    clicker = clicker or uuid.uuid4()
    client_ip = request.headers.get("x-forwarded-for", request.remote_addr)
    if client_ip is not None and "," in client_ip:
        ip_sequence = [ip.strip() for ip in client_ip.split(",")]
        trusted_hops = int(os.getenv("XFF_TRUSTED_HOPS", "0"))
        try:
            client_ip = ip_sequence[-1 * (trusted_hops + 1)]
        except IndexError:
            client_ip = None
    click = ShortenedLinkClick(
        link_id=shortened_link.code,
        clicker=clicker,
        client_ip=client_ip,
        referer=request.headers.get("referer", ""),
        user_agent=user_agent,
        source=request.args.get("utm_source"),
        medium=request.args.get("utm_medium"),
        campaign=request.args.get("utm_campaign"),
        term=request.args.get("utm_term"),
        content=request.args.get("utm_content"),
    )
    db.session.add(click)
    db.session.flush()
    return clicker


def get_link_by_code(code):
    return (
        db.session.query(ShortenedLink)
        .filter(ShortenedLink.code == code, ShortenedLink.deleted_at == None)  # noqa: E711
        .first()
    )


def get_clicks_for_link(code):
    return (
        db.session.query(ShortenedLinkClick)
        .filter(ShortenedLinkClick.link_id == code)
        .order_by(ShortenedLinkClick.clicked_at.desc())
        .all()
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
