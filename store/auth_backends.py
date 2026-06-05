from django.contrib.auth.backends import BaseBackend
from .models import User

class MobileBackend(BaseBackend):
    def authenticate(self, request, mobile_number=None, **kwargs):
        if not mobile_number:
            return None
        try:
            return User.objects.get(mobile_number=mobile_number)
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
