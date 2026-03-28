from django.core.mail import EmailMultiAlternatives, send_mail, EmailMessage
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
EMN_EMAIL = "Eureka! Mentorship Network <emn@ecell.in>"

def send_otp_email(email, otp):
    """Send OTP verification email to the user"""
    subject = "Your OTP for Mentor Registration"
    html_content = render_to_string('emn/emails/otp_email.html', {'otp': otp})
    text_content = strip_tags(html_content)
    
    try:
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            EMN_EMAIL,
            [email]
        )
        msg.attach_alternative(html_content, "text/html")
        return msg.send()
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False

def send_registration_success_email(user_data):
    """Send confirmation email after successful registration"""
    subject = "Registration Successful - Welcome aboard as Eureka! mentor"
    context = {
        'full_name': user_data.get('full_name', 'User'),
        'email': user_data.get('email')
    }
    html_content = render_to_string('emn/emails/registration_success.html', context)
    text_content = strip_tags(html_content)
    
    try:
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            EMN_EMAIL,
            [user_data.get('email')]
        )
        msg.attach_alternative(html_content, "text/html")
        return msg.send()
    except Exception as e:
        logger.error(f"Failed to send registration success email to {user_data.get('email')}: {str(e)}")
        return False

def send_password_reset_email(email, token):
    """Send password reset token email"""
    subject = "Password Reset - Eureka! Mentorship Network"
    html_content = render_to_string('emn/emails/password_reset.html', {'token': token})
    text_content = strip_tags(html_content)
    
    try:
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            EMN_EMAIL,
            [email]
        )
        msg.attach_alternative(html_content, "text/html")
        return msg.send()
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        return False

def send_connection_request_email(sender_name, receiver_email, accept_url, reject_url, message=""):
    """Send connection request email with accept/reject links"""
    subject = f'New Connection Request from {sender_name} - EMN'
    
    context = {
        'sender_name': sender_name,
        'message': message,
        'accept_url': accept_url,
        'reject_url': reject_url
    }
    html_content = render_to_string('emn/emails/connection_request.html', context)
    
    text_content = f"""
    Hi there,
    
    You have a new connection request from {sender_name} on the Eureka! Mentorship Network.
    {f'Message: {message}' if message else ''}
    
    Accept: {accept_url}
    Reject: {reject_url}
    
    For any queries, contact:
    Rohit | +91 80583 52005
    Priyanshu | +91 63761 61627
    Events & PR Heads
    
    Warm regards,
    Team E-Cell, IIT Bombay
    """
    
    try:
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            EMN_EMAIL,
            [receiver_email]
        )
        msg.attach_alternative(html_content, "text/html")
        return msg.send()
    except Exception as e:
        logger.error(f"Failed to send connection request email to {receiver_email}: {str(e)}")
        return False

def send_mentor_interest_email(name, email):
    """Send email when someone shows interest in getting a mentor"""
    subject = "Thanks for showing interest in getting a mentor!"
    html_content = render_to_string('emn/emails/mentor_interest.html', {'name': name})
    text_content = strip_tags(html_content)
    
    try:
        mail = EmailMessage(
            subject=subject,
            body=html_content,
            from_email=EMN_EMAIL,
            to=[email],
            cc=["eureka25@ecell.in"],
        )
        mail.content_subtype = "html"
        return mail.send(fail_silently=False)
    except Exception as e:
        logger.error(f"Failed to send mentor interest email to {email}: {str(e)}")
        return False

def send_direct_message_email(sender, receiver, subject_text, message_text, send_copy=False):
    """Send direct message email between connected users"""
    try:
        sender_name = get_user_display_name(sender)
        recipient_name = get_user_display_name(receiver)
        
        print(f"DEBUG: Sending email from {sender.email} to {receiver.email}")
        
        email_body = f"""Hi {recipient_name},

You have received a message from {sender_name} via EMN:

{message_text}

Best regards,
The EMN Team"""
        
        # Send main email to receiver
        result = send_mail(
            subject=f"[EMN] {subject_text}",
            message=email_body,
            from_email=EMN_EMAIL,
            recipient_list=[receiver.email]
        )
        print(f"DEBUG: Main email sent to {receiver.email}, result: {result}")
        
        # Send copy to sender only if requested
        if send_copy:
            copy_result = send_mail(
                subject=f"[EMN] Copy: {subject_text}",
                message=f"This is a copy of the email you sent to {recipient_name}:\n\n{email_body}",
                from_email=EMN_EMAIL,
                recipient_list=[sender.email],
                fail_silently=True
            )
            print(f"DEBUG: Copy email sent to {sender.email}, result: {copy_result}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send direct message email: {str(e)}")
        return False

def get_user_display_name(user):
    """Get display name for user from their profile"""
    try:
        if hasattr(user, 'mentor_profile'):
            mentor = user.mentor_profile
            return mentor.full_name or user.email
        elif hasattr(user, 'startup_profile'):
            startup = user.startup_profile
            return f"{startup.registration.first_name} {startup.registration.last_name}" or user.email
        # Try to get mentor by email
        from .models import Mentor
        try:
            mentor = Mentor.objects.get(email=user.email)
            return mentor.full_name or user.email
        except Mentor.DoesNotExist:
            pass
        # Try to get startup by user
        from .models import Startup
        try:
            startup = Startup.objects.get(user=user)
            return f"{startup.registration.first_name} {startup.registration.last_name}" or user.email
        except Startup.DoesNotExist:
            pass
    except:
        pass
    return user.email if hasattr(user, 'email') else str(user)

def send_personalized_meeting_invitation_email(mentor_email, mentor_name, startup_email, startup_name, meeting_time, mentor_tracking_link, startup_tracking_link):
    """Send beautiful meeting invitation email from EMN"""
    import pytz
    
    # Convert to IST and format meeting time
    ist = pytz.timezone('Asia/Kolkata')
    meeting_time_ist = meeting_time.astimezone(ist)
    formatted_time = meeting_time_ist.strftime("%A, %B %d, %Y at %I:%M %p IST")
    
    context = {
        'mentor_name': mentor_name,
        'startup_name': startup_name,
        'formatted_time': formatted_time
    }
    
    # Plain text version
    text_message = f"""
EMN - ENTREPRENEUR MENTORSHIP NETWORK
=====================================

MEETING SCHEDULED

Meeting Details:
Mentor: {mentor_name}
Startup: {startup_name}
Date & Time: {formatted_time}
Duration: 30 minutes

JOIN MEETING:
{{tracking_link}}

This meeting was organized by EMN - Eureka! Mentorship Network
Connecting entrepreneurs with experienced mentors for business growth

© 2025 Eureka! Mentorship Network
"""
    
    try:
        # Send to mentor
        mentor_context = {**context, 'tracking_link': mentor_tracking_link}
        mentor_html = render_to_string('emn/emails/meeting_invitation.html', mentor_context)
        mentor_text = text_message.format(tracking_link=mentor_tracking_link)
        
        send_mail(
            subject=f"[EMN] Meeting with {startup_name} - {formatted_time}",
            message=mentor_text,
            from_email=EMN_EMAIL,
            recipient_list=[mentor_email],
            html_message=mentor_html,
            fail_silently=False,
        )
        
        # Send to startup
        startup_context = {**context, 'tracking_link': startup_tracking_link}
        startup_html = render_to_string('emn/emails/meeting_invitation.html', startup_context)
        startup_text = text_message.format(tracking_link=startup_tracking_link)
        
        send_mail(
            subject=f"[EMN] Meeting with {mentor_name} - {formatted_time}",
            message=startup_text,
            from_email=EMN_EMAIL,
            recipient_list=[startup_email],
            html_message=startup_html,
            fail_silently=False,
        )
        
        print(f"DEBUG: Personalized meeting invitations sent to {mentor_email} and {startup_email}")
        return True
    except Exception as e:
        print(f"DEBUG: Failed to send personalized meeting invitations: {e}")
        return False


def send_meeting_reminder_email(booking, reminder_type):
    """Send meeting reminder email"""
    from django.core.mail import send_mail
    from django.conf import settings
    import pytz
    
    # Convert to IST
    ist = pytz.timezone('Asia/Kolkata')
    meeting_time_ist = booking.start_time.astimezone(ist)
    formatted_time = meeting_time_ist.strftime("%A, %B %d, %Y at %I:%M %p IST")
    
    # Create tracking links
    meet_id = booking.google_meet_link.split('/')[-1] if booking.google_meet_link else booking.id
    from django.conf import settings
    mentor_link = f"{settings.BASE_URL}/emn/join-meeting/{meet_id}/?user=mentor"
    startup_link = f"{settings.BASE_URL}/emn/join-meeting/{meet_id}/?user=startup"
    
    if reminder_type == '24_hours':
        subject_prefix = "Reminder: Meeting Tomorrow"
        time_text = "Your meeting is scheduled for tomorrow"
    else:
        subject_prefix = "Meeting Starting Soon"
        time_text = "Your meeting starts in 1 hour"
    
    # Send to mentor
    mentor_subject = f"{subject_prefix} - {booking.startup.registration.first_name} {booking.startup.registration.last_name}"
    mentor_message = f"""
    Hi {booking.mentor.full_name},
    
    {time_text}:
    Date & Time: {formatted_time}
    With: {booking.startup.registration.first_name} {booking.startup.registration.last_name}
    
    Join Meeting: {mentor_link}
    
    Best regards,
    EMN Team
    """
    
    # Send to startup
    startup_subject = f"{subject_prefix} - {booking.mentor.full_name}"
    startup_message = f"""
    Hi {booking.startup.registration.first_name},
    
    {time_text}:
    Date & Time: {formatted_time}
    With: {booking.mentor.full_name}
    
    Join Meeting: {startup_link}
    
    Best regards,
    EMN Team
    """
    
    try:
        # Send to mentor
        send_mail(
            subject=mentor_subject,
            message=mentor_message,
            from_email=EMN_EMAIL,
            recipient_list=[booking.mentor.email],
            fail_silently=False,
        )
        
        # Send to startup
        send_mail(
            subject=startup_subject,
            message=startup_message,
            from_email=EMN_EMAIL,
            recipient_list=[booking.startup.user.email],
            fail_silently=False,
        )
        
        print(f"DEBUG: Reminder sent for booking {booking.id} ({reminder_type})")
        return True
    except Exception as e:
        print(f"DEBUG: Failed to send reminder for booking {booking.id}: {e}")
        return False

def send_reschedule_notification_email(meeting, reschedule_request):
    """Send email notification to mentor about reschedule request"""
    subject = f"Reschedule Request for Meeting with {meeting.startup.registration.first_name} {meeting.startup.registration.last_name}"
    
    context = {
        'mentor_name': meeting.mentor.full_name,
        'startup_name': f"{meeting.startup.registration.first_name} {meeting.startup.registration.last_name}",
        'original_time': meeting.start_time.strftime('%B %d, %Y at %I:%M %p IST'),
        'requested_time': reschedule_request.requested_date.strftime('%B %d, %Y at %I:%M %p IST'),
        'reason': reschedule_request.reason
    }
    
    html_content = render_to_string('emn/emails/reschedule_notification.html', context)
    text_content = strip_tags(html_content)
    
    try:
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            EMN_EMAIL,
            [meeting.mentor.email]
        )
        msg.attach_alternative(html_content, "text/html")
        return msg.send()
    except Exception as e:
        logger.error(f"Failed to send reschedule notification email: {str(e)}")
        return False

def send_meeting_update_email(meeting, action):
    """Send email to startup when mentor reschedules or cancels meeting"""
    startup_email = meeting.startup.user.email
    startup_name = f"{meeting.startup.registration.first_name} {meeting.startup.registration.last_name}"
    mentor_name = meeting.mentor.full_name
    
    if action == 'rescheduled':
        subject = f"Meeting Rescheduled by {mentor_name}"
        new_time = meeting.start_time.strftime('%B %d, %Y at %I:%M %p IST')
    else:
        subject = f"Meeting Cancelled by {mentor_name}"
        new_time = None
    
    context = {
        'startup_name': startup_name,
        'mentor_name': mentor_name,
        'action': action,
        'new_time': new_time
    }
    
    html_content = render_to_string('emn/emails/meeting_update.html', context)
    text_content = strip_tags(html_content)
    
    try:
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            EMN_EMAIL,
            [startup_email]
        )
        msg.attach_alternative(html_content, "text/html")
        return msg.send()
    except Exception as e:
        logger.error(f"Failed to send meeting update email: {str(e)}")
        return False