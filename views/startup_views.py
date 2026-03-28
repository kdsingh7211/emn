from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from ..models import EMNUser, Startup
from ..serializers import *

class StartupLoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({'error': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Import here to avoid circular imports
            from eureka25.models import Registration
            
            # Check if registration exists in Eureka25
            registration = Registration.objects.get(email=email)
            
            # Verify password - check both hashed and plain text for compatibility
            password_valid = False
            if registration.password.startswith('pbkdf2_') or registration.password.startswith('bcrypt') or registration.password.startswith('argon2'):
                # Hashed password
                password_valid = check_password(password, registration.password)
            else:
                # Plain text password (for development)
                password_valid = (password == registration.password)
            
            if not password_valid:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get or create EMNUser
            emn_user, created = EMNUser.objects.get_or_create(
                email=email,
                defaults={
                    'user_type': 'startup', 
                    'is_email_verified': True,
                    'dashboard_access': True
                }
            )
            
            # Enable dashboard access if not already enabled
            if not emn_user.dashboard_access:
                emn_user.dashboard_access = True
                emn_user.save()
            
            # Get or create Startup profile
            startup, created = Startup.objects.get_or_create(
                user=emn_user,
                defaults={'registration': registration}
            )
            
            # Generate JWT token
            refresh = RefreshToken()
            refresh["user_id"] = emn_user.id
            refresh["model"] = "EMNUser"
            
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': emn_user.id,
                    'email': emn_user.email,
                    'user_type': 'startup',
                    'name': f"{registration.first_name} {registration.last_name}"
                }
            })
            
        except Registration.DoesNotExist:
            return Response({'error': 'No account found with this email'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Startup login error: {str(e)}")  # Debug logging
            return Response({'error': f'Login failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)