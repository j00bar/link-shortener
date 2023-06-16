from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from lnkshrtnr.app import app
from lnkshrtnr.models import ShortenedLink
from lnkshrtnr.repository import merge_utm_tags, record_click

IPHONE_UA_STRING = "Mozilla/5.0 (iPhone; CPU iPhone OS 5_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B179 Safari/7534.48.3"  # noqa: E501
SLACK_UA_STRING = "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)"  # noqa: E501


def test_no_click_for_bots(app_ctx):
    with app.test_request_context("/link", method="GET", headers={"User-agent": IPHONE_UA_STRING}):
        with patch("lnkshrtnr.database.db.session", spec=Session) as db_session:
            record_click(ShortenedLink(code="link"))
            db_session.execute.assert_called()
            db_session.add.assert_called()

    with app.test_request_context("/link", method="GET", headers={"User-agent": SLACK_UA_STRING}):
        with patch("lnkshrtnr.database.db.session", spec=Session) as db_session:
            record_click(ShortenedLink(code="link"))
            db_session.execute.assert_not_called()
            db_session.add.assert_not_called()


def test_merge_utm_tags():
    base_url = "https://foo.example.com/path?a=1&utm_source=stuff"
    utm_tags = dict(
        source="things", medium="large", campaign="president", term="word", content="happy", invalid="nope"
    )
    merged_url = merge_utm_tags(base_url, utm_tags)
    query = urlparse(merged_url).query
    qs = parse_qs(query)
    assert qs["a"] == ["1"]
    assert qs["utm_source"] == ["things"]
    assert qs["utm_medium"] == ["large"]
    assert qs["utm_campaign"] == ["president"]
    assert qs["utm_term"] == ["word"]
    assert qs["utm_content"] == ["happy"]
    assert "utm_invalid" not in qs
