from django.core.management.base import BaseCommand
from emn.models import Mentor, Startup, EMNUser
from eureka25.models import Registration, Idea
import random

class Command(BaseCommand):
    help = 'Create test mentors and startups for matching algorithm testing'

    def add_arguments(self, parser):
        parser.add_argument('--mentors', type=int, default=10, help='Number of mentors to create')
        parser.add_argument('--startups', type=int, default=8, help='Number of startups to create')

    def handle(self, *args, **options):
        mentor_count = options['mentors']
        startup_count = options['startups']
        
        self.stdout.write(f'Creating {mentor_count} mentors and {startup_count} startups...')
        
        # Create mentors
        mentors_created = self.create_mentors(mentor_count)
        
        # Create startups
        startups_created = self.create_startups(startup_count)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Created {mentors_created} mentors and {startups_created} startups'
            )
        )

    def create_mentors(self, count):
        sectors = ['blockchain', 'fintech', 'saas', 'edutech', 'healthcare', 'ecommerce', 'iot', 'greentech']
        cities = ['mumbai', 'delhi', 'bengaluru', 'pune', 'hyderabad']
        states = ['Maharashtra', 'Delhi', 'Karnataka', 'Telangana', 'Gujarat']
        
        mentors_data = [
            {'name': 'Rajesh Kumar', 'sectors': ['fintech', 'blockchain', 'saas'], 'city': 'mumbai', 'state': 'Maharashtra'},
            {'name': 'Priya Sharma', 'sectors': ['healthcare', 'biotech', 'edutech'], 'city': 'bengaluru', 'state': 'Karnataka'},
            {'name': 'Amit Patel', 'sectors': ['ecommerce', 'logistics', 'saas'], 'city': 'delhi', 'state': 'Delhi'},
            {'name': 'Sneha Gupta', 'sectors': ['edutech', 'saas', 'it'], 'city': 'pune', 'state': 'Maharashtra'},
            {'name': 'Vikram Singh', 'sectors': ['greentech', 'agriculture', 'manufacturing'], 'city': 'hyderabad', 'state': 'Telangana'},
            {'name': 'Kavya Reddy', 'sectors': ['iot', 'wearable', 'healthcare'], 'city': 'bengaluru', 'state': 'Karnataka'},
            {'name': 'Rohit Agarwal', 'sectors': ['blockchain', 'fintech', 'it'], 'city': 'mumbai', 'state': 'Maharashtra'},
            {'name': 'Anita Joshi', 'sectors': ['social', 'edutech', 'healthcare'], 'city': 'delhi', 'state': 'Delhi'},
            {'name': 'Suresh Nair', 'sectors': ['manufacturing', 'chemical', 'greentech'], 'city': 'pune', 'state': 'Maharashtra'},
            {'name': 'Deepika Rao', 'sectors': ['saas', 'bigdata', 'it'], 'city': 'hyderabad', 'state': 'Telangana'},
        ]
        
        created = 0
        for i in range(count):
            data = mentors_data[i % len(mentors_data)]
            email = f"mentor{i+1}@emn.test"
            
            if not Mentor.objects.filter(email=email).exists():
                mentor = Mentor.objects.create(
                    email=email,
                    full_name=f"{data['name']} {i+1}",
                    phone_number=f"98765{i:05d}",
                    stakeholder_types=['startup_mentor', 'angel_investor'][i % 2:i % 2 + 1],
                    city=data['city'],
                    state=data['state'],
                    organization_name=f"Tech Corp {i+1}",
                    association_interest=['yes', 'maybe', 'no'][i % 3],
                    linkedin_url=f"https://linkedin.com/in/mentor{i+1}",
                    networking_cities=random.sample(cities, random.randint(1, 3)),
                    preferred_sector_1=data['sectors'][0],
                    preferred_sector_2=data['sectors'][1] if len(data['sectors']) > 1 else data['sectors'][0],
                    preferred_sector_3=data['sectors'][2] if len(data['sectors']) > 2 else data['sectors'][0],
                    mentor_any_sector=i % 3 == 0,
                    join_mentorship_portal=i % 2 == 0,
                )
                mentor.set_password('password123')
                mentor.save()
                created += 1
                
        return created

    def create_startups(self, count):
        sectors = ['fintech', 'edutech', 'healthcare', 'ecommerce', 'saas', 'iot', 'greentech', 'blockchain']
        cities = ['Mumbai', 'Delhi', 'Bengaluru', 'Pune', 'Hyderabad', 'Chennai', 'Ahmedabad']
        states = ['Maharashtra', 'Delhi', 'Karnataka', 'Telangana', 'Tamil Nadu', 'Gujarat']
        
        startup_data = [
            {'name': 'Arjun', 'lastname': 'Mehta', 'startup': 'PayEasy', 'sectors': ['fintech', 'blockchain']},
            {'name': 'Riya', 'lastname': 'Shah', 'startup': 'EduTech Pro', 'sectors': ['edutech', 'saas']},
            {'name': 'Karan', 'lastname': 'Verma', 'startup': 'HealthCare AI', 'sectors': ['healthcare', 'bigdata']},
            {'name': 'Pooja', 'lastname': 'Jain', 'startup': 'ShopSmart', 'sectors': ['ecommerce', 'logistics']},
            {'name': 'Rahul', 'lastname': 'Kumar', 'startup': 'GreenEnergy', 'sectors': ['greentech', 'manufacturing']},
            {'name': 'Neha', 'lastname': 'Pandey', 'startup': 'IoT Solutions', 'sectors': ['iot', 'wearable']},
            {'name': 'Siddharth', 'lastname': 'Rao', 'startup': 'SaaS Platform', 'sectors': ['saas', 'it']},
            {'name': 'Anjali', 'lastname': 'Singh', 'startup': 'Social Impact', 'sectors': ['social', 'edutech']},
        ]
        
        created = 0
        for i in range(count):
            data = startup_data[i % len(startup_data)]
            email = f"startup{i+1}@emn.test"
            
            if not Registration.objects.filter(email=email).exists():
                # Create registration
                registration = Registration.objects.create(
                    email=email,
                    password='password123',
                    first_name=f"{data['name']}",
                    last_name=f"{data['lastname']} {i+1}",
                    gender=['Male', 'Female'][i % 2],
                    country_code='+91',
                    contact_number=f"87654{i:05d}",
                    country='India',
                    state=random.choice(states),
                    city=random.choice(cities),
                    pin_code=f"{400000 + i}",
                    current_professional_status='student',
                    educational_background='Engineering',
                    linkedin_url=f"https://linkedin.com/in/startup{i+1}",
                    where_did_you_hear='Social Media',
                    eureka_id=f"EUR{1000 + i}",
                    is_leader=True,
                    idea_filled=True
                )
                
                # Create idea
                idea = Idea.objects.create(
                    startup_name=f"{data['startup']} {i+1}",
                    eureka_id=registration.eureka_id,
                    sector_1=data['sectors'][0],
                    sector_2=data['sectors'][1] if len(data['sectors']) > 1 else None,
                    sector_3=random.choice(sectors) if len(data['sectors']) < 3 else None,
                    dpiit_registered=i % 3 == 0,
                    idea_description=f"Innovative {data['startup']} solution for modern problems",
                    track='General',
                    website_url=f"https://{data['startup'].lower()}{i+1}.com"
                )
                
                # Create EMN user
                emn_user = EMNUser.objects.create(
                    email=email,
                    user_type='startup',
                    is_email_verified=True
                )
                emn_user.set_password('password123')
                emn_user.save()
                
                # Create startup
                Startup.objects.create(
                    user=emn_user,
                    registration=registration,
                    idea=idea
                )
                
                created += 1
                
        return created