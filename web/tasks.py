import shutil
import subprocess as sp
import tarfile
import os
from os import chdir, getcwd
from pathlib import Path
import shutil

from celery.utils.log import get_logger
from django.conf import settings

from optimuspy import celery_app
from web.models import Benchmark, Result, Task, CompError
from web.ops.build_tools import catch2
from web.ops.compilers import Compiler, Compilers
from web.ops.passes import Pass, Passes

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

    for i in task.passes:
        try:
            # Create new result
            r = Result(task=task, num=i)
            r.save()

            # Create result directory
            subdir = path / str(i)
            subdir.mkdir()

            # Copy src files to subdir
            for file in files:
                shutil.copy(file, subdir)

            # Run opsc pass
            _p = Passes(i)
            p: Pass = _p.obj(subdir.iterdir())
            _ret = p.run()
            logger.info('%s finished with code %d', _p.name, _ret)
            if _ret != 0:
                r.error = True
                r.save()

            # For every compiler enabled
            for comps in task.compilers:
                # Get compiler object from enum
                comp: Compiler = Compilers(comps).obj
                # For every cflags in compiler's preset
                for _cf in sorted(set(task.cflags) & set(fl.name for fl in comp.cflags)):
                    try:
                        cf = comp.cflags[_cf]
                        # Create new benchmark
                        b = Benchmark(task=task, pas=i, compiler=comps, cflags=cf.name)
                        b.save()

                        # Create all necessary build files
                        catch2.setup(subdir, c_files, task, comp, cf)

                        cwd = getcwd()
                        try:
                            chdir(subdir)

                            # Run build and test routines
                            ps1 = sp.run(['make', 'build'], check=False, capture_output=True)

                            if ps1.returncode != 0:
                                err = CompError(bench=b, text=ps1.stderr.decode('utf-8'))
                                err.save()

                            ps2 = sp.run(['make', 'test'], check=False)

                        except Exception as e2:
                            logger.info(e2)
                            b.error = True
                            b.save()

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

                        logger.info('benchmark %d exit code: %d', b.id, ps2.returncode)

                        # Cleanup
                        catch2.cleanup(subdir, files)
                    except Exception as e3:
                        logger.info(e3)
                        b.error = True
                        b.save()

            # Package optimized sources
            cwd = getcwd()
            try:
                chdir(subdir)
                files2 = list(Path('.').iterdir())
                with tarfile.open(f'{task.hash}.{Passes(i)}.tar.gz', 'w:gz') as tar:
                    for file in files2:
                        tar.add(file)

                for file in files2:
                    if os.path.isfile(file):
                        os.remove(file)
                    else:
                        shutil.rmtree(file)

            except Exception as e3:
                logger.info(e3)
                r.error = True
                r.save()
            finally:
                chdir(cwd)

        except Exception as e:
            logger.error(e)
            r.error = True
            r.save()

    # Cleanup task root dir
    for file in files:
        if os.path.isfile(file):
            os.remove(file)
        else:
            shutil.rmtree(file)

    task.ready = True
    task.save()
    logger.info('Finished execution of task %s', task.id)
