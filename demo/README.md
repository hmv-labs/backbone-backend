# Get started

## Install backbone

To get started you need to install the backbone requirement as indicated in `requirements.in` file

```
pip install -r requirements.in
```

## Configure right env

After that, you need to configure `manage.py`, `asgi.py` and `wsgi.py`. The latter does not really matter, but better to have it in sync.
Basically you just need to copy paste these files in the new projects.

- update `manage.py` to read right `.env` file
- update `demo/asgi.py` with backbone's bootstrap functionality and `demo/wsgi.py`


## Configure settings

Last thing, configure settings - and update your env variable `DJANGO_SETTINGS_MODULE` in your `.env` file

- configure `demo/settings/base.py` and `demo/settings/development.py`
