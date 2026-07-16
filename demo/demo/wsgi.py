from django.core.wsgi import get_wsgi_application

from backbone.bootstrap import read_env

read_env()
application = get_wsgi_application()
