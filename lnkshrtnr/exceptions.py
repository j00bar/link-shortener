class LinkShortenerException(ValueError):
    def __init__(self, msg, result=None):
        self.msg = msg
        self.result = result
