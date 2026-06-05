from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "Load sample categories, medicines, and site settings into the database."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Loading sample FarmOS store data...'))
        call_command('loaddata', 'initial_data.json')
        self.stdout.write(self.style.SUCCESS('Sample data loaded successfully.'))
