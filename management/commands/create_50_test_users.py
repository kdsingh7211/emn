from django.core.management.base import BaseCommand
from emn.models import Mentor, Startup, EMNUser
from eureka25.models import Registration, Idea
import random

class Command(BaseCommand):
    help = 'Create 22 mentors and 22 startups for testing'

    def handle(self, *args, **options):

        # Delete all existing test users
        # self.stdout.write('Deleting existing test users...')
        # Startup.objects.all().delete()
        # Registration.objects.all().delete()
        # Idea.objects.all().delete()
        # Mentor.objects.all().delete()
        # EMNUser.objects.all().delete()
        

        self.stdout.write('Creating 22 mentors and 22 startups...')
        
        # Create 22 mentors
        mentor_sectors = ['blockchain', 'fintech', 'saas', 'edutech', 'healthcare', 'ecommerce', 'iot', 'greentech', 'manufacturing', 'agriculture']
        cities = ['mumbai', 'delhi', 'bengaluru', 'pune', 'hyderabad']
        states = ['Maharashtra', 'Delhi', 'Karnataka', 'Telangana', 'Gujarat']

        mentor_emails = [
            'meghav@ecell.in', 'purvi@ecell.in', 'bhaveshchandra@ecell.in', 'chaitanya@ecell.in',
            'amit@ecell.in', 'ishant@ecell.in', 'mehul@ecell.in', 'mrunal@ecell.in', 
            'prathmesh@ecell.in', 'priyanshu@ecell.in', 'rohit@ecell.in', 'surendra@ecell.in',
            'sunil@ecell.in', 'kartikpadiya@ecell.in', 'mridul@ecell.in', 'ved@ecell.in',
            'niharika@ecell.in', 'msiddharth@ecell.in', 'ankit@ecell.in', 'vaibhavsemwal@ecell.in',
            'arnavgautam@ecell.in', 'dinesh@ecell.in'
        ]
        
        for i in range(22):
            email = mentor_emails[i]
            
            mentor, created = Mentor.objects.update_or_create(
                email=email,
                defaults={
                    'full_name': f"Mentor {i+1}",
                    'phone_number': f"98765{i:05d}",
                    'stakeholder_types': random.choice([['startup_mentor'], ['angel_investor'], ['vc'], ['other']]),
                    'city': random.choice(cities),
                    'state': random.choice(states),
                    'organization_name': f"Company {i+1}",
                    'association_interest': random.choice(['yes', 'maybe', 'no']),
                    'linkedin_url': f"https://linkedin.com/in/mentor{i+1}",
                    'networking_cities': random.sample(cities, random.randint(1, 3)),
                    'preferred_sector_1': random.choice(mentor_sectors),
                    'preferred_sector_2': random.choice(mentor_sectors),
                    'preferred_sector_3': random.choice(mentor_sectors),
                    'mentor_any_sector': random.choice([True, False]),
                    'join_mentorship_portal': random.choice([True, False]),
                }
            )
            mentor.set_password('pass1234')
            mentor.save()
            
            # Create EMN user for mentor
            emn_user, created = EMNUser.objects.update_or_create(
                email=email,
                defaults={
                    'user_type': 'mentor',
                    'is_email_verified': True,
                    'dashboard_access': True
                }
            )
            emn_user.set_password('pass1234')
            emn_user.save()
        
        # Create 22 startups
        startup_sectors = ['DLT/Blockchain', 'FMCG', 'Hardware', 'SAAS', 'Foodtech', 'Edutech', 'E-Commerce', 'Biotech', 'Healthcare', 'Fintech', 'AI', 'IoT', 'Energy', 'Manufacturing']
        startup_cities = ['Mumbai', 'Delhi', 'Bengaluru', 'Pune', 'Hyderabad', 'Chennai']

        startup_emails = [
            'bhaveshchandrakampa06@gmail.com', 'chaitanya007chiku@gmail.com', 'Bhartiya.amit33@gmail.com',
            'ishant7410@gmail.com', 'mehul13bafna@gmail.com', 'mpachpande28@gmail.com',
            'prathmeshwalimbe.ecell@gmail.com', 'priyanshugehlot011@gmail.com', 'iitbrohitsharma@gmail.com',
            '23b0722@gmail.com', 'sunil.ecell.iitb@gmail.com', 'kartikpadiya.ecell@gmail.com',
            'mridulmantri.ecell.iitb@gmail.com', 'vedpatil.ecell.iitb@gmail.com', 'niharikabansal724@gmail.com',
            'msiddharth.ecell@gmail.com', 'abagariya4@gmail.com', 'vaibhavsemwal741@gmail.com',
            '45arnav@gmail.com', 'dineshsahu.ecell@gmail.com', 'meghavsinghal@gmail.com', 'purvij2609@gmail.com'
        ]
        
        for i in range(22):
            email = startup_emails[i]
            
            # Create registration
            registration, created = Registration.objects.update_or_create(
                email=email,
                defaults={
                    'password': 'pass1234',
                    'first_name': f"Founder{i+1}",
                    'last_name': f"Lastname{i+1}",
                    'gender': random.choice(['Male', 'Female']),
                    'country_code': '+91',
                    'contact_number': f"87654{i:05d}",
                    'country': 'India',
                    'state': random.choice(states),
                    'city': random.choice(startup_cities),
                    'pin_code': f"{400000 + i}",
                    'current_professional_status': 'entrepreneur',
                    'educational_background': 'Engineering',
                    'linkedin_url': f"https://linkedin.com/in/startup{i+1}",
                    'where_did_you_hear': 'Social Media',
                    'eureka_id': f"EUR{3000 + i}",
                    'is_leader': True,
                    'idea_filled': True
                }
            )
            
            # Create idea
            sectors = random.sample(startup_sectors, 3)
            idea, created = Idea.objects.update_or_create(
                eureka_id=registration.eureka_id,
                defaults={
                    'startup_name': f"Startup{i+1} Solutions",
                    'sector_1': sectors[0],
                    'sector_2': sectors[1],
                    'sector_3': sectors[2],
                    'dpiit_registered': random.choice([True, False]),
                    'idea_description': f"Innovative solution for {sectors[0]} industry",
                    'track': 'General',
                    'website_url': f"https://startup{i+1}.com"
                }
            )
            
            # Create EMN user
            emn_user, created = EMNUser.objects.update_or_create(
                email=email,
                defaults={
                    'user_type': 'startup',
                    'is_email_verified': True,
                    'dashboard_access': True
                }
            )
            emn_user.set_password('pass1234')
            emn_user.save()
            
            # Create startup
            Startup.objects.update_or_create(
                user=emn_user,
                defaults={
                    'registration': registration,
                    'idea': idea
                }
            )
        
        self.stdout.write(
            self.style.SUCCESS('Created 22 mentors and 22 startups successfully')
        )
