from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from django.contrib import messages
from django.core.management import call_command
from .models import *

@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ['mentor', 'startup', 'start_time', 'end_time', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['mentor__full_name', 'startup__registration__first_name', 'startup__registration__last_name']
    ordering = ['-start_time']

@admin.register(RescheduleRequest)
class RescheduleRequestAdmin(admin.ModelAdmin):
    list_display = ['meeting', 'requested_by', 'requested_date', 'created_at']
    list_filter = ['created_at']
    search_fields = ['meeting__mentor__full_name', 'meeting__startup__registration__first_name', 'reason']
    ordering = ['-created_at']

@admin.register(MeetingTracker)
class MeetingTrackerAdmin(admin.ModelAdmin):
    list_display = ['meeting_schedule', 'join_status', 'join_time']
    list_filter = ['action', 'booking__start_time']
    search_fields = ['booking__mentor__full_name', 'booking__startup__registration__first_name']
    readonly_fields = ['booking', 'action', 'timestamp']
    ordering = ['-booking__start_time']
    list_per_page = 25
    
    def meeting_schedule(self, obj):
        import pytz
        ist = pytz.timezone('Asia/Kolkata')
        meeting_time = obj.booking.start_time.astimezone(ist)
        formatted_time = meeting_time.strftime('%d %b %Y, %I:%M %p IST')
        return f"{obj.booking.mentor.full_name} & {obj.booking.startup.registration.first_name} {obj.booking.startup.registration.last_name} - {formatted_time}"
    meeting_schedule.short_description = 'Scheduled Meeting'
    
    def join_status(self, obj):
        action_map = {
            'clicked_link_mentor': 'Mentor Joined',
            'clicked_link_startup': 'Startup Joined', 
            'clicked_link_unknown': 'Someone Joined'
        }
        return action_map.get(obj.action, obj.action)
    join_status.short_description = 'Who Joined'
    
    def join_time(self, obj):
        import pytz
        ist = pytz.timezone('Asia/Kolkata')
        join_time_ist = obj.timestamp.astimezone(ist)
        return join_time_ist.strftime('%d %b %Y, %I:%M %p IST')
    join_time.short_description = 'Joined At'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return True

@admin.register(EMNUser)
class EMNUserAdmin(ImportExportModelAdmin):
    list_display = ['email', 'user_type', 'is_email_verified', 'is_active', 'dashboard_access', 'created_at']
    list_filter = ['user_type', 'is_email_verified', 'is_active', 'dashboard_access', 'mentor_profile__password_changed']
    search_fields = ['email']
    readonly_fields = ['created_at', 'updated_at']
    exclude = ['password', 'last_login']  # Exclude unused authentication fields
    actions = ['enable_dashboard_access', 'disable_dashboard_access', 'enable_all_mentors', 'enable_all_startups', 'disable_all_mentors', 'disable_all_startups']
    
    @admin.action(description='Enable dashboard access for selected users')
    def enable_dashboard_access(self, request, queryset):
        count = queryset.update(dashboard_access=True)
        messages.success(request, f'Enabled dashboard access for {count} users')
    
    @admin.action(description='Disable dashboard access for selected users')
    def disable_dashboard_access(self, request, queryset):
        count = queryset.update(dashboard_access=False)
        messages.success(request, f'Disabled dashboard access for {count} users')
    
    @admin.action(description='Enable dashboard access for ALL mentors')
    def enable_all_mentors(self, request, queryset):
        count = EMNUser.objects.filter(user_type='mentor').update(dashboard_access=True)
        messages.success(request, f'Enabled dashboard access for {count} mentors')
    
    @admin.action(description='Enable dashboard access for ALL startups')
    def enable_all_startups(self, request, queryset):
        count = EMNUser.objects.filter(user_type='startup').update(dashboard_access=True)
        messages.success(request, f'Enabled dashboard access for {count} startups')
    
    @admin.action(description='Disable dashboard access for ALL mentors')
    def disable_all_mentors(self, request, queryset):
        count = EMNUser.objects.filter(user_type='mentor').update(dashboard_access=False)
        messages.success(request, f'Disabled dashboard access for {count} mentors')
    
    @admin.action(description='Disable dashboard access for ALL startups')
    def disable_all_startups(self, request, queryset):
        count = EMNUser.objects.filter(user_type='startup').update(dashboard_access=False)
        messages.success(request, f'Disabled dashboard access for {count} startups')

@admin.register(Mentor)
class MentorAdmin(ImportExportModelAdmin):
    list_display = ['full_name', 'email', 'organization_name', 'city', 'is_active']
    list_filter = ['is_active', 'city', 'preferred_sector_1']
    search_fields = ['full_name', 'email', 'organization_name']

@admin.register(Startup)
class StartupAdmin(ImportExportModelAdmin):
    list_display = ['get_name', 'user', 'get_startup_name', 'created_at']
    search_fields = ['user__email', 'registration__first_name', 'registration__last_name', 'registration__eureka_id', 'idea__startup_name', 'idea__idea_id']
    autocomplete_fields = ['user', 'registration', 'idea']
    
    def get_name(self, obj):
        return f"{obj.registration.first_name} {obj.registration.last_name}"
    get_name.short_description = 'Name'
    
    def get_startup_name(self, obj):
        return obj.idea.startup_name if obj.idea else 'No Idea'
    get_startup_name.short_description = 'Startup Name'

@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(ImportExportModelAdmin):
    list_display = ['sender', 'receiver', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['sender__email', 'receiver__email']

@admin.register(Connection)
class ConnectionAdmin(ImportExportModelAdmin):
    list_display = ['user1', 'user2', 'created_at']
    search_fields = ['user1__email', 'user2__email']

@admin.register(MentorMatch)
class MentorMatchAdmin(ImportExportModelAdmin):
    list_display = ['mentor', 'startup', 'match_score', 'created_at']
    list_filter = ['match_score', 'created_at']
    search_fields = ['mentor__full_name', 'startup__registration__first_name']
    actions = [ 'create_matches', 'recreate_matches']
    
    # def changelist_view(self, request, extra_context=None):
    #     # Auto-run create_matches command when opening admin
    #     if not request.GET.get('auto_run_done'):
    #         try:
    #             call_command('create_matches')
    #             messages.success(request, 'Matches auto-updated on page load!')
    #         except Exception as e:
    #             messages.error(request, f'Auto-update failed: {str(e)}')
    #     return super().changelist_view(request, extra_context)
    
    def create_matches(self, request, queryset):
        try:
            call_command('create_matches')
            messages.success(request, 'Matches created successfully!')
        except Exception as e:
            messages.error(request, f'Error creating matches: {str(e)}')
    create_matches.short_description = "Create new matches (keep existing)"
    
    def recreate_matches(self, request, queryset):
        try:
            call_command('create_matches', '--clear-existing')
            messages.success(request, 'All matches recreated successfully!')
        except Exception as e:
            messages.error(request, f'Error recreating matches: {str(e)}')
    recreate_matches.short_description = "Recreate all matches (clear existing first)"

@admin.register(Booking)
class BookingAdmin(ImportExportModelAdmin):
    list_display = ['id', 'mentor_name', 'startup_name', 'start_time', 'status', 'click_count']
    list_filter = ['status', 'start_time', 'mentor', 'startup']
    search_fields = ['mentor__full_name', 'startup__registration__first_name', 'startup__registration__last_name']
    readonly_fields = ['created_at', 'click_count']
    
    def mentor_name(self, obj):
        return obj.mentor.full_name
    mentor_name.short_description = 'Mentor'
    
    def startup_name(self, obj):
        return f"{obj.startup.registration.first_name} {obj.startup.registration.last_name}"
    startup_name.short_description = 'Startup'
    
    def click_count(self, obj):
        return obj.meeting_tracks.count()
    click_count.short_description = 'Total Clicks'

# Custom admin actions for site-wide operations
class SiteAdminActions:
    @admin.action(description='Create mentor-startup matches')
    def create_matches_action(self, request, queryset):
        try:
            call_command('create_matches')
            messages.success(request, 'Matches created successfully!')
        except Exception as e:
            messages.error(request, f'Error creating matches: {str(e)}')
    
    @admin.action(description='Recreate all matches (clear existing)')
    def recreate_matches_action(self, request, queryset):
        try:
            call_command('create_matches', '--clear-existing')
            messages.success(request, 'All matches recreated successfully!')
        except Exception as e:
            messages.error(request, f'Error recreating matches: {str(e)}')

# Add actions to Mentor admin
class MentorAdminWithActions(MentorAdmin, SiteAdminActions):
    actions = ['create_matches_action', 'recreate_matches_action']

# Add actions to Startup admin  
class StartupAdminWithActions(StartupAdmin, SiteAdminActions):
    actions = ['create_matches_action', 'recreate_matches_action', 'create_emn_startups']
    
    @admin.action(description='Create EMN startups from eureka25 registrations')
    def create_emn_startups(self, request, queryset):
        from eureka25.models import Registration, Idea
        
        registrations = Registration.objects.filter(emn_access=True)
        created_count = 0
        
        for registration in registrations:
            emn_user, user_created = EMNUser.objects.get_or_create(
                email=registration.email,
                defaults={'user_type': 'startup'}
            )
            
            startup, startup_created = Startup.objects.get_or_create(
                registration=registration,
                defaults={'user': emn_user}
            )
            
            try:
                idea = Idea.objects.filter(eureka_id=registration.eureka_id).first()
                if idea:
                    startup.idea = idea
                    startup.save()
            except Idea.DoesNotExist:
                pass
            
            if startup_created:
                created_count += 1
        
        messages.success(request, f'Successfully created {created_count} EMN startups')

# Re-register with actions
admin.site.unregister(Mentor)
admin.site.unregister(Startup)
admin.site.register(Mentor, MentorAdminWithActions)
admin.site.register(Startup, StartupAdminWithActions)

# Register other existing models
admin.site.register(EmailOTP)
admin.site.register(FAQ)
admin.site.register(Testimonial)
admin.site.register(ConnectedMentor)
admin.site.register(PastWinner)
admin.site.register(ContactProfile)
admin.site.register(GetAMentorEmail)
admin.site.register(PasswordResetToken)
admin.site.register(SiteSettings)