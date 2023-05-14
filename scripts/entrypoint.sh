#!/bin/sh
# service rabbitmq-server start

python3 manage.py wait_for_db &&
python3 manage.py migrate
celery -A optimuspy worker --concurrency 1 -P solo --loglevel=info &
gunicorn optimuspy.wsgi --bind 0.0.0.0:8000
