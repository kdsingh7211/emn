from django.core.management.base import BaseCommand
from eureka25.models import Registration, Idea
from emn.models import EMNUser, Startup


class Command(BaseCommand):
    help = 'Create EMN users and startups for all emn_access enabled registrations'

    def handle(self, *args, **options):
        registrations = Registration.objects.filter(emn_access=True)
        created_count = 0
        
        for registration in registrations:
            # Create EMN user if not exists
            emn_user, user_created = EMNUser.objects.get_or_create(
                email=registration.email,
                defaults={'user_type': 'startup'}
            )
            
            # Create startup if not exists
            startup, startup_created = Startup.objects.get_or_create(
                registration=registration,
                defaults={'user': emn_user}
            )
            
            # Fetch and link idea
            try:
                idea = Idea.objects.get(eureka_id=registration.eureka_id)
                startup.idea = idea
                startup.save()
            except Idea.DoesNotExist:
                pass
            
            if startup_created:
                created_count += 1
                self.stdout.write(f'Created startup for {registration.first_name} {registration.last_name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} EMN startups')
        )