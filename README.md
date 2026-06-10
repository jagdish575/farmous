# FarmOS Medicine Ordering Website

A modern medicine ordering website built with Django 5, PostgreSQL, Bootstrap 5, and WhatsApp order handling.

## Features

- Mobile number login and registration
- Browse medicines by category
- Live search suggestions
- Medicine detail pages with quantity selector
- Cart management and item quantity updates
- Address management with optional geolocation
- Order placement with WhatsApp redirect
- Order history and cancellation support
- Custom Django Admin dashboard
- SEO metadata, sitemap, and robots.txt

## Tech Stack

- Django 5
- PostgreSQL
- Bootstrap 5
- JavaScript
- Django Templates

## Setup

1. Create a Python virtual environment and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables or edit `farmos/settings.py` for database settings:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_DB_ENGINE`
- `DJANGO_DB_NAME`
- `DJANGO_DB_USER`
- `DJANGO_DB_PASSWORD`
- `DJANGO_DB_HOST`
- `DJANGO_DB_PORT`

4. Run migrations:

```bash
python manage.py migrate
```

5. Create a superuser:

```bash
python manage.py createsuperuser
```

6. Load medicine data (choose one):

**Kaggle dataset (11,000+ real medicines with photos):**

```bash
python manage.py import_kaggle_medicines --reset --limit 500
```

Use `--limit 0` to import all rows (slower).

**Built-in dummy JSON fixture:**

```bash
python manage.py load_dummy_data --reset
```

**Easy-edit JSON:** edit `store/data/catalog.json`, then:

```bash
python manage.py load_dummy_data --format catalog --reset
```

7. Start the development server:

```bash
python manage.py runserver
```

7. Open the site at `http://127.0.0.1:8000/`.

## Deployment Guide

1. Configure PostgreSQL and environment variables for production.
2. Collect static files:

```bash
python manage.py collectstatic
```

3. Use Gunicorn to serve the application:

```bash
gunicorn farmos.wsgi:application --workers 3 --bind 0.0.0.0:8000
```

4. Configure Nginx as a reverse proxy to serve static files and forward requests to Gunicorn.
5. Secure the app with HTTPS using a certificate.

## Admin

Access the Django admin at `/admin/` after creating a superuser.

## Notes

- Orders are handled manually through WhatsApp.
- No payment gateway or OTP provider is integrated.
- Mobile number is the primary identity field.
