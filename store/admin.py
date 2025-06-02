from django.contrib import admin
from .models import SliderImage
from .models.product import Product
from .models.category import Category
from .models.customer import Customer
from .models.orders import Order
from .models import CustomerReview
from .models.boarding import PetBoardingBooking, PetBoardingSlot


# -------------------
# Product Admin
# -------------------
class AdminProduct(admin.ModelAdmin):
    list_display = ['name', 'price', 'category']


class CategoryProduct(admin.ModelAdmin):
    list_display = ['name']


class CustomerProduct(admin.ModelAdmin):
    list_display = ['first_name', 'last_name']


# -------------------
# Slider Image Admin
# -------------------
class SliderImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'uploaded_at']


# -------------------
# Pet Boarding Admin
# -------------------
class PetBoardingBookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'pet_name', 'owner_name', 'start_date', 'end_date', 'status', 'total_price', 'created_at']
    list_filter = ['status', 'pet_type', 'pricing_type', 'start_date', 'created_at']
    search_fields = ['pet_name', 'owner_name', 'owner_email', 'owner_phone']
    readonly_fields = ['total_days', 'total_hours', 'total_price', 'created_at', 'updated_at']

    fieldsets = (
        ('Pet Information', {
            'fields': ('pet_name', 'pet_type', 'pet_age', 'pet_breed')
        }),
        ('Owner Information', {
            'fields': ('owner_name', 'owner_phone', 'owner_email', 'emergency_contact')
        }),
        ('Booking Details', {
            'fields': ('start_date', 'start_time', 'end_date', 'end_time', 'pricing_type')
        }),
        ('Calculated Fields', {
            'fields': ('total_days', 'total_hours', 'total_price'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('special_instructions', 'medical_conditions', 'feeding_instructions')
        }),
        ('Status & Admin', {
            'fields': ('status', 'admin_notes', 'created_at', 'updated_at')
        })
    )

    def save_model(self, request, obj, form, change):
        obj.calculate_duration_and_price()
        super().save_model(request, obj, form, change)


class PetBoardingSlotAdmin(admin.ModelAdmin):
    list_display = ['date', 'available_slots', 'booked_slots', 'remaining_slots', 'is_available']
    list_filter = ['date', 'available_slots']
    ordering = ['date']

    def remaining_slots(self, obj):
        return obj.remaining_slots

    remaining_slots.short_description = 'Remaining'

    def is_available(self, obj):
        return obj.is_available

    is_available.boolean = True
    is_available.short_description = 'Available'


# -------------------
# Register all models
# -------------------
admin.site.register(Product, AdminProduct)
admin.site.register(Category, CategoryProduct)
admin.site.register(Customer, CustomerProduct)
admin.site.register(SliderImage, SliderImageAdmin)
admin.site.register(PetBoardingBooking, PetBoardingBookingAdmin)
admin.site.register(PetBoardingSlot, PetBoardingSlotAdmin)
admin.site.register(Order)
admin.site.register(CustomerReview)