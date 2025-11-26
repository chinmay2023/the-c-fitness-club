# mainapp/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category,
    FitnessClass,
    Feature,
    GalleryImage,
    EquipmentCategory,
    Equipment,
    Plan,
    Testimonial,
    Member,
    HeroSection,
    ContactInquiry,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "image_tag")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    def image_tag(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:80px;height:48px;border-radius:6px;object-fit:cover;" />',
                obj.image.url
            )
        return "-"
    image_tag.short_description = "Image"


@admin.register(FitnessClass)
class FitnessClassAdmin(admin.ModelAdmin):
    list_display = ("thumbnail_tag", "name", "get_category_display", "price")
    list_filter = ("category_fk",)
    search_fields = ("name", "category")
    readonly_fields = ("category", "image_preview")
    fieldsets = (
        (None, {
            "fields": ("name", "category_fk", "category", "price", "image_file", "image_preview")
        }),
    )
    ordering = ("name",)

    def thumbnail_tag(self, obj):
        if obj.image_file:
            return format_html(
                '<img src="{}" style="width:80px;height:auto;border-radius:6px;object-fit:cover;" />',
                obj.image_file.url
            )
        return "-"
    thumbnail_tag.short_description = "Image"

    def image_preview(self, obj):
        if obj.image_file:
            return format_html(
                '<img src="{}" style="max-width:300px;height:auto;border-radius:6px;object-fit:cover;" />',
                obj.image_file.url
            )
        return "No image uploaded."
    image_preview.short_description = "Current image"

from django.contrib import admin
from .models import UpiPayment

@admin.register(UpiPayment)
class UpiPaymentAdmin(admin.ModelAdmin):
    list_display = ('member', 'fitness_class', 'plan', 'amount', 'upi_ref', 'confirmed', 'submitted_at')
    list_filter = ('confirmed', 'submitted_at')
    search_fields = ('member__username', 'upi_ref')


# Register other models (simple registration)
admin.site.register(Feature)
admin.site.register(GalleryImage)
admin.site.register(EquipmentCategory)
admin.site.register(Equipment)
admin.site.register(Plan)
admin.site.register(Testimonial)
admin.site.register(Member)
admin.site.register(HeroSection)
admin.site.register(ContactInquiry)
