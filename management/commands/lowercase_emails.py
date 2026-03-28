from django.core.management.base import BaseCommand
from django.db import transaction
from emn.models import EMNUser, Mentor, EmailOTP, GetAMentorEmail, PasswordResetToken, ContactProfile
from eureka25.models import Registration, EmailOtp, Contact, TeamInvite, Judge


class Command(BaseCommand):
    help = 'Convert all emails to lowercase in EMN and Eureka25 apps'

    def handle(self, *args, **options):
        updated_count = 0
        
        with transaction.atomic():
            # EMN models
            for model in [EMNUser, Mentor, EmailOTP, GetAMentorEmail, PasswordResetToken, ContactProfile]:
                for obj in model.objects.all():
                    if obj.email and obj.email != obj.email.lower():
                        lowercase_email = obj.email.lower()
                        # Check if lowercase version already exists
                        if model.objects.filter(email=lowercase_email).exclude(id=obj.id).exists():
                            self.stdout.write(f'Skipping {model.__name__} {obj.email} - lowercase version exists')
                            continue
                        obj.email = lowercase_email
                        obj.save()
                        updated_count += 1
                        self.stdout.write(f'Updated {model.__name__}: {obj.email}')
            
            # Eureka25 models
            for model in [Registration, EmailOtp, Contact, Judge]:
                for obj in model.objects.all():
                    if obj.email and obj.email != obj.email.lower():
                        lowercase_email = obj.email.lower()
                        # Check if lowercase version already exists
                        if model.objects.filter(email=lowercase_email).exclude(id=obj.id).exists():
                            self.stdout.write(f'Skipping {model.__name__} {obj.email} - lowercase version exists')
                            continue
                        obj.email = lowercase_email
                        obj.save()
                        updated_count += 1
                        self.stdout.write(f'Updated {model.__name__}: {obj.email}')
            
            # TeamInvite has two email fields
            for obj in TeamInvite.objects.all():
                updated = False
                skip = False
                
                if obj.email and obj.email != obj.email.lower():
                    lowercase_email = obj.email.lower()
                    if TeamInvite.objects.filter(email=lowercase_email).exclude(id=obj.id).exists():
                        self.stdout.write(f'Skipping TeamInvite {obj.email} - lowercase version exists')
                        skip = True
                    else:
                        obj.email = lowercase_email
                        updated = True
                        
                if not skip and obj.added_by_email and obj.added_by_email != obj.added_by_email.lower():
                    obj.added_by_email = obj.added_by_email.lower()
                    updated = True
                    
                if updated and not skip:
                    obj.save()
                    updated_count += 1
                    self.stdout.write(f'Updated TeamInvite: {obj.email}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully converted {updated_count} emails to lowercase')
        )