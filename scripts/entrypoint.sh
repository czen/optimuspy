#!/bin/sh
# service rabbitmq-server start

python3 manage.py wait_for_db &&
python3 manage.py migrate
celery -A optimuspy worker --concurrency 1 -P solo --loglevel=info &
daphne -b 0.0.0.0 -p 8000 optimuspy.asgi:application
