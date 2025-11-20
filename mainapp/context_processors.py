# mainapp/context_processors.py
from django.conf import settings
from .models import Member

# Must match the salt/name used when you set the signed cookie
MEMBER_COOKIE_NAME = "member_auth"
MEMBER_COOKIE_SALT = "mainapp-member-auth-salt"

def current_member(request):
    """
    Template context processor that provides `site_member` (Member instance or None)
    so templates can render site-member state without relying on request.user.
    """
    site_member = None
    try:
        signed_val = request.get_signed_cookie(MEMBER_COOKIE_NAME, default=None, salt=MEMBER_COOKIE_SALT)
        if signed_val:
            try:
                member_id = int(signed_val)
                site_member = Member.objects.filter(id=member_id).first()
            except (ValueError, TypeError):
                site_member = None
    except Exception:
        # No cookie or invalid signature -> None
        site_member = None

    return {"site_member": getattr(request, "member", None)}
