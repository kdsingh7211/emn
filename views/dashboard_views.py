from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.db import models
from ..models import *
from ..serializers import *
from ..mailing import send_connection_request_email
from ..matching_algorithm import EMNMatchingAlgorithm
from ..custom_auth import EMNUserAuthentication
from django.conf import settings
import secrets
import hashlib

from django.conf import settings
FRONTEND_URL = f"{settings.BASE_URL}/emn"

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def mentor_dashboard(request):
    """Mentor dashboard data - shows top 20 startups based on matching algorithm"""
    user = request.user
    
    # Check dashboard access
    if not user.dashboard_access:
        return Response({
            'error': 'Dashboard access denied',
            'message': 'Your dashboard access is currently disabled. Please contact support.'
        }, status=403)
    
    # Use the foreign key relationship
    mentor = get_object_or_404(Mentor, user=user)
    
    # Get top 20 startups ordered by match score (best to worst)
    existing_matches = MentorMatch.objects.filter(mentor=mentor).order_by('-match_score')[:20]
    
    startup_data = []
    if existing_matches.exists():
        for match in existing_matches:
            startup_serialized = StartupCardSerializer(match.startup).data
            startup_serialized['match_score'] = match.match_score
            startup_data.append(startup_serialized)
    else:
        # Generate matches if none exist - limit to top 20
        algorithm = EMNMatchingAlgorithm()
        matches_with_scores = algorithm.generate_matches_for_mentor(mentor.id, limit=20)
        for startup, score, factors in matches_with_scores:
            startup_serialized = StartupCardSerializer(startup).data
            startup_serialized['match_score'] = score
            startup_data.append(startup_serialized)
    
    # Get connection requests
    pending_requests = ConnectionRequest.objects.filter(
        receiver=user, status='pending'
    )
    
    # Get connections
    connections = Connection.objects.filter(
        models.Q(user1=user) | models.Q(user2=user)
    )
    print(f"DEBUG: Found {len(startup_data)} startups for mentor {mentor.full_name} (limited to top 20)")
    print(f"DEBUG: Startup data: {startup_data[:2] if startup_data else 'No startups'}")
    
    return Response({
        'mentor': MentorSerializer(mentor).data,
        'user_sectors': [mentor.preferred_sector_1, mentor.preferred_sector_2, mentor.preferred_sector_3],
        'matched_startups': startup_data,
        'pending_requests': ConnectionRequestSerializer(pending_requests, many=True).data,
        'connections': ConnectionSerializer(connections, many=True, context={'request': request}).data,
    })

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def startup_dashboard(request):
    """Startup dashboard data"""
    user = request.user
    
    # Check dashboard access
    if not user.dashboard_access:
        return Response({
            'error': 'Dashboard access denied',
            'message': 'Your dashboard access is currently disabled. Please contact support.'
        }, status=403)
    
    startup = get_object_or_404(Startup, user=user)
    
    # Get top 4 available mentors (excluding declined connections)
    declined_mentor_emails = ConnectionRequest.objects.filter(
        sender=user, status='declined'
    ).values_list('receiver__email', flat=True)
    
    declined_mentors = Mentor.objects.filter(
        email__in=declined_mentor_emails
    ).values_list('id', flat=True)
    
    existing_matches = MentorMatch.objects.filter(
        startup=startup
    ).exclude(
        mentor__id__in=declined_mentors
    ).order_by('-match_score')[:4]
    
    mentor_data = []
    if existing_matches.exists():
        for match in existing_matches:
            mentor_serialized = MentorCardSerializer(match.mentor).data
            mentor_serialized['match_score'] = match.match_score
            mentor_data.append(mentor_serialized)
    else:
        # Generate matches if none exist
        algorithm = EMNMatchingAlgorithm()
        matches_with_scores = algorithm.generate_matches_for_startup(startup.id, limit=20)
        # Filter out declined mentors
        available_matches = [m for m in matches_with_scores if m[0].id not in declined_mentors]
        for mentor, score, factors in available_matches[:4]:
            mentor_serialized = MentorCardSerializer(mentor).data
            mentor_serialized['match_score'] = score
            mentor_data.append(mentor_serialized)
    
    # Verify we're actually getting mentors
    for mentor_obj in mentor_data[:3]:
        print(f"DEBUG: Mentor {mentor_obj.get('id')}: {mentor_obj.get('full_name')} (match_score: {mentor_obj.get('match_score')})")
    print(f"DEBUG: Found {len(mentor_data)} mentors for startup {startup.registration.first_name}")
    print(f"DEBUG: Mentor data: {mentor_data[:2] if mentor_data else 'No mentors'}")
    
    # Get connection requests
    pending_requests = ConnectionRequest.objects.filter(
        receiver=user, status='pending'
    )
    
    # Get connections
    connections = Connection.objects.filter(
        models.Q(user1=user) | models.Q(user2=user)
    )
    
    startup_sectors = []
    if startup.idea:
        startup_sectors = [startup.idea.sector_1, startup.idea.sector_2, startup.idea.sector_3]
        startup_sectors = [s for s in startup_sectors if s]  # Remove None values
    
    return Response({
        'startup_name': startup.idea.startup_name if startup.idea else f"{startup.registration.first_name}'s Startup",
        'user_sectors': startup_sectors,
        'matched_mentors': mentor_data,
        'pending_requests': ConnectionRequestSerializer(pending_requests, many=True).data,
        'connections': ConnectionSerializer(connections, many=True, context={'request': request}).data,
    })

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def send_connection_request(request):
    """Send connection request"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    receiver_id = request.data.get('receiver_id')
    message = request.data.get('message', '')
    
    print(f"DEBUG: Connection request - sender: {request.user.email} ({request.user.user_type}), receiver_id: {receiver_id}")
    
    # Find receiver EMNUser based on mentor/startup ID
    # Check based on sender type - mentors connect to startups, startups connect to mentors
    if request.user.user_type == 'mentor':
        # Mentor trying to connect - look for startup
        try:
            startup = Startup.objects.get(id=receiver_id)
            receiver = startup.user
            print(f"DEBUG: Found startup receiver: {receiver.email} ({receiver.user_type})")
        except Startup.DoesNotExist:
            print(f"DEBUG: No startup found with ID {receiver_id}")
            return Response({'error': 'Startup not found'}, status=404)
    else:
        # Startup trying to connect - look for mentor
        try:
            mentor = Mentor.objects.select_related('user').get(id=receiver_id)
            receiver = mentor.user if mentor.user else EMNUser.objects.get(email=mentor.email)
            print(f"DEBUG: Found mentor receiver: {receiver.email} ({receiver.user_type})")
        except Mentor.DoesNotExist:
            print(f"DEBUG: No mentor found with ID {receiver_id}")
            return Response({'error': 'Mentor not found'}, status=404)
    
    print(f"DEBUG: Final check - sender type: {request.user.user_type}, receiver type: {receiver.user_type}")
    
    # Prevent mentor-to-mentor connections
    if request.user.user_type == 'mentor' and receiver.user_type == 'mentor':
        print(f"DEBUG: Blocking mentor-to-mentor connection")
        return Response({'error': 'Mentors can only connect with startups'}, status=400)
    
    # Prevent startup-to-startup connections  
    if request.user.user_type == 'startup' and receiver.user_type == 'startup':
        print(f"DEBUG: Blocking startup-to-startup connection")
        return Response({'error': 'Startups can only connect with mentors'}, status=400)
    
    connection_request, created = ConnectionRequest.objects.get_or_create(
        sender=request.user,
        receiver=receiver,
        defaults={'message': message}
    )
    
    if created:
        # Generate secure tokens
        accept_token = secrets.token_urlsafe(32)
        reject_token = secrets.token_urlsafe(32)
        
        # Store tokens in the connection request
        connection_request.accept_token = accept_token
        connection_request.reject_token = reject_token
        connection_request.save()
        
        if request.user.user_type == 'mentor':
            mentor = Mentor.objects.get(user=request.user)
            sender_name = mentor.full_name
        else:
            startup = Startup.objects.get(user=request.user)
            sender_name = f"{startup.registration.first_name} {startup.registration.last_name}"
        
        accept_url = f"{FRONTEND_URL}/connection/accept/{accept_token}/"
        reject_url = f"{FRONTEND_URL}/connection/reject/{reject_token}/"
        
        send_connection_request_email(
            sender_name=sender_name,
            receiver_email=receiver.email,
            accept_url=accept_url,
            reject_url=reject_url,
            message=message
        )
        
        return Response({'message': 'Connection request sent'})
    else:
        return Response({'error': 'Request already exists'}, status=400)

@api_view(['GET'])
def respond_connection_request_by_token(request, token):
    """Accept/decline connection request using secure token"""
    try:
        # Try to find request by accept token
        conn_request = ConnectionRequest.objects.get(accept_token=token, status='pending')
        action = 'accept'
    except ConnectionRequest.DoesNotExist:
        try:
            # Try to find request by reject token
            conn_request = ConnectionRequest.objects.get(reject_token=token, status='pending')
            action = 'decline'
        except ConnectionRequest.DoesNotExist:
            return render(request, 'emn/connection_invalid.html', {'dashboard_url': f'{settings.BASE_URL}/emn/dashboard'})
    
    if action == 'accept':
        conn_request.status = 'accepted'
        conn_request.save()
        
        # Create connection if it doesn't exist (ensure consistent ordering)
        user1, user2 = (conn_request.sender, conn_request.receiver) if conn_request.sender.id < conn_request.receiver.id else (conn_request.receiver, conn_request.sender)
        Connection.objects.get_or_create(user1=user1, user2=user2)
        
        return render(request, 'emn/connection_accepted.html', {'dashboard_url': f'{settings.BASE_URL}/emn/dashboard'})
    
    elif action == 'decline':
        conn_request.status = 'declined'
        conn_request.save()
        
        return render(request, 'emn/connection_rejected.html', {'dashboard_url': f'{settings.BASE_URL}/emn/dashboard'})
    
    return render(request, 'emn/connection_invalid.html', {'dashboard_url': f'{settings.BASE_URL}/emn/dashboard'})

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def respond_connection_request(request, request_id):
    """Accept/decline connection request (authenticated endpoint)"""
    action = request.data.get('action')  # 'accept' or 'decline'
    
    conn_request = get_object_or_404(
        ConnectionRequest, 
        id=request_id, 
        receiver=request.user
    )
    
    if action == 'accept':
        conn_request.status = 'accepted'
        conn_request.save()
        
        # Create connection if it doesn't exist (ensure consistent ordering)
        user1, user2 = (conn_request.sender, conn_request.receiver) if conn_request.sender.id < conn_request.receiver.id else (conn_request.receiver, conn_request.sender)
        Connection.objects.get_or_create(user1=user1, user2=user2)
        
        return Response({'message': 'Connection accepted'})
    
    elif action == 'decline':
        conn_request.status = 'declined'
        conn_request.save()
        
        # If declined by mentor, startup will get next available mentor
        response_data = {'message': 'Connection declined'}
        
        if conn_request.sender.user_type == 'startup':
            # Get next available mentor for the startup
            from .replacement_views import get_next_available_mentor
            # This will be handled by frontend calling the replacement endpoint
            response_data['refresh_matches'] = True
        
        return Response(response_data)
    
    return Response({'error': 'Invalid action'}, status=400)

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def get_connections(request):
    """Get user's connections"""
    connections = Connection.objects.filter(
        models.Q(user1=request.user) | models.Q(user2=request.user)
    ).exclude(
        user1=request.user, user2=request.user  # Exclude self-connections
    ).order_by('-created_at')
    
    print(f"DEBUG: Found {connections.count()} connections for user {request.user.id}")
    for conn in connections:
        print(f"DEBUG: Connection {conn.id}: user1={conn.user1.id} ({conn.user1.email}), user2={conn.user2.id} ({conn.user2.email})")
    
    serialized_data = ConnectionSerializer(connections, many=True, context={'request': request}).data
    # Filter out None values (self-connections)
    filtered_data = [conn for conn in serialized_data if conn['connected_user'] is not None]
    
    return Response({
        'connections': filtered_data,
    })

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def send_email_to_connection(request, user_id):
    """Send email to a connected user"""
    try:
        from ..mailing import send_direct_message_email
        
        # Get the other user
        other_user = get_object_or_404(EMNUser, id=user_id)
        print(f"DEBUG: Sender: {request.user.email} (ID: {request.user.id})")
        print(f"DEBUG: Receiver: {other_user.email} (ID: {other_user.id})")
        
        # Check if users are connected
        connection = Connection.objects.filter(
            models.Q(user1=request.user, user2=other_user) | models.Q(user1=other_user, user2=request.user)
        ).first()
        
        if not connection:
            return Response({'error': 'Not connected to this user'}, status=400)
        
        subject = request.data.get('subject', 'Message from EMN')
        message = request.data.get('message', '')
        send_copy = request.data.get('send_copy', False)
        
        if not message:
            return Response({'error': 'Message is required'}, status=400)
        
        # Send email to the other user
        if send_direct_message_email(request.user, other_user, subject, message, send_copy):
            return Response({'message': 'Email sent successfully'})
        else:
            return Response({'error': 'Failed to send email'}, status=500)
            
    except Exception as e:
        return Response({'error': f'Failed to send email: {str(e)}'}, status=500)