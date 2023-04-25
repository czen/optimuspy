import shutil
import subprocess as sp
from os import chdir, getcwd
from pathlib import Path

from celery.utils.log import get_logger

from optimuspy import celery_app

from .models import Task, Benchmark
from .ops.build_tools import catch2
from .ops.passes import Pass, Passes

logger = get_logger(__name__)

# pylint: disable=broad-exception-caught


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
    c_files = [f.name for f in files if f.name.endswith('.c')]

    for i in range(len(Passes)):
        try:
            # Create benchmark directory
            subdir = path / str(i)
            subdir.mkdir()

            # Copy src files to subdir
            for file in files:
                shutil.copy(file, subdir)

            b = Benchmark(task=task, num=i)

            # Run opsc pass
            p: Pass = Passes.get(i)(subdir.iterdir())
            if p.run() != 0:
                b.error = True

            # Create all necessary build files
            catch2.setup(subdir, c_files, task.f_name, task.f_sign, task.tests)  # <-

            cwd = getcwd()
            try:
                chdir(subdir)

                # Run build and test routines
                ps = sp.run(['make'], check=False)

            except Exception as e2:
                logger.info(e2)
            finally:
                chdir(cwd)

            # Parse benchmark results
            v, u = catch2.parse_benchmark(subdir)

            # Check for parsing errors
            if u == 'err':
                b.error = True

            # Assign benchmark results
            b.value = v
            b.unit = u

            b.save()

            logger.info('benchmark %d exit code: %s', i, ps.returncode)

        except Exception as e:
            logger.error(e)
            # Cd back
            chdir(cwd)

    # Cleanup
    for i in range(len(Passes)):
        pass


    task.ready = True
    task.save()
    logger.info('Finished execution of task %s', task.id)
