# File: store/models/training.py
# Create this new file in store/models/ directory

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
import datetime
from decimal import Decimal


class PetTrainingSlot(models.Model):
    """Model to manage training slot availability"""
    date = models.DateField()
    available_slots = models.PositiveIntegerField(default=10)  # Training slots per day
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
        return f"{self.date} - {self.remaining_slots} training slots remaining"


class PetTrainingProgram(models.Model):
    """Model for training programs"""
    PET_TYPE_CHOICES = [
        ('dog', 'Dog'),
        ('cat', 'Cat'),
    ]

    pet_type = models.CharField(max_length=10, choices=PET_TYPE_CHOICES)
    program_name = models.CharField(max_length=100)
    description = models.TextField()
    duration_weeks = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.program_name} for {self.get_pet_type_display()}s"


class PetTrainingBooking(models.Model):
    """Model for pet training bookings - reusing boarding structure"""

    PET_TYPE_CHOICES = [
        ('dog', 'Dog'),
        ('cat', 'Cat'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved - Training Scheduled'),
        ('in_progress', 'Training in Progress'),
        ('completed', 'Training Completed'),
        ('cancelled', 'Cancelled'),
    ]

    SKILL_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    # Pet Information
    pet_name = models.CharField(max_length=100)
    pet_type = models.CharField(max_length=10, choices=PET_TYPE_CHOICES)
    pet_age = models.PositiveIntegerField(validators=[MinValueValidator(1)], help_text="Age in months")
    pet_breed = models.CharField(max_length=100, blank=True)
    current_skill_level = models.CharField(max_length=20, choices=SKILL_LEVELS, default='beginner')

    # Owner Information
    owner_name = models.CharField(max_length=100)
    owner_phone = models.CharField(max_length=15)
    owner_email = models.EmailField()
    emergency_contact = models.CharField(max_length=15, blank=True)

    # Training Details
    start_date = models.DateField()
    end_date = models.DateField()  # Auto-calculated as start_date + 7 days
    training_time_slot = models.CharField(
        max_length=20,
        choices=[
            ('morning', 'Morning (9:00 AM - 12:00 PM)'),
            ('afternoon', 'Afternoon (1:00 PM - 4:00 PM)'),
            ('evening', 'Evening (5:00 PM - 8:00 PM)'),
        ],
        default='morning'
    )

    # Pricing
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Training-specific fields
    training_goals = models.TextField(help_text="What would you like your pet to learn?")
    behavioral_issues = models.TextField(blank=True, help_text="Any behavioral problems to address?")
    previous_training = models.TextField(blank=True, help_text="Any previous training experience?")
    special_requirements = models.TextField(blank=True, help_text="Any special requirements or notes?")

    # Progress tracking
    current_day = models.PositiveIntegerField(default=0)  # Current training day (0-7)
    obedience_score = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])  # 0-100
    socialization_score = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    leash_training_score = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    basic_commands_score = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    # Status and Timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_notes = models.TextField(blank=True, help_text="Internal notes for trainers")

    # Trainer assignment
    assigned_trainer = models.CharField(max_length=100, blank=True, default="Pet Paradise Trainer")

    def save(self, *args, **kwargs):
        # Auto-calculate end date (1 week training)
        if self.start_date:
            self.end_date = self.start_date + datetime.timedelta(days=7)

        # Set price based on pet type
        if self.pet_type == 'dog':
            self.total_price = Decimal('2500')  # ₹2500 for dogs
        elif self.pet_type == 'cat':
            self.total_price = Decimal('2000')  # ₹2000 for cats

        super().save(*args, **kwargs)

        # Update slot availability
        if self.status == 'approved':
            self.update_slot_availability()

    def update_slot_availability(self):
        """Update slot availability for training dates"""
        current_date = self.start_date
        while current_date <= self.end_date:
            slot, created = PetTrainingSlot.objects.get_or_create(
                date=current_date,
                defaults={'available_slots': 10, 'booked_slots': 0}
            )
            if created or slot.booked_slots < slot.available_slots:
                slot.booked_slots += 1
                slot.save()
            current_date += datetime.timedelta(days=1)

    @property
    def progress_percentage(self):
        """Calculate overall training progress"""
        if self.current_day == 0:
            return 0
        return min(int((self.current_day / 7) * 100), 100)

    @property
    def average_skill_score(self):
        """Calculate average skill score"""
        scores = [self.obedience_score, self.socialization_score,
                  self.leash_training_score, self.basic_commands_score]
        return sum(scores) / len(scores) if any(scores) else 0

    @property
    def days_remaining(self):
        """Calculate days remaining in training"""
        return max(0, 7 - self.current_day)

    @property
    def is_active(self):
        """Check if training is currently active"""
        today = timezone.now().date()
        return (self.status in ['approved', 'in_progress'] and
                self.start_date <= today <= self.end_date)

    @staticmethod
    def check_availability(start_date):
        """Check if training slots are available for the given start date"""
        end_date = start_date + datetime.timedelta(days=7)
        current_date = start_date

        while current_date <= end_date:
            slot = PetTrainingSlot.objects.filter(date=current_date).first()
            if slot and not slot.is_available:
                return False, f"No training slots available on {current_date}"
            elif not slot:
                # Create new slot if doesn't exist
                PetTrainingSlot.objects.create(date=current_date)
            current_date += datetime.timedelta(days=1)
        return True, "Training slots available"

    @staticmethod
    def get_training_schedule():
        """Get the 7-day training schedule"""
        schedule = {
            1: {
                'title': 'Orientation & Basic Assessment',
                'activities': ['Meet & greet', 'Behavioral assessment', 'Basic commands evaluation'],
                'icon': '👋'
            },
            2: {
                'title': 'Obedience Foundation',
                'activities': ['Sit, stay, come commands', 'Focus and attention training', 'Positive reinforcement'],
                'icon': '🎯'
            },
            3: {
                'title': 'Socialization Training',
                'activities': ['Meeting other pets', 'Human interaction', 'Confidence building'],
                'icon': '🤝'
            },
            4: {
                'title': 'Leash Training',
                'activities': ['Proper walking technique', 'Heel command', 'Loose leash walking'],
                'icon': '🚶'
            },
            5: {
                'title': 'Advanced Commands',
                'activities': ['Down, wait, place commands', 'Impulse control', 'Problem-solving'],
                'icon': '🧠'
            },
            6: {
                'title': 'Behavioral Correction',
                'activities': ['Address specific issues', 'Redirect unwanted behavior', 'Reinforcement'],
                'icon': '🔧'
            },
            7: {
                'title': 'Graduation & Assessment',
                'activities': ['Final skill test', 'Owner training session', 'Graduation ceremony'],
                'icon': '🎓'
            }
        }
        return schedule

    @staticmethod
    def get_bookings_by_status(status):
        return PetTrainingBooking.objects.filter(status=status).order_by('-created_at')

    def __str__(self):
        return f"{self.pet_name} ({self.owner_name}) - Training {self.start_date} to {self.end_date}"


class PetTrainingProgress(models.Model):
    """Model to track daily training progress"""

    booking = models.ForeignKey(PetTrainingBooking, on_delete=models.CASCADE, related_name='progress_entries')
    day_number = models.PositiveIntegerField()  # 1-7
    date = models.DateField()

    # Daily scores (0-100)
    obedience_score = models.PositiveIntegerField(default=0)
    socialization_score = models.PositiveIntegerField(default=0)
    leash_training_score = models.PositiveIntegerField(default=0)
    basic_commands_score = models.PositiveIntegerField(default=0)

    # Notes and observations
    trainer_notes = models.TextField(blank=True)
    behavior_observations = models.TextField(blank=True)
    homework_for_owner = models.TextField(blank=True)

    # Progress indicators
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['booking', 'day_number']
        ordering = ['day_number']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Update the main booking scores with the latest progress
        if self.completed:
            self.booking.current_day = self.day_number
            self.booking.obedience_score = self.obedience_score
            self.booking.socialization_score = self.socialization_score
            self.booking.leash_training_score = self.leash_training_score
            self.booking.basic_commands_score = self.basic_commands_score

            # Update status based on progress
            if self.day_number == 7:
                self.booking.status = 'completed'
            elif self.day_number >= 1:
                self.booking.status = 'in_progress'

            self.booking.save()

    def __str__(self):
        return f"{self.booking.pet_name} - Day {self.day_number} ({self.date})"