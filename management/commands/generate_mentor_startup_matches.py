from django.core.management.base import BaseCommand
from emn.models import Mentor, Startup, EMNUser
from emn.matching_algorithm import EMNMatchingAlgorithm
from collections import defaultdict
import json

class Command(BaseCommand):
    help = 'Generate mentor-startup matching lists with email outputs'

    def handle(self, *args, **options):
        algorithm = EMNMatchingAlgorithm()
        
        # Get active mentors and startups with dashboard access
        mentors = Mentor.objects.filter(
            is_active=True,
            user__dashboard_access=True
        ).select_related('user')
        
        startups = Startup.objects.filter(
            user__dashboard_access=True
        ).select_related('user', 'registration', 'idea')
        
        # Track mentor assignment count
        mentor_assignment_count = defaultdict(int)
        
        # List 1: Startups with their top 2 matched mentors
        startup_matches = []
        
        # List 2: Mentors with their matched startups (max 5 per mentor)
        mentor_matches = defaultdict(list)
        
        self.stdout.write("Generating matches...")
        
        for startup in startups:
            # Get top matches for this startup
            matches = algorithm.generate_matches_for_startup(startup.id, limit=10)
            
            # Get top 2 mentors that haven't exceeded 5 startup limit
            top_mentors = []
            for mentor, score, factors in matches:
                if mentor_assignment_count[mentor.id] < 5:
                    top_mentors.append({
                        'mentor_email': mentor.user.email,
                        'mentor_name': mentor.full_name,
                        'score': score
                    })
                    mentor_assignment_count[mentor.id] += 1
                    
                    # Add to mentor's list
                    mentor_matches[mentor.id].append({
                        'startup_email': startup.user.email,
                        'startup_name': f"{startup.registration.first_name} {startup.registration.last_name}",
                        'score': score
                    })
                    
                    if len(top_mentors) == 2:
                        break
            
            if top_mentors:
                startup_matches.append({
                    'startup_email': startup.user.email,
                    'startup_name': f"{startup.registration.first_name} {startup.registration.last_name}",
                    'mentors': top_mentors
                })
        
        # Convert mentor_matches to list format
        mentor_list = []
        for mentor_id, startup_list in mentor_matches.items():
            mentor = Mentor.objects.get(id=mentor_id)
            mentor_list.append({
                'mentor_email': mentor.user.email,
                'mentor_name': mentor.full_name,
                'startups': startup_list,
                'total_assignments': len(startup_list)
            })
        
        # Output results
        self.stdout.write("\n" + "="*80)
        self.stdout.write("LIST 1: STARTUPS WITH TOP 2 MATCHED MENTORS")
        self.stdout.write("="*80)
        
        startup_emails = []
        for match in startup_matches:
            self.stdout.write(f"\nStartup: {match['startup_name']} ({match['startup_email']})")
            startup_emails.append(match['startup_email'])
            for i, mentor in enumerate(match['mentors'], 1):
                self.stdout.write(f"  Mentor {i}: {mentor['mentor_name']} ({mentor['mentor_email']}) - Score: {mentor['score']}")
        
        self.stdout.write(f"\nStartup Emails ({len(startup_emails)}):")
        self.stdout.write(", ".join(startup_emails))
        
        self.stdout.write("\n" + "="*80)
        self.stdout.write("LIST 2: MENTORS WITH MATCHED STARTUPS (MAX 5 EACH)")
        self.stdout.write("="*80)
        
        mentor_emails = []
        for mentor_data in mentor_list:
            self.stdout.write(f"\nMentor: {mentor_data['mentor_name']} ({mentor_data['mentor_email']})")
            self.stdout.write(f"Total Assignments: {mentor_data['total_assignments']}")
            mentor_emails.append(mentor_data['mentor_email'])
            for i, startup in enumerate(mentor_data['startups'], 1):
                self.stdout.write(f"  Startup {i}: {startup['startup_name']} ({startup['startup_email']}) - Score: {startup['score']}")
        
        self.stdout.write(f"\nMentor Emails ({len(mentor_emails)}):")
        self.stdout.write(", ".join(mentor_emails))
        
        # Summary
        self.stdout.write("\n" + "="*80)
        self.stdout.write("SUMMARY")
        self.stdout.write("="*80)
        self.stdout.write(f"Total Startups with matches: {len(startup_matches)}")
        self.stdout.write(f"Total Mentors assigned: {len(mentor_list)}")
        self.stdout.write(f"Total Mentors available: {mentors.count()}")
        self.stdout.write(f"Total Startups available: {startups.count()}")
        
        # Export to JSON files
        with open('startup_matches.json', 'w') as f:
            json.dump(startup_matches, f, indent=2)
        
        with open('mentor_matches.json', 'w') as f:
            json.dump(mentor_list, f, indent=2)
        
        self.stdout.write("\nJSON files exported: startup_matches.json, mentor_matches.json")