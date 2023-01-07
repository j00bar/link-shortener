import os

import woodchipper
from flask import current_app
from slack_bolt import App

from . import repository
from .database import db

app = App(signing_secret=os.getenv("SLACK_SIGNING_SECRET"), token=os.getenv("SLACK_BOT_TOKEN"))
logger = woodchipper.get_logger(__name__)


def bind_flask_app(context, next):
    context["flask_app"] = current_app._get_current_object()
    next()


@app.command("/shortenlink", middleware=[bind_flask_app])
def shorten_link_command(ack, respond, context, command):
    # Acknowledge command request
    ack()
    context["flask_app"].app_context().push()
    logger.info("Slack /shortenlink command received.", **command)

    try:
        # Extract arguments from command
        code = command["text"].split()[0]
        redirect_to = command["text"].split()[1]
        default_parameter = None
        if len(command["text"].split()) > 2:
            default_parameter = command["text"].split()[2]

        # Extract requesting user's Slack username
        username = command["user_name"]

        # Run create_redirect function
        repository.create_redirect(code, redirect_to, username, default_parameter)
        db.session.commit()

        # Send message indicating success
        logger.info("Successfully created redirect.", code=code, redirect_to=redirect_to)
        respond(f"Successfully created redirect with code '{code}'")
    except Exception as e:
        # Catch error and send message indicating error and details
        logger.exception("Error creating redirect.", code=code, redirect_to=redirect_to)
        respond(f"Error: {type(e).__name__}\n{e}")
