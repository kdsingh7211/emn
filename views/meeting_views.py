from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from ..models import Meeting, RescheduleRequest, Mentor, Startup, EMNUser, AvailabilitySlot
from ..serializers import MeetingSerializer
from ..mailing import send_reschedule_notification_email, send_meeting_update_email
from ..custom_auth import EMNUserAuthentication
import uuid

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def list_meetings(request):
    """List all meetings for the authenticated user"""
    user = request.user
    
    # Get user's mentor or startup profile
    try:
        if user.user_type == 'mentor':
            mentor = Mentor.objects.get(email=user.email)
            meetings = Meeting.objects.filter(mentor=mentor)
        elif user.user_type == 'startup':
            startup = Startup.objects.get(user=user)
            meetings = Meeting.objects.filter(startup=startup)
        else:
            return Response({'meetings': []})
    except (Mentor.DoesNotExist, Startup.DoesNotExist):
        return Response({'meetings': []})
    
    meetings = meetings.order_by('-start_time')
    serializer = MeetingSerializer(meetings, many=True, context={'request': request})
    return Response({'meetings': serializer.data})

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def book_meeting(request):
    """Book a new meeting"""
    data = request.data
    startup_id = data.get('startup_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([startup_id, start_time, end_time]):
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        startup = Startup.objects.get(id=startup_id)
        
        # Handle both EMNUser and direct Mentor authentication
        if hasattr(request.user, 'user_type'):
            # EMNUser authentication
            mentor = Mentor.objects.get(email=request.user.email)
        else:
            # Direct Mentor authentication - create EMNUser
            mentor = request.user  # request.user is already a Mentor
            emn_user, created = EMNUser.objects.get_or_create(
                email=mentor.email,
                defaults={
                    'user_type': 'mentor',
                    'is_email_verified': True,
                    'is_active': True
                }
            )
        
        # Check for mentor conflicts
        mentor_conflicts = Meeting.objects.filter(
            mentor=mentor,
            start_time__lt=end_time,
            end_time__gt=start_time,
            status='scheduled'
        )
        
        # Check for startup conflicts
        startup_conflicts = Meeting.objects.filter(
            startup=startup,
            start_time__lt=end_time,
            end_time__gt=start_time,
            status='scheduled'
        )
        
        if mentor_conflicts.exists() or startup_conflicts.exists():
            return Response({'error': 'Time slot already booked'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to create Google Calendar event
        meet_link = f"https://meet.google.com/{uuid.uuid4().hex[:10]}"
        event_id = None
        
        try:
            from ..google_calendar import GoogleCalendarService
            from ..models import GoogleCalendarToken
            
            # Try to get mentor's Google Calendar token
            token = GoogleCalendarToken.objects.get(user__email=mentor.email)
            calendar_service = GoogleCalendarService()
            
            meeting_data = calendar_service.create_meeting(
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                start_time=start_time,
                end_time=end_time,
                attendees=[mentor.email, startup.user.email],
                summary=f"Meeting: {mentor.full_name} & {startup.registration.first_name} {startup.registration.last_name}",
                booking_id=None
            )
            
            meet_link = meeting_data['actual_meet_link']
            event_id = meeting_data['event_id']
        except Exception as e:
            print(f"DEBUG: Failed to create Google Calendar event: {e}")
        
        meeting = Meeting.objects.create(
            mentor=mentor,
            startup=startup,
            start_time=start_time,
            end_time=end_time,
            google_meet_link=meet_link,
            google_event_id=event_id
        )
        
        # Send email notifications with trackable links
        from ..mailing import send_personalized_meeting_invitation_email
        from django.utils.dateparse import parse_datetime
        
        # Create separate tracking links for mentor and startup
        meet_id = meet_link.split('/')[-1] if meet_link else meeting.id
        from django.conf import settings
        mentor_tracking_link = f"{settings.BASE_URL}/emn/join-meeting/{meet_id}/?user=mentor"
        startup_tracking_link = f"{settings.BASE_URL}/emn/join-meeting/{meet_id}/?user=startup"
        
        # Parse start_time for email formatting
        meeting_datetime = parse_datetime(start_time) if isinstance(start_time, str) else start_time
        
        # Send personalized emails
        send_personalized_meeting_invitation_email(
            mentor_email=mentor.email,
            mentor_name=mentor.full_name,
            startup_email=startup.user.email,
            startup_name=f"{startup.registration.first_name} {startup.registration.last_name}",
            meeting_time=meeting_datetime,
            mentor_tracking_link=mentor_tracking_link,
            startup_tracking_link=startup_tracking_link
        )
        
        return Response({
            'message': 'Meeting booked successfully',
            'meeting_id': meeting.id,
            'meet_link': meet_link
        })
        
    except Startup.DoesNotExist:
        return Response({'error': 'Startup not found'}, status=status.HTTP_404_NOT_FOUND)
    except Mentor.DoesNotExist:
        return Response({'error': 'Mentor profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def get_booked_slots(request, startup_id):
    """Get booked slots for a startup to hide from calendar"""
    try:
        startup = Startup.objects.get(id=startup_id)
        
        # Get all booked meetings for this startup (both as mentor and startup)
        booked_meetings = Meeting.objects.filter(
            models.Q(startup=startup) | models.Q(mentor__email=request.user.email),
            status__in=['scheduled', 'reschedule_requested'],
            start_time__gte=timezone.now()
        ).distinct()
        
        booked_slots = []
        for meeting in booked_meetings:
            booked_slots.append({
                'start_time': meeting.start_time.isoformat(),
                'end_time': meeting.end_time.isoformat(),
                'meeting_id': meeting.id
            })
        
        return Response({'booked_slots': booked_slots})
        
    except Startup.DoesNotExist:
        return Response({'error': 'Startup not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def request_reschedule(request):
    """Startup requests to reschedule a meeting"""
    data = request.data
    meeting_id = data.get('meeting_id')
    requested_date = data.get('requested_date')
    reason = data.get('reason')
    
    if not all([meeting_id, requested_date, reason]):
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        startup = Startup.objects.get(user=request.user)
        meeting = get_object_or_404(Meeting, id=meeting_id, startup=startup)
        
        if meeting.status not in ['scheduled', 'reschedule_requested']:
            return Response({'error': 'Cannot reschedule this meeting'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or update reschedule request
        from django.utils.dateparse import parse_datetime
        parsed_date = parse_datetime(requested_date)
        if not parsed_date:
            return Response({'error': 'Invalid date format'}, status=status.HTTP_400_BAD_REQUEST)
        
        reschedule_request, created = RescheduleRequest.objects.get_or_create(
            meeting=meeting,
            defaults={
                'requested_by': request.user,
                'requested_date': parsed_date,
                'reason': reason
            }
        )
        
        if not created:
            reschedule_request.requested_date = parsed_date
            reschedule_request.reason = reason
            reschedule_request.save()
        

        
        meeting.status = 'reschedule_requested'
        meeting.save()
        
        # Send email to mentor
        send_reschedule_notification_email(meeting, reschedule_request)
        
        return Response({'message': 'Reschedule request sent successfully'})
        
    except Startup.DoesNotExist:
        return Response({'error': 'Startup profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def reschedule_meeting(request):
    """Mentor reschedules a meeting"""
    data = request.data
    meeting_id = data.get('meeting_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    if not all([meeting_id, start_time, end_time]):
        return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        mentor = Mentor.objects.get(email=request.user.email)
        meeting = get_object_or_404(Meeting, id=meeting_id, mentor=mentor)
        
        # Check for mentor conflicts
        mentor_conflicts = Meeting.objects.filter(
            mentor=mentor,
            start_time__lt=end_time,
            end_time__gt=start_time,
            status='scheduled'
        ).exclude(id=meeting_id)
        
        # Check for startup conflicts
        startup_conflicts = Meeting.objects.filter(
            startup=meeting.startup,
            start_time__lt=end_time,
            end_time__gt=start_time,
            status='scheduled'
        ).exclude(id=meeting_id)
        
        if mentor_conflicts.exists() or startup_conflicts.exists():
            return Response({'error': 'Time slot already booked'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.utils.dateparse import parse_datetime
        parsed_start = parse_datetime(start_time)
        parsed_end = parse_datetime(end_time)
        
        # Store old times for slot management
        old_start = meeting.start_time
        old_end = meeting.end_time
        
        # Unblock old slot
        try:
            old_slot = AvailabilitySlot.objects.get(
                startup=meeting.startup,
                start_time=old_start,
                end_time=old_end,
                is_booked=True
            )
            old_slot.is_booked = False
            old_slot.save()
        except AvailabilitySlot.DoesNotExist:
            pass
        
        # Block new slot
        try:
            new_slot = AvailabilitySlot.objects.get(
                startup=meeting.startup,
                start_time=parsed_start,
                end_time=parsed_end,
                is_booked=False
            )
            new_slot.is_booked = True
            new_slot.save()
        except AvailabilitySlot.DoesNotExist:
            # Create new slot if it doesn't exist
            AvailabilitySlot.objects.create(
                startup=meeting.startup,
                start_time=parsed_start,
                end_time=parsed_end,
                is_booked=True
            )
        
        meeting.start_time = parsed_start
        meeting.end_time = parsed_end
        meeting.status = 'scheduled'
        meeting.save()
        
        # Update in Google Calendar if event_id exists
        if meeting.google_event_id:
            try:
                from ..google_calendar import GoogleCalendarService
                from ..models import GoogleCalendarToken
                
                # Try to get mentor's Google Calendar token
                token = GoogleCalendarToken.objects.get(user__email=mentor.email)
                calendar_service = GoogleCalendarService()
                calendar_service.update_meeting(
                    access_token=token.access_token,
                    refresh_token=token.refresh_token,
                    event_id=meeting.google_event_id,
                    start_time=parsed_start,
                    end_time=parsed_end,
                    summary=f"Meeting: {mentor.full_name} & {meeting.startup.registration.first_name} {meeting.startup.registration.last_name}"
                )
            except Exception as e:
                print(f"DEBUG: Failed to update Google Calendar event: {e}")
        
        # Delete reschedule request if exists
        if hasattr(meeting, 'reschedule_request'):
            meeting.reschedule_request.delete()
        
        # Send email to startup about reschedule
        send_meeting_update_email(meeting, 'rescheduled')
        
        return Response({'message': 'Meeting rescheduled successfully'})
        
    except Mentor.DoesNotExist:
        return Response({'error': 'Mentor profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def cancel_meeting(request, meeting_id):
    """Cancel a meeting (mentor only)"""
    try:
        mentor = Mentor.objects.get(email=request.user.email)
        meeting = get_object_or_404(Meeting, id=meeting_id, mentor=mentor)
        
        if meeting.status == 'cancelled':
            return Response({'error': 'Meeting is already cancelled'}, status=status.HTTP_400_BAD_REQUEST)
        
        meeting.status = 'cancelled'
        meeting.save()
        
        # Cancel in Google Calendar if event_id exists
        if meeting.google_event_id:
            try:
                from ..google_calendar import GoogleCalendarService
                from ..models import GoogleCalendarToken
                
                # Try to get mentor's Google Calendar token
                token = GoogleCalendarToken.objects.get(user__email=mentor.email)
                calendar_service = GoogleCalendarService()
                calendar_service.cancel_meeting(
                    access_token=token.access_token,
                    refresh_token=token.refresh_token,
                    event_id=meeting.google_event_id
                )
            except Exception as e:
                print(f"DEBUG: Failed to cancel Google Calendar event: {e}")
        
        # Unblock the availability slot
        try:
            slot = AvailabilitySlot.objects.get(
                startup=meeting.startup,
                start_time=meeting.start_time,
                end_time=meeting.end_time,
                is_booked=True
            )
            slot.is_booked = False
            slot.save()
        except AvailabilitySlot.DoesNotExist:
            pass  # Slot doesn't exist, nothing to unblock
        
        # Delete reschedule request if exists
        if hasattr(meeting, 'reschedule_request'):
            meeting.reschedule_request.delete()
        
        # Send email to startup about cancellation
        send_meeting_update_email(meeting, 'cancelled')
        
        return Response({'message': 'Meeting cancelled successfully'})
        
    except Mentor.DoesNotExist:
        return Response({'error': 'Mentor profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def list_all_meetings(request):
    """List all meetings with comprehensive tracking info"""
    user = request.user
    
    try:
        if user.user_type == 'mentor':
            mentor = Mentor.objects.get(email=user.email)
            meetings = Meeting.objects.filter(mentor=mentor)
        elif user.user_type == 'startup':
            startup = Startup.objects.get(user=user)
            meetings = Meeting.objects.filter(startup=startup)
        else:
            return Response({'meetings': []})
    except (Mentor.DoesNotExist, Startup.DoesNotExist):
        return Response({'meetings': []})
    
    # Include all meetings including cancelled ones for comprehensive tracking
    meetings = meetings.order_by('-start_time')
    
    meeting_data = []
    for meeting in meetings:
        serializer = MeetingSerializer(meeting, context={'request': request})
        meeting_info = serializer.data
        
        # Add additional tracking info
        meeting_info['is_past'] = meeting.start_time < timezone.now()
        meeting_info['can_join'] = (
            meeting.status == 'scheduled' and 
            meeting.start_time <= timezone.now() and 
            meeting.end_time >= timezone.now()
        )
        
        meeting_data.append(meeting_info)
    
    return Response({
        'meetings': meeting_data,
        'total_meetings': len(meeting_data),
        'upcoming_meetings': len([m for m in meeting_data if not m['is_past'] and m['status'] == 'scheduled']),
        'completed_meetings': len([m for m in meeting_data if m['is_past'] and m['status'] == 'scheduled'])
    })

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def debug_user_info(request):
    """Debug endpoint to check user info"""
    user = request.user
    
    info = {
        'user_id': user.id,
        'email': user.email,
        'user_type': getattr(user, 'user_type', 'Not set'),
        'is_authenticated': user.is_authenticated,
    }
    
    # Check if mentor exists
    try:
        mentor = Mentor.objects.get(email=user.email)
        info['mentor_exists'] = True
        info['mentor_id'] = mentor.id
        info['mentor_name'] = mentor.full_name
    except Mentor.DoesNotExist:
        info['mentor_exists'] = False
    
    # Check if startup exists
    try:
        startup = Startup.objects.get(user=user)
        info['startup_exists'] = True
        info['startup_id'] = startup.id
    except Startup.DoesNotExist:
        info['startup_exists'] = False
    
    # Check meetings
    if info.get('mentor_exists'):
        mentor_meetings = Meeting.objects.filter(mentor__email=user.email).count()
        info['mentor_meetings_count'] = mentor_meetings
    
    if info.get('startup_exists'):
        startup_meetings = Meeting.objects.filter(startup__user=user).count()
        info['startup_meetings_count'] = startup_meetings
    
    return Response(info)