from django.core.management.base import BaseCommand
from emn.models import EMNUser, Mentor, Startup, MentorMatch
from emn.matching_algorithm import EMNMatchingAlgorithm

class Command(BaseCommand):
    help = 'Test dashboard access filtering in matchmaking'

    def handle(self, *args, **options):
        self.stdout.write('Testing dashboard access filtering...\n')
        
        # Count users by dashboard access status
        total_users = EMNUser.objects.count()
        users_with_access = EMNUser.objects.filter(dashboard_access=True).count()
        users_without_access = EMNUser.objects.filter(dashboard_access=False).count()
        
        self.stdout.write(f'Total EMN Users: {total_users}')
        self.stdout.write(f'Users with dashboard access: {users_with_access}')
        self.stdout.write(f'Users without dashboard access: {users_without_access}')
        
        # Count mentors and startups with access
        mentor_emails_with_access = EMNUser.objects.filter(
            user_type='mentor', dashboard_access=True
        ).values_list('email', flat=True)
        
        mentors_with_access = Mentor.objects.filter(
            email__in=mentor_emails_with_access
        ).count()
        
        startups_with_access = Startup.objects.filter(
            user__dashboard_access=True
        ).count()
        
        self.stdout.write(f'\nMentors with dashboard access: {mentors_with_access}')
        self.stdout.write(f'Startups with dashboard access: {startups_with_access}')
        
        # Test matching algorithm filtering
        self.stdout.write('\nTesting matching algorithm...')
        
        if mentors_with_access > 0 and startups_with_access > 0:
            algorithm = EMNMatchingAlgorithm()
            
            # Get first mentor with access
            first_mentor = Mentor.objects.filter(
                email__in=mentor_emails_with_access
            ).first()
            
            if first_mentor:
                matches = algorithm.generate_matches_for_mentor(first_mentor.id, limit=5)
                self.stdout.write(f'Generated {len(matches)} matches for mentor {first_mentor.full_name}')
                
                for startup, score, factors in matches:
                    access_status = startup.user.dashboard_access
                    self.stdout.write(f'  - {startup.registration.first_name} (access: {access_status}, score: {score})')
        
        # Count existing matches that should be filtered
        total_matches = MentorMatch.objects.count()
        valid_matches = MentorMatch.objects.filter(
            mentor__email__in=mentor_emails_with_access,
            startup__user__dashboard_access=True
        ).count()
        
        self.stdout.write(f'\nTotal matches in database: {total_matches}')
        self.stdout.write(f'Valid matches (both users have access): {valid_matches}')
        
        if total_matches > valid_matches:
            invalid_matches = total_matches - valid_matches
            self.stdout.write(
                self.style.WARNING(
                    f'Found {invalid_matches} matches involving users without dashboard access'
                )
            )
            self.stdout.write('Consider running: python manage.py create_matches --clear-existing')
        else:
            self.stdout.write(
                self.style.SUCCESS('All matches involve users with dashboard access ✓')
            )