from django.core.management.base import BaseCommand
from emn.models import Mentor

class Command(BaseCommand):
    help = 'Fix mentor active status'

    def handle(self, *args, **options):
        inactive_mentors = Mentor.objects.filter(is_active=False)
        count = inactive_mentors.count()
        
        if count > 0:
            inactive_mentors.update(is_active=True)
            self.stdout.write(
                self.style.SUCCESS(f'Activated {count} mentors')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All mentors are already active')
            )