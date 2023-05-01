#!/bin/sh
service rabbitmq-server start
celery -A optimuspy worker --concurrency 1 -P solo --loglevel=info &
python3 manage.py runserver 0.0.0.0:8000
