import os

from slack_bolt import App

from . import repository

app = App(signing_secret=os.getenv("SLACK_SIGNING_SECRET"), token=os.getenv("SLACK_BOT_TOKEN"))


@app.command("/shortenlink")
def shorten_link_command(ack, respond, command):
    # Acknowledge command request
    ack()

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

        # Send message indicating success
        respond(f"Successfully created redirect with code '{code}'")
    except Exception as e:
        # Catch error and send message indicating error and details
        respond(f"Error: {type(e).__name__}\n{e}")
