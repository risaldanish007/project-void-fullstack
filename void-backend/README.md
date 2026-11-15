# VOID Django API

## Runtime

- Python 3.12 or newer
- PostgreSQL
- TLS-terminating reverse proxy or managed application platform

## Configure

Copy .env.example to .env for local use, or set those values in the production secret manager. Never commit .env or real credentials.

Production requires SECRET_KEY, DJANGO_SETTINGS_MODULE=config.settings.production, DEBUG=False, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, CSRF_TRUSTED_ORIGINS, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST/DB_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, and USD_TO_INR_RATE. Hosts are comma-separated names without schemes; origin variables are comma-separated full HTTPS origins.

Production settings fail closed if hosts or origins are missing, enforce secure cookies and HTTPS, and enable HSTS. The reverse proxy must forward X-Forwarded-Proto: https only for requests that arrived over HTTPS. Enable HSTS subdomain or preload options only after confirming all affected hosts support HTTPS.

## Deploy

From this directory:

1. Create and activate an isolated Python environment.
2. Install with pip install -r requirements.txt.
3. Run python manage.py check --deploy with production environment configured.
4. Run python manage.py migrate.
5. Run python manage.py collectstatic --noinput and serve staticfiles/ through the platform/web server. Persist uploads in media/ using object storage or a persistent volume.
6. Start with gunicorn config.wsgi:application --bind 0.0.0.0:$PORT from this directory.
7. Configure regular database backups and verify restore before accepting real orders.

Schedule these management commands using the same environment/database: cleanup_pending_orders (releases inventory for safely expired unpaid orders) and cleanup_guest_carts (removes abandoned guest carts). The supported API is Django; do not run a JSON mock API in production.
