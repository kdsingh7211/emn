from django.core.management.base import BaseCommand
from emn.models import Mentor, EMNUser

class Command(BaseCommand):
    help = 'Sync Mentor records with EMNUser records'

    def handle(self, *args, **options):
        mentors = Mentor.objects.all()
        created_count = 0
        
        for mentor in mentors:
            emn_user, created = EMNUser.objects.get_or_create(
                email=mentor.email,
                defaults={
                    'user_type': 'mentor',
                    'is_email_verified': True,
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"Created EMNUser for mentor: {mentor.email}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully synced {created_count} mentor users')
        )