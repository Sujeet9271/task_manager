from django.core.management.base import BaseCommand
from board.cronjob import overdue_tasks


class Command(BaseCommand):
    help = 'Fetch incoming emails'

    def add_arguments(self, parser):
        parser.add_argument('-i', '--id', type=int, help='Id of survey',)

    def handle(self, *args, **kwargs):
        overdue_tasks()