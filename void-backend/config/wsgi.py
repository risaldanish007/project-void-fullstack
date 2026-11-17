"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    raise RuntimeError(
        'Set DJANGO_SETTINGS_MODULE before starting WSGI; use '
        'config.settings.production for deployment.'
    )

application = get_wsgi_application()
