# mainapp/urls.py
from django.urls import path
from . import views
from .views import member_login_view, member_logout_view

urlpatterns = [
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),

    # Classes: landing and category detail
    path('classes/', views.classes_landing, name='classes'),   # landing page showing categories
    path('classes/<slug:slug>/', views.classes_by_category, name='classes_by_category'),
    path('classes/all/', views.class_list, name='classes_all'),

    path('equipment/', views.equipment_view, name='equipment'),
    path('features/', views.features_view, name='features'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('price/', views.plans_view, name='price'),
    path('testimonial/', views.testimonial_view, name='testimonial'),
    path('contact/', views.contact_view, name='contact'),

    path('signup/', views.login_view, name='signup'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    path('book/<int:plan_id>/', views.book_plan_view, name='book_plan'),
    path('registration/', views.registration_view, name='plan_registration'),
    path('member-login/', member_login_view, name='member_login'),
    path('member-logout/', member_logout_view, name='member_logout'),
]
