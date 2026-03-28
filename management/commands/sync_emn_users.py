from django.core.management.base import BaseCommand
from emn.models import EMNUser, Mentor, Startup
from eureka25.models import Registration

class Command(BaseCommand):
    help = 'Sync existing mentors and startups to EMNUser table'

    def handle(self, *args, **options):
        created_mentors = 0
        created_startups = 0
        
        # Sync mentors
        for mentor in Mentor.objects.all():
            emn_user, created = EMNUser.objects.get_or_create(
                email=mentor.email,
                defaults={
                    'user_type': 'mentor',
                    'is_email_verified': True,
                    'dashboard_access': False  # Default to False as required
                }
            )
            if created:
                created_mentors += 1
        
        # Sync startups from registrations
        for registration in Registration.objects.all():
            emn_user, created = EMNUser.objects.get_or_create(
                email=registration.email,
                defaults={
                    'user_type': 'startup',
                    'is_email_verified': True,
                    'dashboard_access': False  # Default to False as required
                }
            )
            if created:
                created_startups += 1
                
                # Create Startup record if it doesn't exist
                Startup.objects.get_or_create(
                    user=emn_user,
                    defaults={'registration': registration}
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Sync complete:\n'
                f'- Created {created_mentors} mentor EMNUser records\n'
                f'- Created {created_startups} startup EMNUser records'
            )
        )