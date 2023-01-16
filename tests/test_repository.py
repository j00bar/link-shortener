from unittest.mock import patch

from lnkshrtnr.app import app
from lnkshrtnr.models import ShortenedLink
from lnkshrtnr.repository import record_click

IPHONE_UA_STRING = "Mozilla/5.0 (iPhone; CPU iPhone OS 5_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B179 Safari/7534.48.3"  # noqa: E501
SLACK_UA_STRING = "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)"  # noqa: E501


def test_no_click_for_bots(app_ctx):
    with app.test_request_context("/link", method="GET", headers={"User-agent": IPHONE_UA_STRING}):
        with patch("lnkshrtnr.database.db.session.execute") as db_session:
            record_click(ShortenedLink(code="link"))
            db_session.assert_called()

    with app.test_request_context("/link", method="GET", headers={"User-agent": SLACK_UA_STRING}):
        with patch("lnkshrtnr.database.db.session.execute") as db_session:
            record_click(ShortenedLink(code="link"))
            db_session.assert_not_called()
