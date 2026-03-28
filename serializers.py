from rest_framework import serializers
from .models import *
from eureka25.models import Registration
import random
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import authenticate

class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        value = value.lower() if value else value
        if Mentor.objects.filter(email=value).exists():
            raise serializers.ValidationError("A mentor with this email already exists")
        return value
    
    def create(self, validated_data):
        email = validated_data.get('email')
        otp = ''.join(random.choices('0123456789', k=6))
        
        email_otp, created = EmailOTP.objects.update_or_create(
            email=email,
            defaults={'otp': otp, 'is_verified': False}
        )
        
        return {'email': email, 'otp': otp}

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    
    def validate(self, data):
        email = data.get('email')
        if email:
            email = email.lower()
            data['email'] = email
        otp = data.get('otp')
        
        try:
            email_otp = EmailOTP.objects.get(email=email)
        except EmailOTP.DoesNotExist:
            raise serializers.ValidationError("Email not found")
        
        if email_otp.otp != otp:
            raise serializers.ValidationError("Invalid OTP")
        
        expiry_time = email_otp.created_at + timedelta(minutes=30)
        if timezone.now() > expiry_time:
            raise serializers.ValidationError("OTP has expired")
        
        return data
    
    def save(self):
        email = self.validated_data.get('email')
        email_otp = EmailOTP.objects.get(email=email)
        email_otp.is_verified = True
        email_otp.save()
        return email_otp

class MentorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mentor
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
        }

    def validate(self, data):
        # Handle JSON fields that come as strings from FormData
        if 'stakeholder_types' in data and isinstance(data['stakeholder_types'], str):
            import json
            try:
                data['stakeholder_types'] = json.loads(data['stakeholder_types'])
            except json.JSONDecodeError:
                data['stakeholder_types'] = []
        
        if 'networking_cities' in data and isinstance(data['networking_cities'], str):
            import json
            try:
                data['networking_cities'] = json.loads(data['networking_cities'])
            except json.JSONDecodeError:
                data['networking_cities'] = []

        stakeholder_types = data.get('stakeholder_types', [])
        if 'other' in stakeholder_types and not data.get('other_stakeholder_type'):
            raise serializers.ValidationError({
                "other_stakeholder_type": "This field is required when 'Other' is selected."
            })

        networking_cities = data.get('networking_cities', [])
        if 'other' in networking_cities and not data.get('other_networking_city'):
            raise serializers.ValidationError({
                "other_networking_city": "This field is required when 'Other' is selected."
            })

        return data

    def create(self, validated_data):
        validated_data.setdefault('is_active', True)
        password = validated_data.pop('password', None)
        if password:
            mentor = Mentor.objects.create_user(password=password, **validated_data)
        else:
            # Create mentor without password - they can set it later via forgot password
            mentor = Mentor(**validated_data)
            mentor.set_unusable_password()
            mentor.save()
        return mentor
    
    def update(self, instance, validated_data):
        # Handle profile image update
        if 'profile_image' in validated_data:
            # Delete old image if exists
            if instance.profile_image:
                instance.profile_image.delete(save=False)
        
        return super().update(instance, validated_data)

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'

class TestimonialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Testimonial
        fields = '__all__'

class ConnectedMentorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectedMentor
        fields = '__all__'

class PastWinnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PastWinner
        fields = '__all__'

class ContactProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactProfile
        fields = '__all__'

class GetAMentorEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = GetAMentorEmail
        fields = '__all__'

class MentorLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})
    
    def validate(self, data):
        email = data.get('email')
        if email:
            email = email.lower()
            data['email'] = email
        password = data.get('password')
        
        if email and password:
            try:
                from django.contrib.auth.hashers import check_password
                user = Mentor.objects.get(email=email)
                
                if check_password(password, user.password):
                    if not user.is_active:
                        raise serializers.ValidationError("Account is disabled")
                    data['user'] = user
                else:
                    raise serializers.ValidationError("Invalid email or password")
            except Mentor.DoesNotExist:
                raise serializers.ValidationError("Invalid email or password")
        else:
            raise serializers.ValidationError("Must provide email and password")
        
        return data

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        value = value.lower() if value else value
        if not Mentor.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account found with this email")
        return value

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)
    
    def validate(self, data):
        email = data.get('email')
        if email:
            email = email.lower()
            data['email'] = email
        token = data.get('token')
        
        try:
            reset_token = PasswordResetToken.objects.get(
                email=email, 
                token=token, 
                is_used=False
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired token")
        
        if timezone.now() > reset_token.created_at + timedelta(minutes=30):
            raise serializers.ValidationError("Token has expired")
        
        data['reset_token'] = reset_token
        return data

class CheckEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        value = value.lower() if value else value
        if not Mentor.objects.filter(email=value).exists():
            raise serializers.ValidationError("No account found with this email")
        return value

class SetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8)
    
    def validate(self, data):
        email = data.get('email')
        if email:
            email = email.lower()
            data['email'] = email
        token = data.get('token')
        
        try:
            reset_token = PasswordResetToken.objects.get(
                email=email, 
                token=token, 
                is_used=False
            )
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired token")
        
        if timezone.now() > reset_token.created_at + timedelta(minutes=30):
            raise serializers.ValidationError("Token has expired")
        
        data['reset_token'] = reset_token
        return data

# Dashboard Serializers
class MentorCardSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Mentor
        fields = ['id', 'user_id', 'full_name', 'organization_name', 'city', 'state', 
                 'preferred_sector_1', 'preferred_sector_2', 'preferred_sector_3',
                 'profile_image', 'stakeholder_types']
    
    def get_user_id(self, obj):
        try:
            emn_user = EMNUser.objects.get(email=obj.email)
            return emn_user.id
        except EMNUser.DoesNotExist:
            return None

class StartupCardSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='registration.first_name')
    last_name = serializers.CharField(source='registration.last_name')
    city = serializers.CharField(source='registration.city')
    state = serializers.CharField(source='registration.state')
    startup_name = serializers.CharField(source='idea.startup_name', allow_null=True)
    sector_1 = serializers.CharField(source='idea.sector_1', allow_null=True)
    sector_2 = serializers.CharField(source='idea.sector_2', allow_null=True)
    sector_3 = serializers.CharField(source='idea.sector_3', allow_null=True)
    user_id = serializers.IntegerField(source='user.id')
    idea = serializers.SerializerMethodField()
    
    class Meta:
        model = Startup
        fields = ['id', 'user_id', 'first_name', 'last_name', 'city', 'state',
                 'startup_name', 'sector_1', 'sector_2', 'sector_3', 'idea']
    
    def get_idea(self, obj):
        if obj.idea:
            return {
                'idea_description': obj.idea.idea_description
            }
        return None

class ConnectionRequestSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    receiver_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ConnectionRequest
        fields = ['id', 'sender', 'receiver', 'sender_name', 'receiver_name',
                 'message', 'status', 'created_at']
    
    def get_sender_name(self, obj):
        if obj.sender.user_type == 'mentor':
            mentor = Mentor.objects.get(email=obj.sender.email)
            return mentor.full_name
        startup = Startup.objects.get(user=obj.sender)
        return f"{startup.registration.first_name} {startup.registration.last_name}"
    
    def get_receiver_name(self, obj):
        if obj.receiver.user_type == 'mentor':
            mentor = Mentor.objects.get(email=obj.receiver.email)
            return mentor.full_name
        startup = Startup.objects.get(user=obj.receiver)
        return f"{startup.registration.first_name} {startup.registration.last_name}"

class ConnectionSerializer(serializers.ModelSerializer):
    connected_user = serializers.SerializerMethodField()
    
    class Meta:
        model = Connection
        fields = ['id', 'connected_user', 'created_at']
    
    def get_connected_user(self, obj):
        request_user = self.context['request'].user
        other_user = obj.user2 if obj.user1 == request_user else obj.user1
        
        print(f"DEBUG ConnectionSerializer: request_user={request_user.id} ({request_user.user_type}), other_user={other_user.id} ({other_user.user_type})")
        
        # Skip self-connections
        if other_user.id == request_user.id:
            print(f"DEBUG: Skipping self-connection")
            return None
        
        try:
            if other_user.user_type == 'mentor':
                mentor = Mentor.objects.get(email=other_user.email)
                data = MentorCardSerializer(mentor).data
                data['user_id'] = other_user.id
                print(f"DEBUG: Returning mentor data for user {other_user.id}")
                return data
            else:
                startup = Startup.objects.get(user=other_user)
                data = StartupCardSerializer(startup).data
                data['user_id'] = other_user.id
                print(f"DEBUG: Returning startup data for user {other_user.id}")
                return data
        except (Mentor.DoesNotExist, Startup.DoesNotExist) as e:
            print(f"DEBUG: Error getting connected user data: {e}")
            return None

class StartupProfileSerializer(serializers.ModelSerializer):
    startup_name = serializers.SerializerMethodField()
    industry = serializers.SerializerMethodField()
    stage = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    
    class Meta:
        model = Registration
        fields = ['email', 'first_name', 'last_name', 'contact_number', 
                 'state', 'city', 'linkedin_url', 'startup_name', 'industry', 
                 'stage', 'description']
        read_only_fields = ['email']
    
    def get_startup_name(self, obj):
        try:
            startup = Startup.objects.get(registration=obj)
            return startup.idea.startup_name if startup.idea else ''
        except (Startup.DoesNotExist, AttributeError):
            return ''
    
    def get_industry(self, obj):
        try:
            startup = Startup.objects.get(registration=obj)
            return startup.idea.sector_1 if startup.idea else ''
        except (Startup.DoesNotExist, AttributeError):
            return ''
    
    def get_stage(self, obj):
        # Default stage based on Eureka participation
        return 'idea'
    
    def get_description(self, obj):
        try:
            startup = Startup.objects.get(registration=obj)
            return startup.idea.idea_description if startup.idea else ''
        except (Startup.DoesNotExist, AttributeError):
            return ''
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Map fields to match frontend expectations
        data['full_name'] = f"{instance.first_name} {instance.last_name}"
        data['phone_number'] = instance.contact_number
        data['linkedin_url'] = instance.linkedin_url or ''
        data['company_name'] = data.pop('startup_name', '')
        return data


class RescheduleRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RescheduleRequest
        fields = ['requested_date', 'reason', 'created_at']


class MeetingSerializer(serializers.ModelSerializer):
    other_user = serializers.SerializerMethodField()
    startup_info = serializers.SerializerMethodField()
    mentor_info = serializers.SerializerMethodField()
    reschedule_request = RescheduleRequestSerializer(read_only=True)
    
    class Meta:
        model = Meeting
        fields = ['id', 'start_time', 'end_time', 'status', 'google_meet_link', 'other_user', 'startup_info', 'mentor_info', 'reschedule_request', 'created_at']
    
    def get_other_user(self, obj):
        request_user = self.context['request'].user
        
        try:
            # Check if user is mentor - handle both authentication systems
            is_mentor = False
            
            # Check if user is directly a Mentor instance
            if isinstance(request_user, Mentor):
                is_mentor = True
            # Check if EMNUser with mentor type
            elif hasattr(request_user, 'user_type') and request_user.user_type == 'mentor':
                is_mentor = True
            # Check if Mentor exists with this email
            elif Mentor.objects.filter(email=request_user.email).exists():
                is_mentor = True
            
            if is_mentor:
                # User is the mentor, return startup info
                startup_name = ''
                if obj.startup.idea and obj.startup.idea.startup_name:
                    startup_name = obj.startup.idea.startup_name
                
                profile_image = None
                if obj.startup.registration.profile_photo:
                    profile_image = obj.startup.registration.profile_photo.url
                
                return {
                    'id': obj.startup.id,
                    'first_name': obj.startup.registration.first_name,
                    'last_name': obj.startup.registration.last_name,
                    'email': obj.startup.user.email,
                    'startup_name': startup_name,
                    'profile_image': profile_image,
                    'user_type': 'startup'
                }
            else:
                # User is the startup, return mentor info
                profile_image = None
                if obj.mentor.profile_image:
                    profile_image = obj.mentor.profile_image.url
                
                return {
                    'id': obj.mentor.id,
                    'full_name': obj.mentor.full_name,
                    'email': obj.mentor.email,
                    'organization_name': obj.mentor.organization_name or '',
                    'profile_image': profile_image,
                    'user_type': 'mentor'
                }
        except Exception as e:
            print(f"Error in get_other_user: {e}")
            return None
    
    def get_startup_info(self, obj):
        try:
            startup_name = ''
            if obj.startup.idea and obj.startup.idea.startup_name:
                startup_name = obj.startup.idea.startup_name
            
            return {
                'id': obj.startup.id,
                'first_name': obj.startup.registration.first_name,
                'last_name': obj.startup.registration.last_name,
                'startup_name': startup_name
            }
        except:
            return None
    
    def get_mentor_info(self, obj):
        try:
            return {
                'id': obj.mentor.id,
                'full_name': obj.mentor.full_name,
                'organization_name': obj.mentor.organization_name or ''
            }
        except:
            return None


class MeetingTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingTracker
        fields = ['action', 'timestamp']

class EMNUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = EMNUser
        fields = ['id', 'email', 'user_type', 'is_email_verified', 'is_active', 
                 'dashboard_access', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']