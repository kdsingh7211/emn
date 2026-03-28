from django.core.management.base import BaseCommand
from emn.models import Mentor, EMNUser

class Command(BaseCommand):
    help = 'Link existing mentors to their EMNUser records'

    def handle(self, *args, **options):
        linked_count = 0
        created_count = 0
        
        for mentor in Mentor.objects.filter(user__isnull=True):
            # Get or create EMNUser for this mentor
            emn_user, created = EMNUser.objects.get_or_create(
                email=mentor.email,
                defaults={
                    'user_type': 'mentor',
                    'is_email_verified': True,
                    'is_active': mentor.is_active,
                    'dashboard_access': True  # Enable dashboard access for existing mentors
                }
            )
            
            # Link mentor to EMNUser
            mentor.user = emn_user
            mentor.save()
            
            linked_count += 1
            if created:
                created_count += 1
                
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully linked {linked_count} mentors to EMNUsers\n'
                f'Created {created_count} new EMNUser records'
            )
        )