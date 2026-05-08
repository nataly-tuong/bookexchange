from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .cart_session import merge_session_cart_to_db


@receiver(user_logged_in)
def merge_cart_after_login(sender, request, user, **kwargs):
    merge_session_cart_to_db(request)
