import os

import pytest

from lnkshrtnr.app import app
from lnkshrtnr.database import db
from lnkshrtnr.models import ShortenedLink
from lnkshrtnr.repository import PARAMETER_PLACEHOLDER


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


@pytest.fixture(scope="function")
def simple_link(app_ctx):
    link = ShortenedLink(code="test", redirect_to="https://example.com/", created_by="joeschmoe")
    db.session.add(link)
    db.session.flush()
    return link


@pytest.fixture(scope="function")
def parametrized_link_with_default(app_ctx):
    link = ShortenedLink(
        code="test-param-with-default",
        redirect_to="https://example.com/" + PARAMETER_PLACEHOLDER,
        default_parameter="foobar",
        created_by="joeschmoe",
    )
    db.session.add(link)
    db.session.flush()
    return link


@pytest.fixture(scope="function")
def parametrized_link_without_default(app_ctx):
    link = ShortenedLink(
        code="test-param-without-default",
        redirect_to="https://example.com/" + PARAMETER_PLACEHOLDER,
        created_by="joeschmoe",
    )
    db.session.add(link)
    db.session.flush()
    return link


@pytest.fixture(scope="function")
def client(app_ctx):
    return app.test_client()


def test_create_link(client):
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "test-create").first() is None
    response = client.post(
        "/", json=dict(code="test-create", redirect_to="https://example.com/", created_by="somebody")
    )
    assert response.status_code == 201
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "test-create").first() is not None


def test_create_link_auto_code(client):
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "test-create").first() is None
    response = client.post("/", json=dict(redirect_to="https://example.com/", created_by="somebody"))
    assert response.status_code == 201
    assert (
        db.session.query(ShortenedLink).filter(ShortenedLink.code == response.get_data(as_text=True).strip()).first()
        is not None
    )


def test_create_link_bad_url(client):
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "test-create").first() is None
    response = client.post(
        "/", json=dict(code="test-create", redirect_to="htps://example.com/", created_by="somebody")
    )
    assert response.status_code == 400
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "test-create").first() is None


def test_create_link_no_code(client):
    response = client.post("/", json=dict(code="", redirect_to="htps://example.com/", created_by="somebody"))
    assert response.status_code == 400


def test_create_link_bad_code(client):
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "illegal code!").first() is None
    response = client.post(
        "/", json=dict(code="illegal code!", redirect_to="htps://example.com/", created_by="somebody")
    )
    assert response.status_code == 400
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "illegal code!").first() is None


def test_create_link_duplicate_code(client, simple_link):
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "test").first() is not None
    response = client.post("/", json=dict(code="test", redirect_to="htps://example.com/", created_by="somebody"))
    assert response.status_code == 400


def test_update_link(client, simple_link):
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "test").first() is not None
    response = client.put("/test", json=dict(redirect_to="https://example.com/other"))
    assert response.status_code == 204
    assert (
        db.session.query(ShortenedLink).filter(ShortenedLink.code == "test").first().redirect_to
        == "https://example.com/other"
    )


def test_update_link_bad_url(client, simple_link):
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "test").first() is not None
    response = client.put("/test", json=dict(redirect_to="htps://example.com/other"))
    assert response.status_code == 400
    assert (
        db.session.query(ShortenedLink).filter(ShortenedLink.code == "test").first().redirect_to
        == "https://example.com/"
    )


def test_delete_link(client, simple_link):
    response = client.delete("/" + simple_link.code)
    assert response.status_code == 204
    assert db.session.query(ShortenedLink).filter(ShortenedLink.code == "test").first().deleted_at is not None
    response = client.get("/test")
    assert response.status_code == 404


def test_get_simple_link(client, simple_link):
    response = client.get("/" + simple_link.code)
    assert response.status_code == 302
    assert response.headers["Location"] == simple_link.redirect_to
    db.session.refresh(simple_link)
    assert simple_link.clicks == 1


def test_get_simple_link_as_qrcode(client, simple_link):
    response = client.get(f"/{simple_link.code}?qr=png")
    assert response.status_code == 200
    assert response.headers.get("Content-Disposition") == f"attachment; filename={simple_link.code}.png"
    assert response.content_type == "image/png"


def test_get_simple_link_but_with_parameter(client, simple_link):
    response = client.get("/" + simple_link.code + "/extra")
    assert response.status_code == 404


def test_get_param_link_using_default(client, parametrized_link_with_default):
    response = client.get("/" + parametrized_link_with_default.code)
    assert response.status_code == 302
    assert response.headers["Location"] == parametrized_link_with_default.redirect_to.replace(
        PARAMETER_PLACEHOLDER, parametrized_link_with_default.default_parameter, 1
    )


def test_get_param_link_without_default_using_default(client, parametrized_link_without_default):
    response = client.get("/" + parametrized_link_without_default.code)
    assert response.status_code == 404


def test_get_param_link_using_parameters(client, parametrized_link_with_default, parametrized_link_without_default):
    response = client.get("/" + parametrized_link_with_default.code + "/extra")
    assert response.status_code == 302
    assert response.headers["Location"] == parametrized_link_with_default.redirect_to.replace(
        PARAMETER_PLACEHOLDER, "extra", 1
    )
    response = client.get("/" + parametrized_link_without_default.code + "/extra")
    assert response.status_code == 302
    assert response.headers["Location"] == parametrized_link_without_default.redirect_to.replace(
        PARAMETER_PLACEHOLDER, "extra", 1
    )
