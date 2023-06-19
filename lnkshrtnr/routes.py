import datetime
import os

import validators.url
import woodchipper
from flask import abort, redirect, request, send_file
from sqlalchemy.exc import IntegrityError

from . import events, exceptions, repository
from .app import app
from .auth import write_requires_psk
from .database import db

logger = woodchipper.get_logger(__name__)


@app.route("/<code>", methods=["GET", "PUT", "DELETE"], strict_slashes=False)
@write_requires_psk
def simple_redirect(code):
    code = code.lower()
    if request.method == "GET":
        link = repository.get_link_by_code(code)
        if link is None:
            logger.info(events.REDIRECT_EVENT, code=code, parameter=None, result="not_found")
            abort(404)
        if repository.PARAMETER_PLACEHOLDER in link.redirect_to:
            if link.default_parameter is not None:
                redirect_to = link.redirect_to.replace(repository.PARAMETER_PLACEHOLDER, link.default_parameter, 1)
            else:
                logger.info(events.REDIRECT_EVENT, code=code, parameter=None, result="not_found")
                abort(404)
        else:
            redirect_to = link.redirect_to
        utm_tags = {tag[4:]: request.args[tag] for tag in request.args if tag.startswith("utm_")}
        logger.info("utm_tags", utm_tags=utm_tags, merged=repository.merge_utm_tags(redirect_to, utm_tags))
        if format := request.args.get("qr"):
            if format not in ["svg", "png", "eps"]:
                logger.warning(events.INVALID_QR_FORMAT, format=format)
                abort(400)
            content_type, buffer = repository.qrcode_for_link(format, code, **utm_tags)
            return send_file(buffer, as_attachment=True, download_name=f"{code}.{format}", mimetype=content_type)
        clicker = repository.record_click(link)
        db.session.flush() if os.getenv("TESTING") else db.session.commit()
        logger.info(events.REDIRECT_EVENT, code=code, parameter=None, result="success")
        response = redirect(repository.merge_utm_tags(redirect_to, utm_tags))
        response.set_cookie("clicker", str(clicker))
        return response

    elif request.method == "PUT":
        redirect_to = request.json.get("redirect_to", "")
        if not validators.url(redirect_to.replace(repository.PARAMETER_PLACEHOLDER, "foo", 1)):
            logger.info(events.UPDATE_EVENT, code=code, redirect_to=redirect_to, result="invalid_url")
            return "Invalid redirect URL", 400
        link = repository.get_link_by_code(code)
        if link is None:
            logger.info(events.UPDATE_EVENT, code=code, redirect_to=redirect_to, result="not_found")
            abort(404)
        link.redirect_to = redirect_to
        if "default_parameter" in request.json:
            link.default_parameter = request.form["default_parameter"]
        db.session.add(link)
        db.session.flush() if os.getenv("TESTING") else db.session.commit()
        logger.info(events.UPDATE_EVENT, code=code, redirect_to=redirect_to, result="success")
        return "", 204
    elif request.method == "DELETE":
        link = repository.get_link_by_code(code)
        if link is None:
            logger.info(events.DELETE_EVENT, code=code, result="not_found")
            abort(404)
        link.deleted_at = datetime.datetime.now(datetime.timezone.utc)
        db.session.add(link)
        db.session.flush() if os.getenv("TESTING") else db.session.commit()
        logger.info(events.DELETE_EVENT, code=code, result="success")
        return "", 204


@app.route("/<code>/<parameter>", strict_slashes=False)
def redirect_with_parameter(code, parameter):
    code = code.lower()
    link = repository.get_link_by_code(code)
    if link is None:
        logger.info(events.REDIRECT_EVENT, code=code, parameter=parameter, result="not_found")
        abort(404)
    if repository.PARAMETER_PLACEHOLDER not in link.redirect_to:
        logger.info(events.REDIRECT_EVENT, code=code, parameter=parameter, result="not_found")
        abort(404)
    else:
        redirect_to = link.redirect_to.replace(repository.PARAMETER_PLACEHOLDER, parameter, 1)
    utm_tags = {tag[4:]: request.args[tag] for tag in request.args if tag.startswith("utm_")}
    if format := request.args.get("qr"):
        if format not in ["svg", "png", "eps"]:
            logger.warning(events.INVALID_QR_FORMAT, format=format)
            abort(400)
        content_type, buffer = repository.qrcode_for_link(format, code, parameter, **utm_tags)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{code}-{parameter}.{format}",
            mimetype=content_type,
        )
    clicker = repository.record_click(link)
    db.session.flush() if os.getenv("TESTING") else db.session.commit()
    logger.info(events.REDIRECT_EVENT, code=code, parameter=parameter, result="success")
    response = redirect(repository.merge_utm_tags(redirect_to, utm_tags))
    response.set_cookie("clicker", str(clicker))
    return response


@app.route("/", methods=["POST"])
@write_requires_psk
def create_redirect():
    try:
        code = request.json.get("code", "").lower()
        if not code:
            code = repository.id_gen()
        redirect_to = request.json["redirect_to"]
        default_parameter = request.json.get("default_parameter")
        created_by = request.json["created_by"]
        repository.create_redirect(code, redirect_to, created_by, default_parameter=default_parameter)
        db.session.flush() if os.getenv("TESTING") else db.session.commit()
        logger.info(events.CREATE_EVENT, code=code, redirect_to=redirect_to, result="success")
        return code, 201
    except exceptions.LinkShortenerException as e:
        logger.info(events.CREATE_EVENT, code=code, redirect_to=redirect_to, result=e.result)
        return e.msg, 400
    except KeyError as e:
        logger.info(events.CREATE_EVENT, code=code, redirect_to=redirect_to, result="missing_arg")
        return str(e), 400
    except IntegrityError:
        logger.info(events.CREATE_EVENT, code=code, redirect_to=redirect_to, result="duplicate")
        return "Code already in use.", 400
