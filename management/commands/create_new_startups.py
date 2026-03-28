from django.core.management.base import BaseCommand
from emn.models import Startup, EMNUser
from eureka25.models import Registration, Idea
import random

class Command(BaseCommand):
    help = 'Create new startups with correct sector values'

    def handle(self, *args, **options):
        # Delete existing test startups
        Startup.objects.filter(registration__email__contains='@emn.test').delete()
        Registration.objects.filter(email__contains='@emn.test').delete()
        EMNUser.objects.filter(email__contains='@emn.test', user_type='startup').delete()
        
        self.stdout.write('Creating new startups with correct sectors...')
        
        startup_data = [
            {'name': 'Arjun', 'lastname': 'Mehta', 'startup': 'CryptoFinance', 'sectors': ['DLT/Blockchain', 'Fintech']},
            {'name': 'Riya', 'lastname': 'Shah', 'startup': 'EduSaaS', 'sectors': ['Edutech', 'SAAS']},
            {'name': 'Karan', 'lastname': 'Verma', 'startup': 'HealthAI', 'sectors': ['Healthcare', 'AI']},
            {'name': 'Pooja', 'lastname': 'Jain', 'startup': 'EcoCommerce', 'sectors': ['E-Commerce', 'Energy']},
            {'name': 'Rahul', 'lastname': 'Kumar', 'startup': 'GreenTech Solutions', 'sectors': ['Energy', 'Manufacturing']},
            {'name': 'Neha', 'lastname': 'Pandey', 'startup': 'IoT Wearables', 'sectors': ['IoT', 'Wearable Tech']},
            {'name': 'Siddharth', 'lastname': 'Rao', 'startup': 'CloudSaaS', 'sectors': ['SAAS', 'IT']},
            {'name': 'Anjali', 'lastname': 'Singh', 'startup': 'AgriTech', 'sectors': ['Agriculture', 'IoT']},
            {'name': 'Vikram', 'lastname': 'Gupta', 'startup': 'DataAnalytics', 'sectors': ['Big Data', 'AI']},
            {'name': 'Priya', 'lastname': 'Sharma', 'startup': 'BioInnovate', 'sectors': ['Biotech', 'Healthcare']},
        ]
        
        cities = ['Mumbai', 'Delhi', 'Bengaluru', 'Pune', 'Hyderabad', 'Chennai']
        states = ['Maharashtra', 'Delhi', 'Karnataka', 'Telangana', 'Tamil Nadu']
        
        created = 0
        for i, data in enumerate(startup_data):
            email = f"startup{i+1}@emn.test"
            
            # Create registration
            registration = Registration.objects.create(
                email=email,
                password='password123',
                first_name=data['name'],
                last_name=data['lastname'],
                gender=['Male', 'Female'][i % 2],
                country_code='+91',
                contact_number=f"87654{i:05d}",
                country='India',
                state=random.choice(states),
                city=random.choice(cities),
                pin_code=f"{400000 + i}",
                current_professional_status='entrepreneur',
                educational_background='Engineering',
                linkedin_url=f"https://linkedin.com/in/{data['name'].lower()}{i+1}",
                where_did_you_hear='Social Media',
                eureka_id=f"EUR{2000 + i}",
                is_leader=True,
                idea_filled=True
            )
            
            # Create idea with correct sectors
            idea = Idea.objects.create(
                startup_name=data['startup'],
                eureka_id=registration.eureka_id,
                sector_1=data['sectors'][0],
                sector_2=data['sectors'][1] if len(data['sectors']) > 1 else None,
                sector_3=data['sectors'][2] if len(data['sectors']) > 2 else None,
                dpiit_registered=i % 3 == 0,
                idea_description=f"Innovative {data['startup']} solution for modern challenges",
                track='General',
                website_url=f"https://{data['startup'].lower().replace(' ', '')}.com"
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
            self.stdout.write(f'Created: {data["name"]} - {data["startup"]} ({data["sectors"]})')
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {created} new startups with correct sectors')
        )