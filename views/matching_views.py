from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import models
from ..models import Mentor, Startup, MentorMatch, EMNUser, ConnectionRequest
from ..matching_algorithm import EMNMatchingAlgorithm
from ..serializers import MentorCardSerializer, StartupCardSerializer
from ..custom_auth import EMNUserAuthentication

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def get_matches_with_scores(request):
    """Get matches with detailed scores for current user"""
    user = request.user
    
    # Check if user has dashboard access
    if not user.dashboard_access:
        return Response({'error': 'Dashboard access required'}, status=403)
    
    if user.user_type == 'mentor':
        mentor = get_object_or_404(Mentor, email=user.email)
        matches = MentorMatch.objects.filter(
            mentor=mentor,
            startup__user__dashboard_access=True
        ).select_related('startup__registration', 'startup__idea').order_by('-match_score')[:20]
        
        match_data = []
        for match in matches:
            startup_data = StartupCardSerializer(match.startup).data
            match_data.append({
                'startup': startup_data,
                'match_score': match.match_score,
                'score_factors': match.score_factors,
                'matching_sectors': match.matching_sectors,
                'created_at': match.created_at
            })
        
        return Response({
            'user_type': 'mentor',
            'matches': match_data
        })
    
    elif user.user_type == 'startup':
        startup = get_object_or_404(Startup, user=user)
        # Get top 4 available mentors (excluding declined)
        declined_mentor_emails = ConnectionRequest.objects.filter(
            sender=user, status='declined'
        ).values_list('receiver__email', flat=True)
        
        declined_mentors = Mentor.objects.filter(
            email__in=declined_mentor_emails
        ).values_list('id', flat=True)
        
        # Only show mentors with dashboard access
        mentor_emails_with_access = EMNUser.objects.filter(
            user_type='mentor', dashboard_access=True
        ).values_list('email', flat=True)
        
        matches = MentorMatch.objects.filter(
            startup=startup,
            mentor__email__in=mentor_emails_with_access
        ).exclude(
            mentor__id__in=declined_mentors
        ).select_related('mentor').order_by('-match_score')[:4]
        
        match_data = []
        for match in matches:
            mentor_data = MentorCardSerializer(match.mentor).data
            match_data.append({
                'mentor': mentor_data,
                'match_score': match.match_score,
                'score_factors': match.score_factors,
                'matching_sectors': match.matching_sectors,
                'created_at': match.created_at
            })
        
        return Response({
            'user_type': 'startup',
            'matches': match_data
        })
    
    return Response({'error': 'Invalid user type'}, status=400)

@api_view(['POST'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def regenerate_matches(request):
    """Regenerate matches for current user"""
    user = request.user
    
    # Check if user has dashboard access
    if not user.dashboard_access:
        return Response({'error': 'Dashboard access required'}, status=403)
    
    if user.user_type == 'mentor':
        mentor = get_object_or_404(Mentor, email=user.email)
        
        # Delete existing matches for this mentor
        MentorMatch.objects.filter(mentor=mentor).delete()
        
        # Generate new matches - limit to top 20
        algorithm = EMNMatchingAlgorithm()
        matches_with_scores = algorithm.generate_matches_for_mentor(mentor.id, limit=20)
        
        return Response({
            'message': f'Generated {len(matches_with_scores)} new matches',
            'high_quality_matches': len([m for m in matches_with_scores if m[1] >= 70])
        })
    
    elif user.user_type == 'startup':
        startup = get_object_or_404(Startup, user=user)
        
        # Delete existing matches for this startup
        MentorMatch.objects.filter(startup=startup).delete()
        
        # Generate new matches
        matches_with_scores = EMNMatchingAlgorithm.generate_matches_for_startup(startup, limit=20)
        
        return Response({
            'message': f'Generated {len(matches_with_scores)} new matches',
            'high_quality_matches': len([m for m in matches_with_scores if m[1] >= 70])
        })
    
    return Response({'error': 'Invalid user type'}, status=400)

@api_view(['GET'])
@authentication_classes([EMNUserAuthentication])
@permission_classes([IsAuthenticated])
def get_match_explanation(request, match_id):
    """Get detailed explanation of a specific match"""
    match = get_object_or_404(MentorMatch, id=match_id)
    
    # Check if user has dashboard access
    user = request.user
    if not user.dashboard_access:
        return Response({'error': 'Dashboard access required'}, status=403)
    
    # Verify user has access to this match
    if user.user_type == 'mentor':
        mentor = get_object_or_404(Mentor, email=user.email)
        if match.mentor != mentor:
            return Response({'error': 'Access denied'}, status=403)
    elif user.user_type == 'startup':
        startup = get_object_or_404(Startup, user=user)
        if match.startup != startup:
            return Response({'error': 'Access denied'}, status=403)
    else:
        return Response({'error': 'Invalid user type'}, status=400)
    
    # Recalculate match to get fresh explanation
    result = EMNMatchingAlgorithm.calculate_match_score(match.mentor, match.startup)
    
    explanation = {
        'overall_score': result['score'],
        'factors': result['factors'],
        'matching_sectors': match.matching_sectors,
        'mentor': {
            'name': match.mentor.full_name,
            'sectors': [
                match.mentor.preferred_sector_1,
                match.mentor.preferred_sector_2,
                match.mentor.preferred_sector_3
            ],
            'stakeholder_types': match.mentor.stakeholder_types,
            'location': f"{match.mentor.city}, {match.mentor.state}",
            'networking_cities': match.mentor.networking_cities,
            'mentor_any_sector': match.mentor.mentor_any_sector
        },
        'startup': {
            'name': f"{match.startup.registration.first_name} {match.startup.registration.last_name}",
            'sectors': [
                match.startup.idea.sector_1 if match.startup.idea else None,
                match.startup.idea.sector_2 if match.startup.idea else None,
                match.startup.idea.sector_3 if match.startup.idea else None
            ] if match.startup.idea else [],
            'location': f"{match.startup.registration.city}, {match.startup.registration.state}",
            'startup_name': match.startup.idea.startup_name if match.startup.idea else 'No idea submitted'
        }
    }
    
    return Response(explanation)

@api_view(['GET'])
def get_matching_stats(request):
    """Get overall matching statistics"""
    total_matches = MentorMatch.objects.count()
    high_quality_matches = MentorMatch.objects.filter(match_score__gte=70).count()
    medium_quality_matches = MentorMatch.objects.filter(match_score__gte=50, match_score__lt=70).count()
    
    mentor_count = Mentor.objects.count()
    startup_count = Startup.objects.count()
    
    # Average scores by factor
    matches_with_factors = MentorMatch.objects.exclude(score_factors={})
    
    avg_factors = {}
    if matches_with_factors.exists():
        for match in matches_with_factors:
            for factor, score in match.score_factors.items():
                if factor not in avg_factors:
                    avg_factors[factor] = []
                avg_factors[factor].append(score)
        
        # Calculate averages
        for factor in avg_factors:
            avg_factors[factor] = sum(avg_factors[factor]) / len(avg_factors[factor])
    
    return Response({
        'total_matches': total_matches,
        'high_quality_matches': high_quality_matches,
        'medium_quality_matches': medium_quality_matches,
        'low_quality_matches': total_matches - high_quality_matches - medium_quality_matches,
        'mentor_count': mentor_count,
        'startup_count': startup_count,
        'average_match_score': MentorMatch.objects.aggregate(
            avg_score=models.Avg('match_score')
        )['avg_score'] or 0,
        'average_factor_scores': avg_factors
    })