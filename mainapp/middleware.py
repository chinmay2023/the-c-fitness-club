# mainapp/middleware.py
from django.core import signing
from django.conf import settings
from .models import Member

MEMBER_COOKIE_NAME = "member_auth"
MEMBER_COOKIE_SALT = "mainapp-member-auth-salt"

class MemberAuthMiddleware:
    """
    Reads signed member cookie and sets request.member to Member or None.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.member = None
        try:
            signed_val = request.get_signed_cookie(MEMBER_COOKIE_NAME, default=None, salt=MEMBER_COOKIE_SALT)
            if signed_val:
                try:
                    member_id = int(signed_val)
                    member = Member.objects.filter(id=member_id).first()
                    if member:
                        request.member = member
                except Exception:
                    # invalid cookie or parsing error, leave request.member = None
                    request.member = None
        except Exception:
            # cookie missing or signature invalid -> treat as no member
            request.member = None

        response = self.get_response(request)
        return response
