# mainapp/views.py
"""
Corrected views for mainapp.

Auth / flow:
- login_view + member_login_view: try Django auth first, else Member auth via signed cookie.
- registration_view: creates Member but does NOT auto-login; redirects to signup (login) page.
- get_current_member: reads Member from middleware or signed cookie.
- book_class_payment / book_plan_payment: require Member; if not, redirect to signup with ?next=...
"""

from urllib.parse import urlparse

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.http import HttpResponse
from django.contrib.auth import get_user_model

from .models import (
    HeroSection, FitnessClass, GalleryImage, EquipmentCategory,
    Feature, Plan, Testimonial, Member, Category, UpiPayment
)
from .forms import ContactForm, MemberRegistrationForm

import qrcode
from io import BytesIO
import base64


# Cookie settings for member auth
MEMBER_COOKIE_NAME = "member_auth"
MEMBER_COOKIE_SALT = "mainapp-member-auth-salt"
MEMBER_COOKIE_MAX_AGE = 60 * 60 * 24 * 14  # 14 days


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def get_current_member(request):
    """
    Return the currently authenticated Member (if any).
    Priority:
      1) request.member (if middleware populates it)
      2) signed cookie MEMBER_COOKIE_NAME (fallback)
    Returns Member instance or None.
    """
    member = getattr(request, "member", None)
    if member:
        return member

    try:
        signed_val = request.get_signed_cookie(
            MEMBER_COOKIE_NAME,
            default=None,
            salt=MEMBER_COOKIE_SALT,
        )
        if signed_val:
            try:
                member_id = int(signed_val)
                return Member.objects.filter(id=member_id).first()
            except (ValueError, TypeError):
                return None
    except Exception:
        # missing/invalid cookie -> treat as not logged in
        return None

    return None


def _redirect_with_next(default_name, request):
    """
    Helper to redirect to `next` query parameter if present and safe, else to default_name.
    """
    next_url = request.GET.get("next") or request.POST.get("next")
    if next_url:
        parsed = urlparse(next_url)
        if not parsed.scheme and not parsed.netloc:
            return redirect(next_url)
    return redirect(default_name)


def generate_upi_qr(upi_id, amount, name, note=""):
    """
    Generate a base64-encoded PNG QR code for a UPI payment URI.
    """
    upi_uri = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR&tn={note}"
    img = qrcode.make(upi_uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return "data:image/png;base64," + img_b64


# -------------------------------------------------------------------
# Public pages
# -------------------------------------------------------------------

def home_view(request):
    hero = HeroSection.objects.first() or HeroSection()
    return render(request, "index.html", {"hero": hero})


def about_view(request):
    images = GalleryImage.objects.all()
    features = Feature.objects.all()
    testimonials = Testimonial.objects.all()
    return render(
        request,
        "about.html",
        {"images": images, "features": features, "testimonials": testimonials},
    )


def class_list(request):
    classes = FitnessClass.objects.select_related("category_fk").all()
    return render(request, "classes.html", {"classes": classes})


def gallery_view(request):
    images = GalleryImage.objects.all()
    return render(request, "gallery.html", {"images": images})


from django.core.mail import send_mail
from django.conf import settings

def contact_view(request):
    if request.method == "POST":
        user_email = request.POST.get("email")
        message = request.POST.get("message")

        # 1) Send mail to YOU (site owner)
        send_mail(
            subject="New contact message from C-Fitness site",
            message=f"From: {user_email}\n\nMessage:\n{message}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_RECEIVER_EMAIL],  # see below
            fail_silently=False,
        )

        # 2) Send auto-reply to USER
        send_mail(
            subject="Thanks for contacting C-Fitness Club",
            message="We received your message and will reply soon.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )

        return redirect("contact")

    return render(request, "contact.html")


def equipment_view(request):
    categories = EquipmentCategory.objects.prefetch_related("equipment_set").all()
    return render(request, "equipment.html", {"categories": categories})


def features_view(request):
    features = Feature.objects.all()
    return render(request, "features.html", {"features": features})


def plans_view(request):
    plans = Plan.objects.all()
    return render(request, "price.html", {"plans": plans})


def testimonial_view(request):
    testimonials = Testimonial.objects.all()
    return render(request, "testimonial.html", {"testimonials": testimonials})


# -------------------------------------------------------------------
# Booking entry (plan registration landing)
# -------------------------------------------------------------------

def book_plan_view(request, plan_id):
    """
    Redirect to registration for a plan if the visitor is not a logged-in Member.
    Uses signed-cookie member auth (or middleware). Keeps admin auth separate.
    """
    next_url = reverse("plan_registration") + f"?plan_id={plan_id}"
    member = get_current_member(request)
    if not member:
        signup_url = reverse("signup") + f"?next={next_url}"
        return redirect(signup_url)
    return redirect(next_url)


# -------------------------------------------------------------------
# Registration & login flow
# -------------------------------------------------------------------

def registration_view(request):
    """
    Register a site member (creates Member only).
    After registration, redirect the user to the login (signup) page
    and do not log them in automatically.
    """
    if request.method == "POST":
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            form.save()  # creates Member
            return redirect("signup")  # go to login page after registration
    else:
        form = MemberRegistrationForm()
    return render(request, "registration.html", {"form": form})


def login_view(request):
    """
    Login endpoint used by 'signup' route.
    - Try Django auth first (for staff/admin or regular users).
    - If that fails, try Member auth (email or username) and set signed cookie.
    """
    error = None
    username_or_email = ""
    if request.method == "POST":
        username_or_email = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # 1) Django auth
        user = authenticate(request, username=username_or_email, password=password)
        if user:
            login(request, user)
            return _redirect_with_next("home", request)

        # 2) Member auth (email or username)
        member = (
            Member.objects.filter(email__iexact=username_or_email).first()
            or Member.objects.filter(username__iexact=username_or_email).first()
        )
        if member and member.check_password(password):
            response = _redirect_with_next("home", request)
            response.set_signed_cookie(
                MEMBER_COOKIE_NAME,
                str(member.id),
                salt=MEMBER_COOKIE_SALT,
                max_age=MEMBER_COOKIE_MAX_AGE,
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
            )
            return response

        error = "Invalid username/email or password."

    return render(
        request, "signup.html", {"error": error, "username": username_or_email}
    )


def member_login_view(request):
    """
    Member/Django login endpoint that always redirects to home after login.
    """
    error = None
    username_or_email = ""
    if request.method == "POST":
        username_or_email = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # 1) Django auth
        user = authenticate(request, username=username_or_email, password=password)
        if user:
            login(request, user)
            return redirect("home")

        # 2) Member auth
        member = (
            Member.objects.filter(email__iexact=username_or_email).first()
            or Member.objects.filter(username__iexact=username_or_email).first()
        )
        if member and member.check_password(password):
            response = redirect("home")
            response.set_signed_cookie(
                MEMBER_COOKIE_NAME,
                str(member.id),
                salt=MEMBER_COOKIE_SALT,
                max_age=MEMBER_COOKIE_MAX_AGE,
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
            )
            return response

        error = "Invalid username/email or password."

    return render(
        request, "signup.html", {"error": error, "username": username_or_email}
    )


def logout_view(request):
    """
    Logout Django session auth (admin / staff). Does NOT touch member cookie.
    """
    logout(request)
    return redirect("home")


def member_logout_view(request):
    """
    Logout Member cookie auth.
    """
    response = redirect("home")
    response.delete_cookie(MEMBER_COOKIE_NAME)
    return response


def profile_view(request):
    """
    Show profile for the current member.
    If logged in as Django non-staff user, prefer that Member by email.
    Else try signed cookie / middleware.
    """
    member = None
    if request.user.is_authenticated and not request.user.is_staff:
        member = Member.objects.filter(email=request.user.email).first()
    if not member:
        member = get_current_member(request)

    if not member:
        return redirect("member_login")

    return render(request, "profile.html", {"member": member})


# -------------------------------------------------------------------
# Classes / categories
# -------------------------------------------------------------------

def classes_landing(request):
    categories_qs = Category.objects.all()

    if not categories_qs.exists():
        categories = [
            {
                "name": "Yoga & Zumba",
                "slug": "yoga",
                "desc": "Improve mobility, balance and calm.",
            },
            {
                "name": "Weight Lifting & Strength",
                "slug": "weight-lifting",
                "desc": "Build strength and muscle safely.",
            },
        ]
        return render(
            request,
            "category.html",
            {"categories": categories, "is_queryset": False},
        )

    return render(
        request,
        "category.html",
        {"categories": categories_qs, "is_queryset": True},
    )


def classes_by_category(request, slug):
    category_obj = Category.objects.filter(slug=slug).first()
    classes_qs = FitnessClass.objects.none()
    display_name = slug.replace("-", " ").title()

    if category_obj:
        classes_qs = (
            FitnessClass.objects.select_related("category_fk")
            .filter(category_fk=category_obj)
            .order_by("name")
        )
        display_name = category_obj.name
        if not classes_qs.exists():
            classes_qs = (
                FitnessClass.objects.select_related("category_fk")
                .filter(category__iexact=category_obj.name)
                .order_by("name")
            )
    else:
        keywords = slug.replace("-", " ").split()
        q = Q()
        for kw in keywords:
            q |= Q(category__icontains=kw) | Q(name__icontains=kw)
        classes_qs = (
            FitnessClass.objects.select_related("category_fk")
            .filter(q)
            .distinct()
            .order_by("name")
        )

    return render(
        request, "classes.html", {"classes": classes_qs, "category": display_name}
    )


# -------------------------------------------------------------------
# Payment for classes and plans (UPI)
# -------------------------------------------------------------------

def book_class_payment(request, class_id):
    member = get_current_member(request)
    if not member:
        login_url = reverse("signup") + f"?next=/book/class/{class_id}/"
        return redirect(login_url)

    gym_class = get_object_or_404(FitnessClass, pk=class_id)

    real_upi_id = "7774999781@ibl"  # Your real UPI ID
    club_name = "C-Fitness Club"
    upi_qr_url = generate_upi_qr(
        real_upi_id, str(gym_class.price), club_name, gym_class.name
    )

    if request.method == "POST":
        upi_ref = request.POST.get("upi_ref")
        screenshot = request.FILES.get("screenshot")
        UpiPayment.objects.create(
            member=member,
            fitness_class=gym_class,
            amount=gym_class.price,
            upi_ref=upi_ref,
            screenshot=screenshot,
        )
        context = {
            "msg": "Thank you! We'll verify and confirm your booking soon.",
            "amount": gym_class.price,
            "class_name": gym_class.name,
            "upi_id": "7774999781@ibl",
            "upi_qr_url": upi_qr_url,
            "redirect_home": True,
        }
        return render(request, "payment_page.html", context)

    context = {
        "amount": gym_class.price,
        "class_name": gym_class.name,
        "upi_id": "7774999781@ibl",
        "upi_qr_url": upi_qr_url,
    }
    return render(request, "payment_page.html", context)


def book_plan_payment(request, plan_id):
    member = get_current_member(request)
    if not member:
        login_url = reverse("signup") + f"?next=/book/plan/{plan_id}/"
        return redirect(login_url)

    plan = get_object_or_404(Plan, pk=plan_id)

    real_upi_id = "7774999781@ibl"  # Your real UPI ID
    club_name = "C-Fitness Club"
    upi_qr_url = generate_upi_qr(
        real_upi_id, str(plan.price), club_name, plan.name
    )

    if request.method == "POST":
        upi_ref = request.POST.get("upi_ref")
        screenshot = request.FILES.get("screenshot")
        UpiPayment.objects.create(
            member=member,
            plan=plan,
            amount=plan.price,
            upi_ref=upi_ref,
            screenshot=screenshot,
        )
        context = {
            "msg": "Thank you! We'll verify and confirm your membership soon.",
            "amount": plan.price,
            "plan_name": plan.name,
            "upi_id": "7774999781@ibl",
            "upi_qr_url": upi_qr_url,
            "redirect_home": True,
        }
        return render(request, "payment_page.html", context)

    context = {
        "amount": plan.price,
        "plan_name": plan.name,
        "upi_id": "7774999781@ibl",
        "upi_qr_url": upi_qr_url,
    }
    return render(request, "payment_page.html", context)


# -------------------------------------------------------------------
# Utility: create temp superuser
# -------------------------------------------------------------------

def create_temp_superuser(request):
    User = get_user_model()
    if User.objects.filter(username="cfitness").exists():
        return HttpResponse("Superuser already exists.")
    User.objects.create_superuser(
        username="cfitness",
        email="chinmypendke@gmail.com",
        password="cfitness",
    )
    return HttpResponse("Superuser created.")
