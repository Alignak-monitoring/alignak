
from .bottlecore import *


class Bottle(Bottle):

    def wsgi(self, environ, start_response):
        if 'HTTP_X_FORWARDED_PROTO' in environ:
            environ['wsgi.url_scheme'] = environ['HTTP_X_FORWARDED_PROTO']
        return super(Bottle, self).wsgi(environ, start_response)


class BaseRequest(BaseRequest):
    MEMFILE_MAX = 102400
