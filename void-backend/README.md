# VOID Django API

## Local development

Use Python 3.12+, PostgreSQL, and Redis (Redis is only needed for local Celery work; the default Django cache remains process-local). Copy `.env.example` to `.env`, replace the placeholders needed for services you use, install `requirements.txt`, then run `python manage.py migrate` and `python manage.py runserver`. `manage.py` defaults to `config.settings.development` for local commands; direct WSGI, ASGI, and Celery processes require `DJANGO_SETTINGS_MODULE` explicitly. Tests use in-memory SQLite by default; set `VOID_TEST_USE_POSTGRES=true` with test database credentials to run the concurrency suite against PostgreSQL.

## Production environment

Set `DJANGO_SETTINGS_MODULE=config.settings.production` in the process environment **before** starting Django, Gunicorn, Celery worker, or Beat. This value must not rely on `.env` loading. Production settings fail closed and require:

`SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `CELERY_BROKER_URL`, `CACHE_REDIS_URL`, `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET`.

Set `DB_PORT` (default 5432), `EMAIL_PORT` (default 587), `DB_CONN_MAX_AGE` (default 60), `MEDIA_ROOT`, and `STATIC_ROOT` to suit the host. Hosts are comma-separated DNS names; CORS and CSRF values are comma-separated origins including scheme. Keep secret values in a protected secret manager or root-owned environment file. Do not put live secrets in source control.

`COOKIE_SAMESITE` supports `Lax`, `Strict`, or `None`; default `Lax` fits a frontend and API on the same site (including subdomains). For separate sites, `None` requires HTTPS and secure cookies, and browser third-party-cookie policies may still block cookies. `COOKIE_DOMAIN` is unset by default. Choose the production domain before setting CORS/CSRF origins or a shared cookie domain; no production domain is assumed here.

## AWS EC2 deployment example

Examples in `deploy/` assume a Linux host, a private Gunicorn Unix socket, Nginx as the TLS terminator, private PostgreSQL and Redis networking, and persistent paths under `/srv/void`. They are templates: replace the example domain and filesystem paths after the domain and storage decisions are made. Restrict inbound access to HTTPS (and SSH from an administrative IP); do not expose PostgreSQL or Redis to the public internet. The Nginx proxy must overwrite `X-Forwarded-Proto` using `$scheme` and forward the original host. The app trusts `X-Forwarded-Proto: https` only behind that trusted proxy.

1. Provision the host, PostgreSQL, Redis, TLS certificate, and persistent upload volume. Put only secret-free config examples in source control; store the actual production environment in `/etc/void/void.env` with owner-only read permissions.
2. Create the virtual environment and install `requirements.txt`.
3. Set production environment values, including `DJANGO_SETTINGS_MODULE=config.settings.production`; run `python manage.py check --deploy` and `python manage.py migrate` once against the intended database.
4. Run `python manage.py collectstatic --noinput`; configure Nginx to serve `STATIC_ROOT` and persistent `MEDIA_ROOT`. Back up product media independently from database backups. Never use an ephemeral deploy directory for uploads.
5. Install the service templates from `deploy/systemd/`, update their paths, then enable `void-gunicorn`, `void-celery-worker`, and exactly one `void-celery-beat` instance. Use a managed Redis service or a private Redis service; point `CELERY_BROKER_URL` and `CACHE_REDIS_URL` to separate Redis logical databases (or separate instances), with authentication/TLS where supported.
6. Configure the Razorpay webhook URL as `https://<chosen-api-host>/api/v1/orders/webhooks/razorpay/`, subscribe to `payment.captured` and `refund.processed`, and set the matching webhook secret. Test with Razorpay test credentials before enabling live payments.
7. Add external health checks for `/api/v1/catalog/` (or a dedicated health endpoint), monitor Gunicorn/worker/Beat and Nginx logs, Redis/PostgreSQL health, disk space, failed tasks, and payment/refund reconciliation. Establish encrypted database and media backups and test restoration before accepting orders.

The scheduled pending-order cleanup and payment callback/webhook processing serialize on the order row. A late captured payment re-reserves available stock or creates a durable refund request. Refund retries use a stable Razorpay receipt and a Celery task; keep at least one worker running and alert on tasks that exhaust retries. Run only one Beat scheduler to avoid duplicate scheduling; task behavior is also idempotent where possible.

## Service commands

See `deploy/systemd/` and `deploy/nginx/` for example service/proxy configuration. From the backend directory, use `python manage.py runserver` for local development; set `DJANGO_SETTINGS_MODULE=config.settings.development` before running local `celery -A config worker -l INFO` or `celery -A config beat -l INFO`.
