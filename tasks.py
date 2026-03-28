from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Booking
from .mailing import send_meeting_reminder_email

@shared_task
def send_meeting_reminders():
    """Send meeting reminders 24 hours and 1 hour before meetings"""
    now = timezone.now()
    
    # 24 hours reminder
    reminder_24h = now + timedelta(hours=24)
    bookings_24h = Booking.objects.filter(
        start_time__gte=reminder_24h - timedelta(minutes=30),
        start_time__lte=reminder_24h + timedelta(minutes=30),
        status='confirmed'
    )
    
    for booking in bookings_24h:
        send_meeting_reminder_email(
            booking=booking,
            reminder_type='24_hours'
        )
    
    # 1 hour reminder
    reminder_1h = now + timedelta(hours=1)
    bookings_1h = Booking.objects.filter(
        start_time__gte=reminder_1h - timedelta(minutes=15),
        start_time__lte=reminder_1h + timedelta(minutes=15),
        status='confirmed'
    )
    
    for booking in bookings_1h:
        send_meeting_reminder_email(
            booking=booking,
            reminder_type='1_hour'
        )
    
    return f"Sent reminders for {len(bookings_24h)} (24h) and {len(bookings_1h)} (1h) meetings"