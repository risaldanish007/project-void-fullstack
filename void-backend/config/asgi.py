"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    raise RuntimeError(
        'Set DJANGO_SETTINGS_MODULE before starting ASGI; use '
        'config.settings.production for deployment.'
    )

application = get_asgi_application()
