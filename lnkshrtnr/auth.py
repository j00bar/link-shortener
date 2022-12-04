import functools
import os

from flask import abort, request


def write_requires_psk(fn):
    @functools.wraps(fn)
    def __wrapped__(*args, **kwargs):
        if not os.getenv("BYPASS_AUTH"):
            if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                if request.headers.get("Authorization", "") != f"PSK {os.getenv('PRIVATE_SHARED_KEY')}":
                    abort(401)
        return fn(*args, **kwargs)

    return __wrapped__
