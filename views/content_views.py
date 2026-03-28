from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.core.cache import cache
from ..models import FAQ, Testimonial, ConnectedMentor, PastWinner, ContactProfile, GetAMentorEmail, SiteSettings
from ..serializers import (
    FAQSerializer, 
    TestimonialSerializer, 
    ConnectedMentorSerializer,
    PastWinnerSerializer, 
    ContactProfileSerializer,
    GetAMentorEmailSerializer
)
from ..mailing import send_mentor_interest_email

class FAQView(generics.ListAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer

class TestimonialView(generics.ListAPIView):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer

class ConnectedMentorView(generics.ListAPIView):
    queryset = ConnectedMentor.objects.all()
    serializer_class = ConnectedMentorSerializer

class PastWinnerView(generics.ListAPIView):
    queryset = PastWinner.objects.all()
    serializer_class = PastWinnerSerializer

class ContactProfileView(generics.ListAPIView):
    queryset = ContactProfile.objects.all()
    serializer_class = ContactProfileSerializer
    permission_classes = [AllowAny]

class GetAMentorEmailView(generics.CreateAPIView):
    serializer_class = GetAMentorEmailSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        email = request.data.get('email')

        if GetAMentorEmail.objects.filter(email=email).exists():
            return Response({
                "detail": "You've already submitted your interest. We'll be in touch soon!"
            }, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        name = serializer.validated_data.get('name', 'There')
        
        # Send email using mailing function
        email_sent = send_mentor_interest_email(name, email)
        
        if not email_sent:
            return Response({
                "detail": "Saved, but failed to send email."
            }, status=status.HTTP_201_CREATED)

        return Response({
            "detail": "Interest submitted. We'll contact you soon."
        }, status=status.HTTP_201_CREATED)

class SiteSettingsView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Try to get settings from cache first
        cached_settings = cache.get('site_settings')
        if cached_settings is not None:
            return Response(cached_settings, status=status.HTTP_200_OK)
        
        # If not in cache, get from database and cache it
        settings = SiteSettings.get_settings()
        settings_data = {
            "mentor_registration_enabled": settings.mentor_registration_enabled
        }
        
        # Cache for 1 hour (3600 seconds)
        cache.set('site_settings', settings_data, 3600)
        
        return Response(settings_data, status=status.HTTP_200_OK)