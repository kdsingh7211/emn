from django.core.management.base import BaseCommand
from emn.models import Mentor, Startup, MentorMatch
from emn.matching_algorithm import EMNMatchingAlgorithm, MatchingConfig

class Command(BaseCommand):
    help = 'Create intelligent mentor-startup matches using matching algorithm'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing matches before creating new ones'
        )

    def handle(self, *args, **options):
        clear_existing = options['clear_existing']
        
        if clear_existing:
            self.stdout.write('Clearing existing matches...')
            MentorMatch.objects.all().delete()
        
        self.stdout.write('Creating intelligent mentor-startup matches...')
        
        # Generate all matches using the new algorithm
        config = MatchingConfig()
        algorithm = EMNMatchingAlgorithm(config)
        result = algorithm.batch_create_matches()
        
        # Count high quality matches
        high_quality_matches = MentorMatch.objects.filter(
            match_score__gte=70
        ).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nMatching Results:\n'
                f'- Total matches processed: {result["total_matches"]}\n'
                f'- High quality matches (≥70): {result["high_quality_matches"]}\n'
                f'- Mentors: {result["mentors_count"]}\n'
                f'- Startups: {result["startups_count"]}\n'
            )
        )
        
        # Show some example matches
        self.stdout.write('\n' + '='*80)
        self.stdout.write('TOP MATCHES CREATED:')
        self.stdout.write('='*80)
        sample_matches = MentorMatch.objects.select_related(
            'mentor', 'startup__registration'
        ).order_by('-match_score')[:5]
        
        for match in sample_matches:
            sectors = ', '.join(match.matching_sectors) if match.matching_sectors else 'No common sectors'
            
            # Extract calculated vs final score from factors
            factors = match.score_factors or {}
            raw_calculated = factors.get('raw_calculated', match.match_score)
            final = factors.get('final_score', match.match_score)
            
            # Get mentor and startup sectors for display
            mentor_sectors = f"{match.mentor.preferred_sector_1}, {match.mentor.preferred_sector_2}, {match.mentor.preferred_sector_3}"
            startup_sectors = "N/A"
            if match.startup.idea:
                startup_sectors = f"{match.startup.idea.sector_1}, {match.startup.idea.sector_2}, {match.startup.idea.sector_3}"
            
            # Show mentor_any_sector status
            any_sector_boost = " (+ Any Sector Boost)" if match.mentor.mentor_any_sector else ""
            
            if raw_calculated != final:
                score_info = f"Calculated: {raw_calculated:.1f}% → Final: {final:.1f}%{any_sector_boost}"
            else:
                score_info = f"Score: {final:.1f}%"
            
            self.stdout.write(
                f'\n  📊 {match.mentor.full_name} <-> {match.startup.registration.first_name}'
            )
            self.stdout.write(
                f'     {score_info}'
            )
            self.stdout.write(
                f'     Mentor sectors: [{mentor_sectors}]'
            )
            self.stdout.write(
                f'     Startup sectors: [{startup_sectors}]'
            )
            self.stdout.write(
                f'     Matches: {sectors}'
            )