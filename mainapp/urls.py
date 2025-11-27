# mainapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Home & static pages
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),

    # Classes: landing and category detail
    path('classes/', views.classes_landing, name='classes'),   # landing page showing categories
    path('classes/<slug:slug>/', views.classes_by_category, name='classes_by_category'),
    path('classes/all/', views.class_list, name='classes_all'),

    # Other content pages
    path('equipment/', views.equipment_view, name='equipment'),
    path('features/', views.features_view, name='features'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('price/', views.plans_view, name='price'),
    path('testimonial/', views.testimonial_view, name='testimonial'),
    path('contact/', views.contact_view, name='contact'),

    # Site member flows (signup.html is used as member login page)
    path('signup/', views.member_login_view, name='signup'),          # member login (site)
    path('register/', views.register_view, name='register'),          # member register

    # Member logout – expose **two names** so templates using either still work
    path('logout/', views.member_logout_view, name='logout'),         # main logout name
    path('member-logout/', views.member_logout_view, name='member_logout'),  # for old `{% url 'member_logout' %}`

    # Profile, booking etc.
    path('profile/', views.profile_view, name='profile'),
    path('book/<int:plan_id>/', views.book_plan_view, name='book_plan'),
    path('registration/', views.registration_view, name='plan_registration'),

    # Optional admin/staff login (uses Django auth)
    path('staff-login/', views.login_view, name='staff_login'),
    path('book/class/<int:class_id>/', views.book_class_payment, name='book_class_payment'),
    path('book/plan/<int:plan_id>/', views.book_plan_payment, name='book_plan_payment'),

    path("create-temp-superuser/", views.create_temp_superuser),
]
