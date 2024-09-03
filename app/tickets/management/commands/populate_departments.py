from django.core.management.base import BaseCommand
from tickets.models import Department

class Command(BaseCommand):
    help = 'Populates the database with initial departments'

    def handle(self, *args, **options):
        departments = [
            'HR',
            'Finance',
            'Engineering',
            'IT',
            'Sales'
        ]

        for dept in departments:
            Department.objects.create(department_name=dept)

        self.stdout.write(self.style.SUCCESS('Successfully populated departments'))
