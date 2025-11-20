# mainapp/views.py
"""
Corrected views for mainapp.

Key fixes:
- `login_view` now supports both Django user auth (session) and Member auth (signed cookie).
  It will try Django auth first (for staff/admin). If that fails it will try Member auth.
- All member sign-in/out uses a signed cookie (MEMBER_COOKIE_NAME). We never call
  django.contrib.auth.login() for Members so Django admin/session remains separate.
- `register_view` (Member registration) respects optional `next` query and signs-in the member via cookie.
- `member_login_view` kept as an explicit member-only login endpoint; `login_view` acts as a combined endpoint too.
- Next parameter handling added so redirects return the user to the intended page.
"""
from urllib.parse import urlparse, urlunparse, urlencode

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import (
    HeroSection, FitnessClass, GalleryImage, EquipmentCategory,
    Feature, Plan, Testimonial, Member, Category
)
from .forms import ContactForm, MemberRegistrationForm

# Cookie settings for member auth
MEMBER_COOKIE_NAME = "member_auth"
MEMBER_COOKIE_SALT = "mainapp-member-auth-salt"
MEMBER_COOKIE_MAX_AGE = 60 * 60 * 24 * 14  # 14 days


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
        signed_val = request.get_signed_cookie(MEMBER_COOKIE_NAME, default=None, salt=MEMBER_COOKIE_SALT)
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
    next_url = request.GET.get('next') or request.POST.get('next')
    if next_url:
        # Very simple safety check: allow only internal URLs (no scheme/netloc)
        parsed = urlparse(next_url)
        if not parsed.scheme and not parsed.netloc:
            return redirect(next_url)
    return redirect(default_name)


def home_view(request):
    hero = HeroSection.objects.first()
    if not hero:
        hero = HeroSection()
    return render(request, 'index.html', {'hero': hero})


def about_view(request):
    images = GalleryImage.objects.all()
    features = Feature.objects.all()
    testimonials = Testimonial.objects.all()
    return render(request, 'about.html', {
        'images': images,
        'features': features,
        'testimonials': testimonials,
    })


def class_list(request):
    classes = FitnessClass.objects.select_related('category_fk').all()
    return render(request, 'classes.html', {'classes': classes})


def gallery_view(request):
    images = GalleryImage.objects.all()
    return render(request, 'gallery.html', {'images': images})


def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message was submitted. We'll get back to you soon.")
            return redirect('contact')
    else:
        form = ContactForm()
    return render(request, 'contact.html', {'form': form})


def equipment_view(request):
    categories = EquipmentCategory.objects.prefetch_related('equipment_set').all()
    return render(request, 'equipment.html', {'categories': categories})


def features_view(request):
    features = Feature.objects.all()
    return render(request, 'features.html', {'features': features})


def plans_view(request):
    plans = Plan.objects.all()
    return render(request, 'price.html', {'plans': plans})


def testimonial_view(request):
    testimonials = Testimonial.objects.all()
    return render(request, 'testimonial.html', {'testimonials': testimonials})


def book_plan_view(request, plan_id):
    """
    Redirect to registration for a plan if the visitor is not a logged-in Member.
    Uses signed-cookie member auth (or middleware). Keeps admin auth separate.
    """
    next_url = reverse('plan_registration') + f'?plan_id={plan_id}'
    member = get_current_member(request)
    if not member:
        signup_url = reverse('signup') + f'?next={next_url}'
        return redirect(signup_url)
    return redirect(next_url)


def register_view(request):
    """
    Register a site member (creates Member only).
    After saving Member, set the signed cookie so member is logged in to the site.
    """
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            member = form.save()  # expected to return Member instance

            # Set signed cookie so this member is logged into the site (separate from Django admin)
            response = _redirect_with_next('home', request)
            response.set_signed_cookie(
                MEMBER_COOKIE_NAME,
                str(member.id),
                salt=MEMBER_COOKIE_SALT,
                max_age=MEMBER_COOKIE_MAX_AGE,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax'
            )
           
            return response
    else:
        form = MemberRegistrationForm()

    return render(request, 'registration.html', {'form': form})


def login_view(request):
    """
    Combined login endpoint used by your 'signup' route in urls.py.
    Behaviour:
      - Try Django auth first (staff/admin & regular Django users)
      - If Django auth fails, attempt Member auth (email or username) and set signed cookie.
    This keeps Django session and Member cookie distinct.
    """
    error = None
    username_or_email = ''
    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # 1) Try Django auth first (this preserves admin/session and avoids overriding admin auth)
        user = authenticate(request, username=username_or_email, password=password)
        if user:
            login(request, user)
            return _redirect_with_next('home', request)

        # 2) Try Member auth (email or username). Do not call django.login for members.
        member = None
        try:
            member = Member.objects.filter(email__iexact=username_or_email).first()
            if not member:
                member = Member.objects.filter(username__iexact=username_or_email).first()
        except Exception:
            member = None

        if member and member.check_password(password):
            response = _redirect_with_next('home', request)
            response.set_signed_cookie(
                MEMBER_COOKIE_NAME,
                str(member.id),
                salt=MEMBER_COOKIE_SALT,
                max_age=MEMBER_COOKIE_MAX_AGE,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax'
            )
           
            return response

       

    # Render the same signup.html template (used as login form in your project).
    # Ensure the form posts to the correct URL (the current route).
    return render(request, 'signup.html', {'error': error, 'username': username_or_email})


def logout_view(request):
    """
    Logout Django session auth (admin / staff). This does NOT touch member cookie.
    Use member_logout_view to sign out site members.
    """
    logout(request)
    return redirect('home')


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
        return redirect('member_login')

    return render(request, 'profile.html', {'member': member})


def registration_view(request):
    """
    Register a site member (creates Member only).
    After registration, redirect the user to the login (signup) page and do not log them in automatically.
    """
    if request.method == 'POST':
        form = MemberRegistrationForm(request.POST)
        if form.is_valid():
            form.save()  # expected to return Member instance
            return redirect('signup')  # <--- Send user to login form after registration
    else:
        form = MemberRegistrationForm()
    return render(request, 'registration.html', {'form': form})


def member_login_view(request):
    """
    Combined login endpoint used by your 'signup' route in urls.py.
    After login, always redirects to home.
    """
    error = None
    username_or_email = ''
    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # 1) Try Django auth first (this preserves admin/session and avoids overriding admin auth)
        user = authenticate(request, username=username_or_email, password=password)
        if user:
            login(request, user)
            return redirect('home')

        # 2) Try Member auth (email or username). Do not call django.login for members.
        member = None
        try:
            member = Member.objects.filter(email__iexact=username_or_email).first()
            if not member:
                member = Member.objects.filter(username__iexact=username_or_email).first()
        except Exception:
            member = None

        if member and member.check_password(password):
            response = redirect('home')  # <--- Always go home after login
            response.set_signed_cookie(
                MEMBER_COOKIE_NAME,
                str(member.id),
                salt=MEMBER_COOKIE_SALT,
                max_age=MEMBER_COOKIE_MAX_AGE,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax'
            )
            
            return response

        

    # Render the same signup.html template (used as login form in your project).
    return render(request, 'signup.html', {'error': error, 'username': username_or_email})





def member_logout_view(request):
    response = redirect('home')
    response.delete_cookie(MEMBER_COOKIE_NAME)
    return response


def classes_landing(request):
    categories_qs = Category.objects.all()

    if not categories_qs.exists():
        categories = [
            {"name": "Yoga & Zumba", "slug": "yoga", "desc": "Improve mobility, balance and calm."},
            {"name": "Weight Lifting & Strength", "slug": "weight-lifting", "desc": "Build strength and muscle safely."},
        ]
        return render(request, 'category.html', {"categories": categories, "is_queryset": False})

    return render(request, 'category.html', {"categories": categories_qs, "is_queryset": True})


def classes_by_category(request, slug):
    category_obj = Category.objects.filter(slug=slug).first()
    classes_qs = FitnessClass.objects.none()
    display_name = slug.replace('-', ' ').title()

    if category_obj:
        classes_qs = FitnessClass.objects.select_related('category_fk').filter(category_fk=category_obj).order_by('name')
        display_name = category_obj.name
        if not classes_qs.exists():
            classes_qs = FitnessClass.objects.select_related('category_fk').filter(category__iexact=category_obj.name).order_by('name')
    else:
        keywords = slug.replace('-', ' ').split()
        q = Q()
        for kw in keywords:
            q |= Q(category__icontains=kw) | Q(name__icontains=kw)
        classes_qs = FitnessClass.objects.select_related('category_fk').filter(q).distinct().order_by('name')

    return render(request, 'classes.html', {"classes": classes_qs, "category": display_name})
