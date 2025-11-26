# mainapp/models.py
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils.text import slugify


class HeroSection(models.Model):
    # Added title & subtitle because views/templates expect them
    title = models.CharField(max_length=200, blank=True, default="Welcome to Our Gym")
    subtitle = models.CharField(max_length=300, blank=True, default="Your Fitness Journey Starts Here")
    hero_image = models.ImageField(upload_to="upload/", null=True, blank=True)

    def __str__(self):
        return self.title or "Hero Section"


class Category(models.Model):
    """
    Canonical category entity (e.g., 'Yoga & Zumba', 'Weight Lifting & Strength').
    Added `image` and `description` so templates can render category tiles from admin uploads.
    """
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)  # optional textual description
    image = models.ImageField(upload_to="category/", null=True, blank=True)  # admin-uploaded category image

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class FitnessClass(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    # Legacy free-text category kept for backward compatibility during migration.
    category = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="(Legacy) Free-text category; will be replaced by Category FK."
    )
    # New normalized relation
    category_fk = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classes"
    )
    price = models.DecimalField(max_digits=7, decimal_places=2)
    image_file = models.ImageField(upload_to="fitness_class/", blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def get_category_display(self) -> str:
        """Prefer FK name; fall back to legacy text."""
        if self.category_fk:
            return self.category_fk.name
        return self.category or ""

    @property
    def image_url(self) -> str:
        """Safe access in templates."""
        return self.image_file.url if self.image_file else ""

    def __str__(self):
        return self.name


class ContactInquiry(models.Model):
    email = models.EmailField()
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return self.email


class EquipmentCategory(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Equipment(models.Model):
    category = models.ForeignKey(EquipmentCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Feature(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=100, blank=True)  # CSS or SVG icon

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class GalleryImage(models.Model):
    image_file = models.ImageField(upload_to="gallery/")
    title = models.CharField(max_length=100)
    caption = models.CharField(max_length=300)
    quote = models.CharField(max_length=300)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Plan(models.Model):
    name = models.CharField(max_length=50)
    membership = models.CharField(max_length=100)
    duration = models.CharField(max_length=10)
    price = models.CharField(max_length=30)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    review = models.TextField()
    profile_photo = models.ImageField(upload_to="uploads/", null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Member(models.Model):
    username = models.CharField(max_length=100, unique=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    join_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-join_date"]

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.username

from django.conf import settings

class UpiPayment(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    # Either class or plan, use null=True/blank=True for flexible relation
    fitness_class = models.ForeignKey(FitnessClass, null=True, blank=True, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    upi_ref = models.CharField(max_length=100)
    screenshot = models.ImageField(upload_to="upi_screenshots/", null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    confirmed = models.BooleanField(default=False)  # Set True manually in admin after bank/UPI check

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.member} | {self.amount} | Verified: {self.confirmed}"
