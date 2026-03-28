from django.db import models
from django.core.validators import RegexValidator, URLValidator
from django.contrib.auth.models import AbstractBaseUser
from django.core.cache import cache
from .managers import CustomUserManager
import random
import string

class EmailOTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.email

class Mentor(AbstractBaseUser):
    # Link to EMNUser for unified user management
    user = models.OneToOneField('EMNUser', on_delete=models.CASCADE, related_name='mentor_profile', null=True, blank=True)

    # Step 1: Email Verification
    email = models.EmailField(unique=True)
    
    # Authentication fields
    is_active = models.BooleanField(default=True)
    password_changed = models.BooleanField(default=False)
    
    # Step 2: Basic Details & Preferences
    full_name = models.CharField(max_length=255)
    
    phone_regex = RegexValidator(
        regex=r'^\d{10}$',
        message="Phone number must be 10 digits without country code"
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=10)
    
    # Stakeholder Type - Using a JSONField to store multiple selections
    STAKEHOLDER_CHOICES = [
        ('angel_investor', 'Angel Investor'),
        ('startup_mentor', 'Startup Mentor'),
        ('vc', 'VC'),
        ('other', 'Other')
    ]
    stakeholder_types = models.JSONField(default=list)  # Will store list of selected types
    other_stakeholder_type = models.CharField(max_length=255, blank=True, null=True)
    
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    
    ASSOCIATION_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
        ('maybe', 'Maybe'),
        ('already_associated', 'Already Associated with Eureka! 2024')
    ]
    association_interest = models.CharField(max_length=50, choices=ASSOCIATION_CHOICES)
    
    linkedin_url = models.TextField()
    
    # Step 3: Mentorship & Participation
    CITY_CHOICES = [
        ('mumbai', 'Mumbai'),
        ('delhi', 'Delhi'),
        ('bengaluru', 'Bengaluru'),
        ('ahmedabad', 'Ahmedabad'),
        ('hyderabad', 'Hyderabad'),
        ('pune', 'Pune'),
        ('other', 'Other')
    ]
    networking_cities = models.JSONField(default=list)  # Will store list of selected cities
    other_networking_city = models.CharField(max_length=255, blank=True, null=True)
    
    SECTOR_CHOICES = [
        ('blockchain', 'Blockchain / Deep Learning / Web3'),
        ('fmcg', 'FMCG'),
        ('saas', 'SaaS'),
        ('foodtech', 'FoodTech'),
        ('edutech', 'EduTech'),
        ('fintech', 'FinTech'),
        ('biotech', 'BioTech'),
        ('ecommerce', 'E-Commerce'),
        ('healthcare', 'Healthcare'),
        ('consulting', 'Consulting'),
        ('agriculture', 'Agriculture'),
        ('iot', 'IoT'),
        ('manufacturing', 'Manufacturing'),
        ('greentech', 'GreenTech and Renewable Technology'),
        ('it', 'IT'),
        ('wearable', 'Wearable Tech'),
        ('chemical', 'Chemical'),
        ('bigdata', 'Big Data and Analysis'),
        ('social', 'Social Startups'),
        ('logistics', 'Logistics & Supply Chain')
    ]
    preferred_sector_1 = models.CharField(max_length=20, choices=SECTOR_CHOICES)
    preferred_sector_2 = models.CharField(max_length=20, choices=SECTOR_CHOICES)
    preferred_sector_3 = models.CharField(max_length=20, choices=SECTOR_CHOICES)
    
    mentor_any_sector = models.BooleanField(default=False)
    join_mentorship_portal = models.BooleanField(default=False)
    
    profile_image = models.ImageField(upload_to='emn/mentor_profiles/', blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"

    
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        self.is_active = True
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.full_name
    
    
# FAQs
class FAQ(models.Model):
    question = models.CharField(max_length=300)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-order']

    def __str__(self):
        return self.question


# Testimonials
class Testimonial(models.Model):
    ROLE_CHOICES = [
        ('mentor', 'Mentor'),
        ('startup', 'Startup'),
    ]

    name = models.CharField(max_length=100)
    position = models.CharField(max_length=150)
    profile_pic = models.ImageField(upload_to='emn/testimonial/', null=True, blank=True)
    message = models.TextField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.name} ({self.role})"


# Connected Mentors
class ConnectedMentor(models.Model):
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=150)
    location = models.CharField(max_length=150, null=True, blank=True)
    profile_pic = models.ImageField(upload_to='emn/mentor/', null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.name


# Past Eureka Winners
class PastWinner(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='emn/winner/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-order']

    def __str__(self):
        return self.name


# Contact Team/Profile
class ContactProfile(models.Model):
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, null=True, blank=True)
    linkedin = models.URLField(blank=True, null=True)
    profile_pic = models.ImageField(upload_to='emn/contact/', null=True, blank=True)

    class Meta:
        ordering = ['-id']
    
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



class GetAMentorEmail(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True, null=True)  # Optional
    message = models.TextField(blank=True, null=True)               # Optional note
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class PasswordResetToken(models.Model):
    email = models.EmailField()
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.email} - {self.token}"


class SiteSettings(models.Model):
    mentor_registration_enabled = models.BooleanField(
        default=True,
        help_text="Enable or disable mentor registration"
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SiteSettings.objects.exists():
            raise ValueError("Only one SiteSettings instance is allowed")
        super().save(*args, **kwargs)
        # Clear cache when settings are updated
        cache.delete('site_settings')
    
    @classmethod
    def get_settings(cls):
        """Get or create the single settings instance"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
    
    def __str__(self):
        return "Site Settings"


# EMN User Model (similar to NextcoUser)
class EMNUser(AbstractBaseUser):
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=20, choices=[
        ('mentor', 'Mentor'),
        ('startup', 'Startup')
    ])
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    dashboard_access = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    
    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return self.email


# Startup Model (using Eureka25 Registration)
class Startup(models.Model):
    user = models.OneToOneField(EMNUser, on_delete=models.CASCADE, related_name='startup_profile')
    registration = models.ForeignKey('eureka25.Registration', on_delete=models.CASCADE, related_name='emn_startup')
    idea = models.ForeignKey('eureka25.Idea', on_delete=models.CASCADE, related_name='emn_startup', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.registration.first_name} {self.registration.last_name} - {self.user.email}"


# Mentor-Startup Matching (intelligent algorithm-based)
class MentorMatch(models.Model):
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='matches')
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='matches')
    matching_sectors = models.JSONField(default=list)  # Common sectors
    match_score = models.FloatField(default=0.0)  # Algorithm-calculated score (0-100)
    score_factors = models.JSONField(default=dict)  # Breakdown of score factors
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('mentor', 'startup')
        ordering = ['-match_score', '-created_at']
    
    def __str__(self):
        return f"{self.mentor.full_name} <-> {self.startup.registration.first_name} ({self.match_score}%)"


# Connection System (like NextCo)
class ConnectionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('withdrawn', 'Withdrawn')
    ]
    
    sender = models.ForeignKey(EMNUser, on_delete=models.CASCADE, related_name='sent_requests')
    receiver = models.ForeignKey(EMNUser, on_delete=models.CASCADE, related_name='received_requests')
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    accept_token = models.CharField(max_length=64, blank=True, null=True)
    reject_token = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('sender', 'receiver')
    
    def __str__(self):
        return f"{self.sender} -> {self.receiver} ({self.status})"


class Connection(models.Model):
    user1 = models.ForeignKey(EMNUser, on_delete=models.CASCADE, related_name='connections_as_user1')
    user2 = models.ForeignKey(EMNUser, on_delete=models.CASCADE, related_name='connections_as_user2')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user1', 'user2')
    
    def __str__(self):
        return f"{self.user1} <-> {self.user2}"


# Booking System Models
class WeeklyAvailability(models.Model):
    startup = models.OneToOneField(Startup, on_delete=models.CASCADE, related_name='weekly_availability')
    slot_duration = models.IntegerField(default=30)  # in minutes
    availability_data = models.JSONField(default=dict)  # stores the complete availability structure
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.startup.registration.first_name} - Weekly Availability"


class AvailabilitySlot(models.Model):
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='availability_slots')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.startup.registration.first_name} - {self.start_time}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed')
    ]
    
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='bookings')
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='bookings')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    google_meet_link = models.URLField(blank=True, null=True)
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.mentor.full_name} -> {self.startup.registration.first_name}"


class GoogleCalendarToken(models.Model):
    user = models.OneToOneField(EMNUser, on_delete=models.CASCADE, related_name='google_token')
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expiry = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.email} - Google Calendar"


class MeetingTracker(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='meeting_tracks')
    action = models.CharField(max_length=30, choices=[
        ('clicked_link_mentor', 'Mentor Joined'),
        ('clicked_link_startup', 'Startup Joined'),
        ('clicked_link_unknown', 'Unknown Joined')
    ])
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.booking} - {self.action} at {self.timestamp}"


# New Meeting Management Models
class Meeting(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('reschedule_requested', 'Reschedule Requested'),
    ]
    
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='mentor_meetings')
    startup = models.ForeignKey(Startup, on_delete=models.CASCADE, related_name='startup_meetings')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    google_meet_link = models.URLField(blank=True, null=True)
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"Meeting: {self.mentor.full_name} - {self.startup.registration.first_name}"


class RescheduleRequest(models.Model):
    meeting = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name='reschedule_request')
    requested_by = models.ForeignKey(EMNUser, on_delete=models.CASCADE)
    requested_date = models.DateTimeField()
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Reschedule request for {self.meeting}"
    

