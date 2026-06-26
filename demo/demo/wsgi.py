from backbone.bootstrap import read_env
from django.core.wsgi import get_wsgi_application

read_env()
application = get_wsgi_application()
