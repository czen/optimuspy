from os import system

from django.core import management
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Clear db, remove task dirs, purge task queue'

    # pylint: broad-exception-caught
    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.NOTICE('Removing database entries...'))
            management.call_command('migrate', 'web', 'zero')
            self.stdout.write(self.style.NOTICE('Migrating database...'))
            management.call_command('migrate', 'web')
            self.stdout.write(self.style.NOTICE('Removing task directories...'))
            management.call_command('rmtasks')
            self.stdout.write(self.style.NOTICE('Purging task queue...'))
            system('celery purge -f')
            self.stdout.write(self.style.SUCCESS('Done'))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(exc))
