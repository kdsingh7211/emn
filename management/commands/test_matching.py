from django.core.management.base import BaseCommand
from emn.models import Mentor, Startup, MentorMatch
from emn.matching_algorithm import EMNMatchingAlgorithm
from eureka25.models import Registration, Idea

class Command(BaseCommand):
    help = 'Test the matching algorithm with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Testing EMN Matching Algorithm...\n')
        
        # Get sample mentor and startup
        mentor = Mentor.objects.first()
        startup = Startup.objects.first()
        
        if not mentor:
            self.stdout.write(self.style.ERROR('No mentors found. Please create some mentors first.'))
            return
            
        if not startup:
            self.stdout.write(self.style.ERROR('No startups found. Please create some startups first.'))
            return
        
        self.stdout.write(f'Testing match between:')
        self.stdout.write(f'  Mentor: {mentor.full_name}')
        self.stdout.write(f'    - Sectors: {mentor.preferred_sector_1}, {mentor.preferred_sector_2}, {mentor.preferred_sector_3}')
        self.stdout.write(f'    - Location: {mentor.city}, {mentor.state}')
        self.stdout.write(f'    - Stakeholder Types: {mentor.stakeholder_types}')
        self.stdout.write(f'    - Mentor Any Sector: {mentor.mentor_any_sector}')
        
        self.stdout.write(f'  Startup: {startup.registration.first_name} {startup.registration.last_name}')
        if startup.idea:
            self.stdout.write(f'    - Startup Name: {startup.idea.startup_name}')
            self.stdout.write(f'    - Sectors: {startup.idea.sector_1}, {startup.idea.sector_2}, {startup.idea.sector_3}')
        else:
            self.stdout.write(f'    - No idea submitted yet')
        self.stdout.write(f'    - Location: {startup.registration.city}, {startup.registration.state}')
        
        # Calculate match score
        result = EMNMatchingAlgorithm.calculate_match_score(mentor, startup)
        
        self.stdout.write(f'\n--- MATCH RESULTS ---')
        self.stdout.write(f'Overall Score: {result["score"]}%')
        self.stdout.write(f'Match Created: {"Yes" if result["created"] else "Already existed"}')
        
        self.stdout.write(f'\n--- SCORE BREAKDOWN ---')
        for factor, score in result['factors'].items():
            self.stdout.write(f'  {factor.title()}: {score}%')
        
        self.stdout.write(f'\n--- MATCHING SECTORS ---')
        if result['match'].matching_sectors:
            for sector in result['match'].matching_sectors:
                self.stdout.write(f'  • {sector}')
        else:
            self.stdout.write('  No matching sectors found')
        
        # Test generating matches for this mentor
        self.stdout.write(f'\n--- TOP 5 MATCHES FOR {mentor.full_name} ---')
        matches = EMNMatchingAlgorithm.generate_matches_for_mentor(mentor, limit=5)
        
        for i, (match, score, factors) in enumerate(matches, 1):
            startup_name = f"{match.startup.registration.first_name} {match.startup.registration.last_name}"
            self.stdout.write(f'  {i}. {startup_name} - {score}%')
            
        self.stdout.write(self.style.SUCCESS('\nMatching algorithm test completed!'))