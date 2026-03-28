from django.core.management.base import BaseCommand
from emn.models import Mentor, Startup, MentorMatch
from emn.matching_algorithm import EMNMatchingAlgorithm

class Command(BaseCommand):
    help = 'Test the top 20 startup matches functionality for mentors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mentor-id',
            type=int,
            help='Test for specific mentor ID'
        )

    def handle(self, *args, **options):
        mentor_id = options.get('mentor_id')
        
        if mentor_id:
            # Test specific mentor
            try:
                mentor = Mentor.objects.get(id=mentor_id)
                self.test_mentor_matches(mentor)
            except Mentor.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Mentor with ID {mentor_id} not found')
                )
        else:
            # Test all mentors
            mentors = Mentor.objects.all()[:3]  # Test first 3 mentors
            for mentor in mentors:
                self.test_mentor_matches(mentor)
                self.stdout.write('-' * 50)

    def test_mentor_matches(self, mentor):
        self.stdout.write(f'\nTesting matches for: {mentor.full_name}')
        
        # Check existing matches in database
        existing_matches = MentorMatch.objects.filter(mentor=mentor).order_by('-match_score')[:20]
        self.stdout.write(f'Existing matches in DB: {existing_matches.count()}')
        
        if existing_matches.exists():
            self.stdout.write('Top 5 existing matches:')
            for i, match in enumerate(existing_matches[:5], 1):
                startup_name = f"{match.startup.registration.first_name} {match.startup.registration.last_name}"
                self.stdout.write(f'  {i}. {startup_name} - Score: {match.match_score}%')
        
        # Test algorithm generation
        algorithm = EMNMatchingAlgorithm()
        generated_matches = algorithm.generate_matches_for_mentor(mentor.id, limit=20)
        self.stdout.write(f'Generated matches: {len(generated_matches)}')
        
        if generated_matches:
            self.stdout.write('Top 5 generated matches:')
            for i, (startup, score, factors) in enumerate(generated_matches[:5], 1):
                startup_name = f"{startup.registration.first_name} {startup.registration.last_name}"
                self.stdout.write(f'  {i}. {startup_name} - Score: {score}%')
        
        # Verify limit is working
        if len(generated_matches) <= 20:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Limit working correctly: {len(generated_matches)} matches (≤20)')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ Limit not working: {len(generated_matches)} matches (>20)')
            )