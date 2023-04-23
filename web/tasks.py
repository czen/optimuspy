# import shutil
import subprocess as sp
from os import chdir, getcwd
from pathlib import Path

from celery.utils.log import get_logger

from optimuspy import celery_app

from .models import Task
from .ops.build_tools import catch2

logger = get_logger(__name__)


@celery_app.task
def compiler_job(task_id: int):
    # Obtain all necessary data
    task = Task.objects.get(id=task_id)
    path = Path(task.path)

    # Log execution start
    logger.info('Started execution of task %s', task.id)

    # Get list of all task files
    files = list(path.iterdir())

    # Filter sources only
    c_files = [f for f in files if f.name.endswith('.c')]

    # Create all necessary build files
    catch2.setup(path, c_files, task.tests)

    cwd = getcwd()
    try:
        chdir(path)
        ps = sp.run(['make'], check=False)
        logger.info('compiler exit code: %s', ps.returncode)
    # pylint: disable=broad-exception-caught
    except Exception as exc:
        logger.error(exc)
    finally:
        chdir(cwd)

    task.ready = True
    task.save()
    logger.info('Finished execution of task %s', task.id)
