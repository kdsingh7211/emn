from django.core.management.base import BaseCommand
from emn.models import EMNUser

class Command(BaseCommand):
    help = 'Manage dashboard access for EMN users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enable',
            nargs='+',
            help='Enable dashboard access for specified email addresses'
        )
        parser.add_argument(
            '--disable',
            nargs='+',
            help='Disable dashboard access for specified email addresses'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all users and their dashboard access status'
        )
        parser.add_argument(
            '--enable-all',
            action='store_true',
            help='Enable dashboard access for all users'
        )
        parser.add_argument(
            '--disable-all',
            action='store_true',
            help='Disable dashboard access for all users'
        )
        parser.add_argument(
            '--enable-mentors',
            action='store_true',
            help='Enable dashboard access for all mentors only'
        )
        parser.add_argument(
            '--enable-startups',
            action='store_true',
            help='Enable dashboard access for all startups only'
        )
        parser.add_argument(
            '--disable-mentors',
            action='store_true',
            help='Disable dashboard access for all mentors only'
        )
        parser.add_argument(
            '--disable-startups',
            action='store_true',
            help='Disable dashboard access for all startups only'
        )
        parser.add_argument(
            '--filter-type',
            choices=['mentor', 'startup'],
            help='Filter list by user type'
        )
        parser.add_argument(
            '--filter-access',
            choices=['enabled', 'disabled'],
            help='Filter list by access status'
        )

    def handle(self, *args, **options):
        if options['enable']:
            for email in options['enable']:
                try:
                    user = EMNUser.objects.get(email=email)
                    user.dashboard_access = True
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Enabled dashboard access for {email}')
                    )
                except EMNUser.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'User {email} not found')
                    )

        if options['disable']:
            for email in options['disable']:
                try:
                    user = EMNUser.objects.get(email=email)
                    user.dashboard_access = False
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Disabled dashboard access for {email}')
                    )
                except EMNUser.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'User {email} not found')
                    )

        if options['enable_all']:
            count = EMNUser.objects.update(dashboard_access=True)
            self.stdout.write(
                self.style.SUCCESS(f'Enabled dashboard access for {count} users')
            )

        if options['disable_all']:
            count = EMNUser.objects.update(dashboard_access=False)
            self.stdout.write(
                self.style.SUCCESS(f'Disabled dashboard access for {count} users')
            )

        if options['enable_mentors']:
            count = EMNUser.objects.filter(user_type='mentor').update(dashboard_access=True)
            self.stdout.write(
                self.style.SUCCESS(f'Enabled dashboard access for {count} mentors')
            )

        if options['enable_startups']:
            count = EMNUser.objects.filter(user_type='startup').update(dashboard_access=True)
            self.stdout.write(
                self.style.SUCCESS(f'Enabled dashboard access for {count} startups')
            )

        if options['disable_mentors']:
            count = EMNUser.objects.filter(user_type='mentor').update(dashboard_access=False)
            self.stdout.write(
                self.style.SUCCESS(f'Disabled dashboard access for {count} mentors')
            )

        if options['disable_startups']:
            count = EMNUser.objects.filter(user_type='startup').update(dashboard_access=False)
            self.stdout.write(
                self.style.SUCCESS(f'Disabled dashboard access for {count} startups')
            )

        if options['list']:
            users = EMNUser.objects.all()
            
            # Apply filters
            if options['filter_type']:
                users = users.filter(user_type=options['filter_type'])
            
            if options['filter_access']:
                access_filter = options['filter_access'] == 'enabled'
                users = users.filter(dashboard_access=access_filter)
            
            users = users.order_by('user_type', 'email')
            
            # Display summary
            total_users = EMNUser.objects.count()
            enabled_users = EMNUser.objects.filter(dashboard_access=True).count()
            disabled_users = total_users - enabled_users
            
            self.stdout.write('\nDashboard Access Summary:')
            self.stdout.write('=' * 60)
            self.stdout.write(f'Total Users: {total_users}')
            self.stdout.write(f'Access Enabled: {enabled_users}')
            self.stdout.write(f'Access Disabled: {disabled_users}')
            
            self.stdout.write('\nUser List:')
            self.stdout.write('=' * 60)
            for user in users:
                status = '✓' if user.dashboard_access else '✗'

            
            if not users.exists():
                self.stdout.write('No users found matching the criteria.')