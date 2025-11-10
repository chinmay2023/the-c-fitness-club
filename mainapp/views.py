# mainapp/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q

from .models import (
    HeroSection, FitnessClass, GalleryImage, EquipmentCategory,
    Feature, Plan, Testimonial, Member, Category
)
from .forms import ContactForm, RegistrationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


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
    next_url = reverse('plan_registration') + f'?plan_id={plan_id}'
    if 'member_id' not in request.session:
        signup_url = reverse('signup') + f'?next={next_url}'
        return redirect(signup_url)
    return redirect(next_url)


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('signup')
    else:
        form = RegistrationForm()
    return render(request, 'registration.html', {'form': form})


def login_view(request):
    error = None
    username = ''
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            error = "Invalid username or password."
    return render(request, 'signup.html', {'error': error, 'username': username})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile_view(request):
    member = Member.objects.filter(email=request.user.email).first()
    return render(request, 'profile.html', {'member': member})


def registration_view(request):
    member_id = request.session.get('member_id')
    if not member_id:
        return redirect('signup')

    plan_id = request.GET.get('plan_id')
    plan = get_object_or_404(Plan, id=plan_id) if plan_id else None
    member = get_object_or_404(Member, id=member_id)
    return render(request, 'registration.html', {'plan': plan, 'member': member})


def member_login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            member = Member.objects.get(email=email)
            if member.check_password(password):
                request.session['member_id'] = member.id
                return redirect('home')
        except Member.DoesNotExist:
            pass
    return render(request, 'member_login.html')


def member_logout_view(request):
    if 'member_id' in request.session:
        del request.session['member_id']
    return redirect('member_login')


def classes_landing(request):
    """
    Category landing page. Use a QuerySet of Category objects (so templates can access
    cat.image.url and cat.description directly). If the DB has no categories we fall
    back to static tiles (dicts).
    """
    # keep as a QuerySet (do NOT convert to list)
    categories_qs = Category.objects.all()

    if not categories_qs.exists():
        categories = [
            {"name": "Yoga & Zumba", "slug": "yoga", "desc": "Improve mobility, balance and calm."},
            {"name": "Weight Lifting & Strength", "slug": "weight-lifting", "desc": "Build strength and muscle safely."},
        ]
        # tell template this is not a queryset (so it can fall back)
        return render(request, 'category.html', {"categories": categories, "is_queryset": False})

    # pass the actual QuerySet so cat.image and cat.description are available in template
    return render(request, 'category.html', {"categories": categories_qs, "is_queryset": True})



def classes_by_category(request, slug):
    """
    Strict category filtering:
    1) If a Category with the slug exists -> return classes with that FK ONLY.
       (This guarantees yoga classes appear only under yoga.)
    2) If FK yields no classes, attempt a legacy exact-text match (category__iexact).
       Note: this is exact (not contains) to avoid cross-category leakage.
    3) If no Category object exists, fall back to a safe keyword search on legacy text fields.
    """
    category_obj = Category.objects.filter(slug=slug).first()
    classes_qs = FitnessClass.objects.none()
    display_name = slug.replace('-', ' ').title()

    if category_obj:
        # Primary: strict FK lookup
        classes_qs = FitnessClass.objects.select_related('category_fk').filter(category_fk=category_obj).order_by('name')
        display_name = category_obj.name

        # Fallback: try exact legacy match only (no contains)
        if not classes_qs.exists():
            classes_qs = FitnessClass.objects.select_related('category_fk').filter(category__iexact=category_obj.name).order_by('name')
    else:
        # No Category row -> best-effort legacy search (split words from slug)
        keywords = slug.replace('-', ' ').split()
        q = Q()
        for kw in keywords:
            q |= Q(category__icontains=kw) | Q(name__icontains=kw)
        classes_qs = FitnessClass.objects.select_related('category_fk').filter(q).distinct().order_by('name')

    return render(request, 'classes.html', {"classes": classes_qs, "category": display_name})
