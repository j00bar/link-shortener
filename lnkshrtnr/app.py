from flask import request
from slack_bolt.adapter.flask import SlackRequestHandler

from . import setup_app, slack_app
from .database import setup_database

app = setup_app()
setup_database(app)

from . import routes  # noqa

slack_handler = SlackRequestHandler(slack_app.app)


@app.route("/_slack/command", methods=["POST"])
def slack_route():
    return slack_handler.handle(request)
