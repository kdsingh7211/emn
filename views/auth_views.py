from django.shortcuts import render
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from ..models import EmailOTP, Mentor, SiteSettings, PasswordResetToken, EMNUser
from ..custom_auth import EMNUserAuthentication
from ..serializers import (
    EmailVerificationSerializer,
    OTPVerificationSerializer,
    MentorSerializer,
    MentorLoginSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    CheckEmailSerializer,
    SetPasswordSerializer
)
from ..models import EmailOTP, Mentor, SiteSettings, PasswordResetToken, EMNUser, Startup
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from ..mailing import send_otp_email, send_registration_success_email, send_password_reset_email
import random
import string
from django.utils import timezone

class EmailVerificationView(generics.GenericAPIView):
    serializer_class = EmailVerificationSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        settings = SiteSettings.get_settings()
        if not settings.mentor_registration_enabled:
            return Response({
                "error": "Mentor registration is currently disabled"
            }, status=status.HTTP_403_FORBIDDEN)
            
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        otp = ''.join(random.choices('0123456789', k=6))
        
        email_otp, created = EmailOTP.objects.update_or_create(
            email=email,
            defaults={
                'otp': otp, 
                'is_verified': False,
                'created_at': timezone.now()
            }
        )
        
        send_otp_email(email, otp)
        
        return Response({
            "message": "OTP sent to your email",
            "email": email
        }, status=status.HTTP_200_OK)

class OTPVerificationView(generics.GenericAPIView):
    serializer_class = OTPVerificationSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            print(serializer.errors)
            
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data.get('email')
        otp = serializer.validated_data.get('otp')
        
        try:
            email_otp = EmailOTP.objects.get(email=email)
            if email_otp.otp != otp:
                return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
            
            email_otp.is_verified = True
            email_otp.save()
            
            return Response({
                "message": "Email verified successfully",
                "email": email,
                "is_verified": True
            }, status=status.HTTP_200_OK)
            
        except EmailOTP.DoesNotExist:
            return Response({"error": "Email not found"}, status=status.HTTP_400_BAD_REQUEST)

class MentorRegView(generics.CreateAPIView):
    queryset = Mentor.objects.all()
    serializer_class = MentorSerializer 
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        settings = SiteSettings.get_settings()
        if not settings.mentor_registration_enabled:
            return Response({
                "error": "Mentor registration is currently disabled"
            }, status=status.HTTP_403_FORBIDDEN)
            
        email = request.data.get('email')
        try:
            email_otp = EmailOTP.objects.get(email=email)
            if not email_otp.is_verified:
                return Response(
                    {"error": "Email must be verified before registration"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except EmailOTP.DoesNotExist:
            return Response(
                {"error": "Email not found. Please verify your email first"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if Mentor.objects.filter(email=email).exists():
            return Response(
                {"error": "Mentor with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mentor = serializer.save()
        
        # Create EMNUser after mentor registration
        emn_user, created = EMNUser.objects.get_or_create(
            email=email,
            defaults={
                'user_type': 'mentor',
                'is_email_verified': True,
                'is_active': True,
                'dashboard_access': False
            }
        )
        
        # Link mentor to EMNUser
        mentor.user = emn_user
        mentor.save()
        
        return Response({
            "message": "Mentor registered successfully",
            "mentor_id": mentor.id,
            "emn_user_id": emn_user.id
        }, status=status.HTTP_201_CREATED)

class MentorLoginView(generics.GenericAPIView):
    serializer_class = MentorLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        user = serializer.validated_data['user']
        
        # Get or create EMNUser for this mentor
        if user.user:
            emn_user = user.user
        else:
            emn_user, created = EMNUser.objects.get_or_create(
                email=user.email,
                defaults={
                    'user_type': 'mentor',
                    'is_email_verified': True,
                    'is_active': True,
                    'dashboard_access': False
                }
            )
            # Link the mentor to EMNUser
            user.user = emn_user
            user.save()
        
        refresh = RefreshToken()
        refresh["user_id"] = emn_user.id
        refresh["model"] = "EMNUser"
        
        response = Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': emn_user.id,
                'email': emn_user.email,
                'user_type': 'mentor',
                'name': user.full_name
            }
        })
        
        response.set_cookie(
            key='emn_mentor_auth',
            value=str(refresh.access_token),
            httponly=True,
            samesite='Lax',
            secure=False,
            max_age=3600 * 24
        )
        
        return response

class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        token = ''.join(random.choices('0123456789', k=6))
        
        PasswordResetToken.objects.create(email=email, token=token)
        send_password_reset_email(email, token)
        
        return Response({
            "message": "Password reset token sent to your email"
        }, status=status.HTTP_200_OK)

class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        new_password = serializer.validated_data['new_password']
        reset_token = serializer.validated_data['reset_token']
        
        mentor = Mentor.objects.get(email=email)
        mentor.set_password(new_password)
        mentor.save()
        
        reset_token.is_used = True
        reset_token.save()
        
        return Response({
            "message": "Password reset successfully"
        }, status=status.HTTP_200_OK)

class CheckEmailView(generics.GenericAPIView):
    serializer_class = CheckEmailSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        mentor = Mentor.objects.get(email=email)
        
        if not mentor.password_changed:
            token = ''.join(random.choices('0123456789', k=6))
            PasswordResetToken.objects.create(email=email, token=token)
            send_password_reset_email(email, token)
            
            return Response({
                "requires_password_setup": True,
                "message": "OTP sent to set your password"
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "requires_password_setup": False,
                "message": "Enter your password to continue"
            }, status=status.HTTP_200_OK)

class SetPasswordView(generics.GenericAPIView):
    serializer_class = SetPasswordSerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        new_password = serializer.validated_data['new_password']
        reset_token = serializer.validated_data['reset_token']
        
        mentor = Mentor.objects.get(email=email)
        mentor.set_password(new_password)
        mentor.password_changed = True
        mentor.save()
        
        reset_token.is_used = True
        reset_token.save()
        
        return Response({
            "message": "Password set successfully. You can now login.",
            "success": True
        }, status=status.HTTP_200_OK)

class MentorProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = MentorSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [EMNUserAuthentication]
    
    def get_object(self):
        user = self.request.user
        if user.user_type == 'mentor':
            return Mentor.objects.get(user=user)
        else:
            raise PermissionDenied('Access denied')

class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [EMNUserAuthentication]
    
    def get_serializer_class(self):
        user = self.request.user
        if user.user_type == 'mentor':
            return MentorSerializer
        else:
            from ..serializers import StartupProfileSerializer
            return StartupProfileSerializer
    
    def get_object(self):
        user = self.request.user
        if user.user_type == 'mentor':
            return Mentor.objects.get(user=user)
        else:
            return Startup.objects.get(user=user)
    
    def retrieve(self, request, *args, **kwargs):
        user = request.user
        if user.user_type == 'mentor':
            mentor = Mentor.objects.get(user=user)
            serializer = MentorSerializer(mentor)
            data = serializer.data
            data['user_type'] = 'mentor'
            # Add full URL for profile image
            if data.get('profile_image'):
                data['profile_image'] = request.build_absolute_uri(data['profile_image'])
            return Response(data)
        else:
            startup = Startup.objects.get(user=user)
            registration = startup.registration
            
            # Build startup profile data manually
            data = {
                'user_type': 'startup',
                'email': registration.email,
                'full_name': f"{registration.first_name} {registration.last_name}",
                'phone_number': registration.contact_number,
                'state': registration.state or '',
                'city': registration.city or '',
                'linkedin_url': registration.linkedin_url or '',
                'company_name': startup.idea.startup_name if startup.idea else '',
                'industry': startup.idea.sector_1 if startup.idea else '',
                'stage': 'idea',
                'description': startup.idea.idea_description if startup.idea else ''
            }
            return Response(data)
    
    def update(self, request, *args, **kwargs):
        user = request.user
        if user.user_type == 'mentor':
            mentor = Mentor.objects.get(user=user)
            
            # Handle FormData - convert JSON strings back to objects
            data = request.data.copy()
            
            # Convert boolean strings to actual booleans
            boolean_fields = ['mentor_any_sector', 'join_mentorship_portal']
            for field in boolean_fields:
                if field in data:
                    data[field] = data[field].lower() in ['true', '1', 'yes']
            
            serializer = MentorSerializer(mentor, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                response_data = serializer.data
                response_data['user_type'] = 'mentor'
                # Add full URL for profile image
                if response_data.get('profile_image'):
                    response_data['profile_image'] = request.build_absolute_uri(response_data['profile_image'])
                return Response(response_data)
            else:
                return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Handle startup profile update
            return super().update(request, *args, **kwargs)