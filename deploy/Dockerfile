FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip check
COPY . .
RUN DJANGO_SETTINGS_MODULE=antheec_app.settings.build ANTHEEC_MODE=development python manage.py collectstatic --noinput
# These are public code/brand assets, not protected uploads or secrets.
# collectstatic inherits the application's restrictive upload permissions.
RUN chmod -R a+rX /app/staticfiles
USER 10001:10001
ENV DJANGO_SETTINGS_MODULE=antheec_app.settings.production ANTHEEC_MODE=owner-testing
CMD ["sh", "-c", "exec gunicorn antheec_app.wsgi:application --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 2 --timeout 120 --max-requests 500 --max-requests-jitter 50 --error-logfile - --log-level warning"]
