from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ..models import EMNUser, Mentor, Startup, AvailabilitySlot, Booking, WeeklyAvailability
from ..custom_auth import EMNUserAuthentication

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def create_availability_slot(request):
    try:
        startup = Startup.objects.get(user=request.user)
        slot = AvailabilitySlot.objects.create(
            startup=startup,
            start_time=request.data['start_time'],
            end_time=request.data['end_time']
        )
        return Response({
            'id': slot.id,
            'start_time': slot.start_time,
            'end_time': slot.end_time,
            'is_booked': slot.is_booked
        }, status=status.HTTP_201_CREATED)
    except Startup.DoesNotExist:
        return Response({'error': 'Only startups can create availability slots'}, 
                       status=status.HTTP_403_FORBIDDEN)

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def get_availability_slots(request):
    startup_id = request.GET.get('startup_id')
    
    if startup_id:
        slots = AvailabilitySlot.objects.filter(
            startup_id=startup_id, 
            is_booked=False,
            start_time__gte=timezone.now()
        ).select_related('startup__registration')
    else:
        slots = AvailabilitySlot.objects.filter(
            is_booked=False,
            start_time__gte=timezone.now()
        ).select_related('startup__registration')
    
    data = [{
        'id': slot.id,
        'start_time': slot.start_time,
        'end_time': slot.end_time,
        'startup': {
            'id': slot.startup.id,
            'registration': {
                'first_name': slot.startup.registration.first_name,
                'last_name': slot.startup.registration.last_name,
                'organization_name': getattr(slot.startup.registration, 'organization_name', '')
            }
        }
    } for slot in slots]
    
    return Response(data)

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def book_slot(request):
    try:
        mentor = Mentor.objects.get(email=request.user.email)
        
        # Check if Google Calendar is connected
        from emn.models import GoogleCalendarToken
        try:
            GoogleCalendarToken.objects.get(user=request.user)
        except GoogleCalendarToken.DoesNotExist:
            return Response({
                'error': 'Google Calendar connection required',
                'message': 'Connect Google Calendar first to book meetings'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        startup_id = request.data.get('startup_id')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        
        startup = Startup.objects.get(id=startup_id)
        
        # Block the availability slot first
        try:
            slot = AvailabilitySlot.objects.get(
                startup=startup,
                start_time=start_time,
                end_time=end_time,
                is_booked=False
            )
            slot.is_booked = True
            slot.save()
        except AvailabilitySlot.DoesNotExist:
            # Create a new slot if it doesn't exist
            slot = AvailabilitySlot.objects.create(
                startup=startup,
                start_time=start_time,
                end_time=end_time,
                is_booked=True
            )
        
        # Try to create Google Meet link if tokens available
        meet_link = None
        event_id = None
        
        try:
            from emn.google_calendar import GoogleCalendarService
            
            # Create both booking and meeting
            booking = Booking.objects.create(
                mentor=mentor,
                startup=startup,
                start_time=start_time,
                end_time=end_time,
                google_meet_link='',
                google_event_id=''
            )
            
            from emn.models import Meeting
            meeting = Meeting.objects.create(
                mentor=mentor,
                startup=startup,
                start_time=start_time,
                end_time=end_time,
                google_meet_link='',
                status='scheduled'
            )
            
            # Try to get Google Calendar token for mentor
            token = GoogleCalendarToken.objects.get(user=request.user)
            calendar_service = GoogleCalendarService()
            
            meeting_data = calendar_service.create_meeting(
                access_token=token.access_token,
                refresh_token=token.refresh_token,
                start_time=timezone.datetime.fromisoformat(start_time.replace('Z', '+00:00')),
                end_time=timezone.datetime.fromisoformat(end_time.replace('Z', '+00:00')),
                attendees=[mentor.email, startup.user.email],
                summary=f"Meeting: {mentor.full_name} & {startup.registration.first_name} {startup.registration.last_name}",
                booking_id=booking.id
            )
            
            meet_link = meeting_data['actual_meet_link']
            event_id = meeting_data['event_id']
            tracking_link = meeting_data['meet_link']
            
        except Exception as e:
            import uuid
            meet_id = str(uuid.uuid4())[:8] + '-' + str(uuid.uuid4())[:4] + '-' + str(uuid.uuid4())[:4]
            meet_link = f"https://meet.google.com/{meet_id}"
            from django.conf import settings
            tracking_link = f"{settings.BASE_URL}/emn/join-meeting/{meet_id}/"
        
        # Update both booking and meeting with meet link
        if 'booking' in locals():
            booking.google_meet_link = meet_link
            booking.google_event_id = event_id
            booking.save()
            
            meeting.google_meet_link = meet_link
            meeting.save()
            tracking_url = tracking_link if 'tracking_link' in locals() else f"{settings.BASE_URL}/emn/join-meeting/{booking.id}/"
        else:
            booking = Booking.objects.create(
                mentor=mentor,
                startup=startup,
                start_time=start_time,
                end_time=end_time,
                google_meet_link=meet_link,
                google_event_id=event_id
            )
            
            from emn.models import Meeting
            Meeting.objects.create(
                mentor=mentor,
                startup=startup,
                start_time=start_time,
                end_time=end_time,
                google_meet_link=meet_link,
                status='scheduled'
            )
            tracking_url = f"{settings.BASE_URL}/emn/join-meeting/{booking.id}/"
        
        # Send email notifications with trackable links
        from emn.mailing import send_personalized_meeting_invitation_email
        from django.utils.dateparse import parse_datetime
        
        # Create separate tracking links for mentor and startup
        meet_id = booking.google_meet_link.split('/')[-1] if booking.google_meet_link else booking.id
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
            'booking_id': booking.id,
            'meet_link': tracking_url
        })
        
    except Mentor.DoesNotExist:
        return Response({'error': 'Only mentors can book meetings'}, 
                       status=status.HTTP_403_FORBIDDEN)
    except Startup.DoesNotExist:
        return Response({'error': 'Startup not found'}, 
                       status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def my_bookings(request):
    if request.user.user_type == 'mentor':
        mentor = Mentor.objects.get(email=request.user.email)
        bookings = Booking.objects.filter(mentor=mentor).select_related('startup__registration', 'slot')
    else:
        startup = Startup.objects.get(user=request.user)
        bookings = Booking.objects.filter(startup=startup).select_related('mentor', 'slot')
    
    data = [{
        'id': booking.id,
        'start_time': booking.slot.start_time,
        'end_time': booking.slot.end_time,
        'google_meet_link': booking.google_meet_link,
        'status': booking.status,
        'mentor_name': booking.mentor.full_name,
        'startup_name': f"{booking.startup.registration.first_name} {booking.startup.registration.last_name}"
    } for booking in bookings]
    
    return Response(data)

@api_view(['GET', 'POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def weekly_availability(request):
    if request.method == 'GET':
        startup_id = request.GET.get('startup_id')
        
        if startup_id:
            # Mentor viewing startup availability
            try:
                startup = Startup.objects.get(id=startup_id)
                availability = WeeklyAvailability.objects.get(startup=startup)
                return Response({
                    'slot_duration': availability.slot_duration,
                    'days': availability.availability_data
                })
            except (Startup.DoesNotExist, WeeklyAvailability.DoesNotExist):
                return Response({
                    'slot_duration': 30,
                    'days': []
                })
        else:
            # Startup viewing own availability
            try:
                startup = Startup.objects.get(user=request.user)
                availability = WeeklyAvailability.objects.get(startup=startup)
                return Response({
                    'slot_duration': availability.slot_duration,
                    'days': availability.availability_data
                })
            except Startup.DoesNotExist:
                return Response({'error': 'Only startups can manage availability'}, 
                               status=status.HTTP_403_FORBIDDEN)
            except WeeklyAvailability.DoesNotExist:
                return Response({
                    'slot_duration': 30,
                    'days': []
                })
    
    elif request.method == 'POST':
        try:
            startup = Startup.objects.get(user=request.user)
            slot_duration = request.data.get('slot_duration', 30)
            days_data = request.data.get('days', [])
            
            availability, created = WeeklyAvailability.objects.update_or_create(
                startup=startup,
                defaults={
                    'slot_duration': slot_duration,
                    'availability_data': days_data
                }
            )
            
            return Response({'message': 'Weekly availability saved successfully'})
            
        except Startup.DoesNotExist:
            return Response({'error': 'Only startups can manage availability'}, 
                           status=status.HTTP_403_FORBIDDEN)

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def get_startups(request):
    startups = Startup.objects.all().select_related('registration')
    data = [{
        'id': startup.id,
        'registration': {
            'first_name': startup.registration.first_name,
            'last_name': startup.registration.last_name,
            'organization_name': getattr(startup.registration, 'organization_name', '')
        }
    } for startup in startups]
    
    return Response(data)

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def google_calendar_auth(request):
    from emn.google_calendar import GoogleCalendarService
    
    calendar_service = GoogleCalendarService()
    auth_url = calendar_service.get_auth_url(request.user.id)
    
    return Response({'auth_url': auth_url})

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def google_calendar_status(request):
    from emn.models import GoogleCalendarToken
    
    try:
        token = GoogleCalendarToken.objects.get(user=request.user)
        return Response({'connected': True, 'email': request.user.email})
    except GoogleCalendarToken.DoesNotExist:
        return Response({'connected': False})

@api_view(['DELETE'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def google_calendar_disconnect(request):
    from emn.models import GoogleCalendarToken
    
    try:
        token = GoogleCalendarToken.objects.get(user=request.user)
        token.delete()
        return Response({'message': 'Google Calendar disconnected successfully'})
    except GoogleCalendarToken.DoesNotExist:
        return Response({'message': 'No Google Calendar connection found'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def track_meet_click(request, booking_id):
    from emn.models import Booking, MeetingTracker
    
    try:
        booking = Booking.objects.get(id=booking_id)
        
        # Get client IP and user agent
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            ip_address = ip_address.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Track the click
        MeetingTracker.objects.create(
            booking=booking,
            user=request.user,
            action='clicked_link',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return Response({
            'message': 'Click tracked',
            'meet_link': booking.google_meet_link
        })
        
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)

@api_view(['GET'])
def join_meeting(request, meet_identifier):
    from emn.models import Booking, MeetingTracker
    from django.http import HttpResponseRedirect
    import re
    
    try:
        # Check if meet_identifier is a booking ID (numeric) or meet ID (alphanumeric with dashes)
        if meet_identifier.isdigit():
            # It's a booking ID
            booking = Booking.objects.get(id=meet_identifier)
            actual_meet_link = booking.google_meet_link
        else:
            # It's a meet ID (like nyu-zsvp-iwp), find booking by meet link
            booking = Booking.objects.filter(google_meet_link__contains=meet_identifier).first()
            if not booking:
                # If no booking found, construct Google Meet URL directly
                actual_meet_link = f"https://meet.google.com/{meet_identifier}"
            else:
                actual_meet_link = booking.google_meet_link
        
        # Get client IP and user agent
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            ip_address = ip_address.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Get user type from URL parameter
        user_type = request.GET.get('user', 'unknown')
        
        # Track the click with simplified model
        if booking:
            MeetingTracker.objects.create(
                booking=booking,
                action=f'clicked_link_{user_type}'
            )
        
        # Redirect to actual Google Meet link
        return HttpResponseRedirect(actual_meet_link)
        
    except Booking.DoesNotExist:
        # If booking not found but we have a meet ID, still redirect to Google Meet
        if not meet_identifier.isdigit():
            actual_meet_link = f"https://meet.google.com/{meet_identifier}"
            return HttpResponseRedirect(actual_meet_link)
        return HttpResponseRedirect('https://ecell.in/emn/dashboard')

@api_view(['GET'])
@csrf_exempt
def google_callback(request):
    from emn.google_calendar import GoogleCalendarService
    from emn.models import GoogleCalendarToken, EMNUser
    from django.http import HttpResponse
    import traceback
    
    code = request.GET.get('code')
    state = request.GET.get('state')  # user_id
    
    print(f"Google callback - Code: {code}, State: {state}")
    
    if not code or not state:
        return HttpResponse('''
        <html>
        <head>
            <title>Connection Error</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="min-h-screen bg-black flex items-center justify-center">
            <div class="max-w-md w-full mx-4">
                <div class="bg-white border border-gray-200 rounded-2xl shadow-2xl overflow-hidden">
                    <div class="bg-black p-8 text-white">
                        <div class="text-center">
                            <div class="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg class="w-8 h-8 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                            </div>
                            <h2 class="text-2xl font-bold">Connection Error</h2>
                            <p class="text-gray-300 mt-2">Missing required parameters</p>
                        </div>
                    </div>
                    <div class="p-8 text-center">
                        <p class="text-gray-600">This window will close automatically</p>
                    </div>
                </div>
            </div>
            <script>setTimeout(() => window.close(), 2000);</script>
        </body>
        </html>
        ''')
    
    try:
        user = EMNUser.objects.get(id=state)
        print(f"Found user: {user.email}")
        
        calendar_service = GoogleCalendarService()
        tokens = calendar_service.exchange_code_for_tokens(code, state)
        print(f"Got tokens: {tokens.keys()}")
        
        # Handle missing refresh token
        refresh_token = tokens.get('refresh_token')
        if not refresh_token:
            # Try to get existing refresh token
            try:
                existing_token = GoogleCalendarToken.objects.get(user=user)
                refresh_token = existing_token.refresh_token
            except GoogleCalendarToken.DoesNotExist:
                refresh_token = 'placeholder_refresh_token'
        
        GoogleCalendarToken.objects.update_or_create(
            user=user,
            defaults={
                'access_token': tokens['access_token'],
                'refresh_token': refresh_token,
                'token_expiry': tokens.get('token_expiry')
            }
        )
        
        return HttpResponse('''
        <html>
        <head>
            <title>Google Calendar Connected</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="min-h-screen bg-black flex items-center justify-center">
            <div class="max-w-md w-full mx-4">
                <div class="bg-white border border-gray-200 rounded-2xl shadow-2xl overflow-hidden">
                    <div class="bg-black p-8 text-white">
                        <div class="text-center">
                            <div class="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg class="w-8 h-8 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                </svg>
                            </div>
                            <h2 class="text-2xl font-bold">Calendar Connected!</h2>
                            <p class="text-gray-300 mt-2">Google Calendar integration successful</p>
                        </div>
                    </div>
                    <div class="p-8">
                        <div class="bg-gray-100 rounded-lg border border-gray-200 p-4 mb-6">
                            <div class="flex items-center">
                                <div class="w-10 h-10 bg-black rounded-full flex items-center justify-center mr-3">
                                    <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                    </svg>
                                </div>
                                <div>
                                    <p class="text-gray-800 text-sm font-medium">Connection Successful!</p>
                                    <p class="text-gray-700 font-semibold">You can now close this window</p>
                                </div>
                            </div>
                        </div>
                        <div class="text-center text-gray-600 text-sm">
                            <p>This window will close automatically in 3 seconds</p>
                        </div>
                    </div>
                </div>
            </div>
            <script>setTimeout(() => window.close(), 3000);</script>
        </body>
        </html>
        ''')
        
    except EMNUser.DoesNotExist:
        print(f"User not found with ID: {state}")
        return HttpResponse('''
        <html>
        <head>
            <title>Invalid User</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="min-h-screen bg-black flex items-center justify-center">
            <div class="max-w-md w-full mx-4">
                <div class="bg-white border border-gray-200 rounded-2xl shadow-2xl overflow-hidden">
                    <div class="bg-black p-8 text-white">
                        <div class="text-center">
                            <div class="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-4">
                                <svg class="w-8 h-8 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                            </div>
                            <h2 class="text-2xl font-bold">Invalid User</h2>
                            <p class="text-gray-300 mt-2">User authentication failed</p>
                        </div>
                    </div>
                    <div class="p-8 text-center">
                        <p class="text-gray-600">This window will close automatically</p>
                    </div>
                </div>
            </div>
            <script>setTimeout(() => window.close(), 2000);</script>
        </body>
        </html>
        ''')
    except Exception as e:
        print(f"Error in Google callback: {str(e)}")
        print(traceback.format_exc())
        return HttpResponse(f'''
        <html><body>
        <h2>❌ Error</h2>
        <p>{str(e)}</p>
        <script>setTimeout(() => window.close(), 3000);</script>
        </body></html>
        ''')