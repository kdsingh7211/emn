from django.core.management.base import BaseCommand
from emn.models import Mentor, Startup
from emn.matching_algorithm import EMNMatchingAlgorithm
from collections import defaultdict
import csv

class Command(BaseCommand):
    help = 'Generate startup CSV with mentor matching progress'

    def handle(self, *args, **options):
        algorithm = EMNMatchingAlgorithm()
        
        mentors = Mentor.objects.filter(
            is_active=True,
            user__dashboard_access=True
        ).select_related('user')
        
        startups = Startup.objects.filter(
            user__dashboard_access=True
        ).select_related('user', 'registration', 'idea')
        
        self.stdout.write(f"Starting matchmaking...")
        self.stdout.write(f"Available mentors: {mentors.count()}")
        self.stdout.write(f"Available startups: {startups.count()}")
        
        mentor_assignments = defaultdict(int)
        startup_data = []
        unmatched_startups = []
        processed = 0
        matched = 0
        
        for startup in startups:
            processed += 1
            self.stdout.write(f"Processing startup {processed}/{startups.count()}: {startup.registration.first_name} {startup.registration.last_name}")
            
            matches = algorithm.generate_matches_for_startup(startup.id, limit=20)
            
            assigned_mentors = []
            for mentor, score, _ in matches:
                if mentor_assignments[mentor.id] < 5:
                    assigned_mentors.append({
                        'email': mentor.user.email,
                        'name': mentor.full_name,
                        'phone': mentor.phone_number
                    })
                    mentor_assignments[mentor.id] += 1
                    self.stdout.write(f"  Assigned mentor: {mentor.full_name} (now has {mentor_assignments[mentor.id]} startups)")
                    if len(assigned_mentors) == 2:
                        break
            
            if assigned_mentors:
                matched += 1
                startup_data.append({
                    'email': startup.user.email,
                    'name': f"{startup.registration.first_name} {startup.registration.last_name}",
                    'phone': startup.registration.contact_number,
                    'idea': startup.idea.startup_name if startup.idea else 'No idea',
                    'mentors': assigned_mentors
                })
                self.stdout.write(f"  ✓ Matched with {len(assigned_mentors)} mentors")
            else:
                unmatched_startups.append(startup)
                self.stdout.write(f"  ✗ No available mentors found")
        
        # Assign random mentors to unmatched startups
        if unmatched_startups:
            self.stdout.write(f"\nAssigning random mentors to {len(unmatched_startups)} unmatched startups...")
            available_mentors = [m for m in mentors if mentor_assignments[m.id] < 5]
            
            for startup in unmatched_startups:
                assigned_mentors = []
                for mentor in available_mentors:
                    if mentor_assignments[mentor.id] < 5:
                        assigned_mentors.append({
                            'email': mentor.user.email,
                            'name': mentor.full_name,
                            'phone': mentor.phone_number
                        })
                        mentor_assignments[mentor.id] += 1
                        self.stdout.write(f"  Random assigned: {mentor.full_name} to {startup.registration.first_name}")
                        if len(assigned_mentors) == 2:
                            break
                
                if assigned_mentors:
                    matched += 1
                    startup_data.append({
                        'email': startup.user.email,
                        'name': f"{startup.registration.first_name} {startup.registration.last_name}",
                        'phone': startup.registration.contact_number,
                        'idea': startup.idea.startup_name if startup.idea else 'No idea',
                        'mentors': assigned_mentors
                    })
        
        with open('startups_with_mentors.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Startup Email', 'Startup Name', 'Startup Phone', 'Idea Title', 
                           'Mentor1 Email', 'Mentor1 Name', 'Mentor1 Phone',
                           'Mentor2 Email', 'Mentor2 Name', 'Mentor2 Phone'])
            
            for s in startup_data:
                row = [s['email'], s['name'], s['phone'], s['idea']]
                for i in range(2):
                    if i < len(s['mentors']):
                        m = s['mentors'][i]
                        row.extend([m['email'], m['name'], m['phone']])
                    else:
                        row.extend(['', '', ''])
                writer.writerow(row)
        
        used_mentors = len([m for m in mentor_assignments.values() if m > 0])
        
        self.stdout.write(f"\n=== FINAL RESULTS ===")
        self.stdout.write(f"CSV file created: startups_with_mentors.csv")
        self.stdout.write(f"Total startups processed: {processed}")
        self.stdout.write(f"Startups successfully matched: {matched}")
        self.stdout.write(f"Startups without matches: {processed - matched}")
        self.stdout.write(f"Mentors used for matching: {used_mentors}/{mentors.count()}")
        self.stdout.write(f"Total mentor assignments: {sum(mentor_assignments.values())}")