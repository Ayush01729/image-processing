web: gunicorn main:app
worker: celery -A tasks.celery worker --loglevel=info

