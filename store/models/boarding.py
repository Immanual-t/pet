# File: store/models/boarding.py
# Add these methods to the PetBoardingBooking class

from django.db import models
from django.core.validators import MinValueValidator
import datetime
from decimal import Decimal


class PetBoardingSlot(models.Model):
    """Model to manage boarding slot availability"""
    date = models.DateField()
    available_slots = models.PositiveIntegerField(default=20)  # Total slots per day
    booked_slots = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['date']

    @property
    def remaining_slots(self):
        return self.available_slots - self.booked_slots

    @property
    def is_available(self):
        return self.remaining_slots > 0

    def __str__(self):
        return f"{self.date} - {self.remaining_slots} slots remaining"


class PetBoardingBooking(models.Model):
    PET_TYPE_CHOICES = [
        ('dog', 'Dog'),
        ('cat', 'Cat'),
        ('bird', 'Bird'),
        ('rabbit', 'Rabbit'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PRICING_TYPE_CHOICES = [
        ('daily', 'Daily (₹500/day)'),
        ('hourly', 'Hourly (₹100/hour)'),
    ]

    # Pet Information
    pet_name = models.CharField(max_length=100)
    pet_type = models.CharField(max_length=20, choices=PET_TYPE_CHOICES)
    pet_age = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text="Age in months")
    pet_breed = models.CharField(max_length=100, blank=True)

    # Owner Information
    owner_name = models.CharField(max_length=100)
    owner_phone = models.CharField(max_length=15)
    owner_email = models.EmailField()
    emergency_contact = models.CharField(max_length=15, blank=True)

    # Booking Details
    start_date = models.DateField()
    start_time = models.TimeField()
    end_date = models.DateField()
    end_time = models.TimeField()
    pricing_type = models.CharField(max_length=10, choices=PRICING_TYPE_CHOICES, default='daily')

    # Calculated Fields
    total_days = models.PositiveIntegerField(default=0)
    total_hours = models.PositiveIntegerField(default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Additional Information
    special_instructions = models.TextField(blank=True, help_text="Any special care instructions")
    medical_conditions = models.TextField(blank=True, help_text="Any medical conditions or medications")
    feeding_instructions = models.TextField(blank=True, help_text="Feeding schedule and preferences")

    # Status and Timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_notes = models.TextField(blank=True, help_text="Internal notes for admin")

    def save(self, *args, **kwargs):
        # Calculate duration and price before saving
        self.calculate_duration_and_price()
        super().save(*args, **kwargs)

        # Update slot availability
        self.update_slot_availability()

    def calculate_duration_and_price(self):
        """Calculate total duration and price based on booking dates"""
        start_datetime = datetime.datetime.combine(self.start_date, self.start_time)
        end_datetime = datetime.datetime.combine(self.end_date, self.end_time)

        total_duration = end_datetime - start_datetime

        if self.pricing_type == 'daily':
            self.total_days = total_duration.days
            if total_duration.seconds > 0:  # If there are extra hours, count as extra day
                self.total_days += 1
            self.total_price = Decimal(self.total_days * 500)
        else:  # hourly
            self.total_hours = int(total_duration.total_seconds() / 3600)
            if total_duration.total_seconds() % 3600 > 0:  # Round up partial hours
                self.total_hours += 1
            self.total_price = Decimal(self.total_hours * 100)

    def update_slot_availability(self):
        """Update slot availability for booking dates"""
        if self.status == 'approved':
            current_date = self.start_date
            while current_date <= self.end_date:
                slot, created = PetBoardingSlot.objects.get_or_create(
                    date=current_date,
                    defaults={'available_slots': 20, 'booked_slots': 0}
                )
                if created or slot.booked_slots < slot.available_slots:
                    slot.booked_slots += 1
                    slot.save()
                current_date += datetime.timedelta(days=1)

    @staticmethod
    def check_availability(start_date, end_date):
        """Check if slots are available for the given date range"""
        current_date = start_date
        while current_date <= end_date:
            slot = PetBoardingSlot.objects.filter(date=current_date).first()
            if slot and not slot.is_available:
                return False, f"No slots available on {current_date}"
            elif not slot:
                # Create new slot if doesn't exist
                PetBoardingSlot.objects.create(date=current_date)
            current_date += datetime.timedelta(days=1)
        return True, "Slots available"

    @staticmethod
    def get_bookings_by_status(status):
        return PetBoardingBooking.objects.filter(status=status).order_by('-created_at')

    @staticmethod
    def get_all_bookings():
        return PetBoardingBooking.objects.all().order_by('-created_at')

    @staticmethod
    def get_current_bookings():
        """Get bookings that are currently active (pets are being boarded)"""
        today = datetime.date.today()
        now = datetime.datetime.now().time()

        current_bookings = []
        for booking in PetBoardingBooking.objects.filter(status='approved'):
            # Check if booking is currently active
            if booking.start_date <= today <= booking.end_date:
                # If it's the start date, check if start time has passed
                if booking.start_date == today and booking.start_time > now:
                    continue
                # If it's the end date, check if end time has passed
                if booking.end_date == today and booking.end_time <= now:
                    continue
                current_bookings.append(booking)

        return current_bookings

    @staticmethod
    def update_booking_statuses():
        """Automatically update booking statuses based on current date and time"""
        today = datetime.date.today()
        now = datetime.datetime.now().time()

        # Mark overdue bookings as completed
        overdue_bookings = PetBoardingBooking.objects.filter(
            status='approved',
            end_date__lt=today
        )

        overdue_count = 0
        for booking in overdue_bookings:
            booking.status = 'completed'
            booking.admin_notes += f'\nAuto-completed on {today} (overdue)'
            booking.save()
            overdue_count += 1

        # Mark bookings that ended today and past end time as completed
        today_ended_bookings = PetBoardingBooking.objects.filter(
            status='approved',
            end_date=today,
            end_time__lt=now
        )

        today_ended_count = 0
        for booking in today_ended_bookings:
            booking.status = 'completed'
            booking.admin_notes += f'\nAuto-completed on {today} at {now.strftime("%H:%M")}'
            booking.save()
            today_ended_count += 1

        return {
            'overdue_completed': overdue_count,
            'today_completed': today_ended_count,
            'total_updated': overdue_count + today_ended_count
        }

    def __str__(self):
        return f"{self.pet_name} ({self.owner_name}) - {self.start_date} to {self.end_date}"