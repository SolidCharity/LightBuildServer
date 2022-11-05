from django.core.management.base import BaseCommand, CommandError
from lib.LightBuildServer import LightBuildServer


class Command(BaseCommand):
    help = 'Run the builds'

    def handle(self, *args, **options):
        LBS = LightBuildServer()
        LBS.ProcessBuildQueue()
