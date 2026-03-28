from django.core.management.base import BaseCommand
from emn.models import Mentor, EMNUser

class Command(BaseCommand):
    help = 'Migrate existing Mentor data to EMNUser structure'

    def handle(self, *args, **options):
        self.stdout.write('Starting migration of Mentor data to EMNUser...')
        
        mentors = Mentor.objects.all()
        created_count = 0
        
        for mentor in mentors:
            # Create EMNUser for each mentor
            emn_user, created = EMNUser.objects.get_or_create(
                email=mentor.email,
                defaults={
                    'user_type': 'mentor',
                    'is_email_verified': True,
                    'is_active': mentor.is_active
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created EMNUser for mentor: {mentor.email}')
            else:
                self.stdout.write(f'EMNUser already exists for: {mentor.email}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Migration completed! Created {created_count} EMNUsers from {mentors.count()} mentors.'
            )
        )