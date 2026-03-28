from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import ValidationError
from .models import EMNUser
from django.db.models.query import QuerySet

class JWTCookieAuthentication(BaseAuthentication):
    model = None
    nonce = None

    def get_queryset(self) -> QuerySet:
        return self.model.objects.all()

    def authenticate(self, request):
        # Attempt to get token from the cookie
        token = request.COOKIES.get(f"emn_{self.model.__name__.lower()}_auth")
        if token:
            try:
                validated_token = JWTAuthentication().get_validated_token(token)
                user = self.get_queryset().get(id=validated_token["user_id"])
                return user, "Cookie"
            except Exception as e:
                print(f"Cookie auth failed: {e}")
                pass

        # Check authentication header
        token = request.headers.get("Authorization", None)
        if token is None:
            return None

        # Extract the token from the header
        try:
            token = token.split(" ")[1]
        except IndexError:
            return None
            
        if token:
            try:
                validated_token = JWTAuthentication().get_validated_token(token)

                # Check if model field exists in token, if not, skip the check
                if "model" in validated_token and validated_token["model"] != self.model.__name__:
                    raise ValidationError("Model type mismatch")

                user = self.get_queryset().get(id=validated_token["user_id"])
                return user, "Header"
            except self.model.DoesNotExist:
                print(f"Header auth failed for {self.model.__name__}: User ID {validated_token.get('user_id', 'unknown')} does not exist")
                return None
            except Exception as e:
                print(f"Header auth failed for {self.model.__name__}: {e}")
                print(f"Token model: {validated_token.get('model', 'None') if 'validated_token' in locals() else 'Token invalid'}")
                pass

        return None

class EMNUserAuthentication(JWTCookieAuthentication):
    nonce = "emn"
    model = EMNUser