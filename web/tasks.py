from celery.utils.log import get_logger

from optimuspy import celery_app

from .models import Task

logger = get_logger(__name__)


@celery_app.task
def compiler_job(task_id: int):
    # pylint: disable=no-member
    task = Task.objects.get(id=task_id)
    logger.info('Started execution of task %s', task.id)
    # ...
    logger.info('Finished execution of task %s', task.id)
