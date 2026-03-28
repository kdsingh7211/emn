from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from ..models import Startup, MentorMatch, ConnectionRequest
from ..serializers import MentorCardSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_next_available_mentor(request):
    """Get next available mentor when current ones are declined"""
    user = request.user
    
    if user.user_type != 'startup':
        return Response({'error': 'Only startups can access this endpoint'}, status=400)
    
    startup = get_object_or_404(Startup, user=user)
    
    # Get declined mentors
    declined_mentor_emails = ConnectionRequest.objects.filter(
        sender=user, status='declined'
    ).values_list('receiver__email', flat=True)
    
    declined_mentors = Mentor.objects.filter(
        email__in=declined_mentor_emails
    ).values_list('id', flat=True)
    
    # Get currently shown mentors (top 4 available)
    current_mentors = MentorMatch.objects.filter(
        startup=startup
    ).exclude(
        mentor__id__in=declined_mentors
    ).order_by('-match_score')[:4].values_list('mentor__id', flat=True)
    
    # Get next best mentor not in current list or declined
    excluded_mentors = list(declined_mentors) + list(current_mentors)
    
    next_mentor_match = MentorMatch.objects.filter(
        startup=startup
    ).exclude(
        mentor__id__in=excluded_mentors
    ).order_by('-match_score').first()
    
    if next_mentor_match:
        mentor_data = MentorCardSerializer(next_mentor_match.mentor).data
        return Response({
            'mentor': mentor_data,
            'match_score': next_mentor_match.match_score,
            'available': True
        })
    
    return Response({
        'mentor': None,
        'available': False,
        'message': 'No more mentors available'
    })