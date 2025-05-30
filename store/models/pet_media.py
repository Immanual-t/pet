# File: store/models/pet_media.py (Updated with datetime fixes)

from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from .boarding import PetBoardingBooking
import os
import datetime


def pet_media_upload_path(instance, filename):
    """Generate upload path for pet media files"""
    # Organize by booking ID and date
    booking_id = instance.booking.id

    # Ensure we have a proper datetime object
    upload_time = instance.uploaded_at if instance.uploaded_at else timezone.now()
    if isinstance(upload_time, datetime.date) and not isinstance(upload_time, datetime.datetime):
        upload_time = datetime.datetime.combine(upload_time, datetime.time.min)
        upload_time = timezone.make_aware(upload_time)

    date_str = upload_time.strftime('%Y/%m/%d') if upload_time else '2025/01/01'

    # Clean filename
    name, ext = os.path.splitext(filename)
    clean_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    clean_filename = f"{clean_name}{ext}".lower()

    return f'pet_media/booking_{booking_id}/{date_str}/{clean_filename}'


class PetMedia(models.Model):
    """Model to store photos and videos of pets during their boarding stay"""

    MEDIA_TYPE_CHOICES = [
        ('photo', 'Photo'),
        ('video', 'Video'),
    ]

    # Link to booking
    booking = models.ForeignKey(
        PetBoardingBooking,
        on_delete=models.CASCADE,
        related_name='media_updates'
    )

    # Media file
    media_file = models.FileField(
        upload_to=pet_media_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    'jpg', 'jpeg', 'png', 'gif', 'webp',  # Photos
                    'mp4', 'webm', 'avi', 'mov', 'm4v'  # Videos
                ]
            )
        ],
        help_text="Supported formats: JPG, PNG, GIF, WebP, MP4, WebM, AVI, MOV"
    )

    # Media type (auto-detected)
    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPE_CHOICES,
        blank=True
    )

    # Optional fields
    caption = models.TextField(
        blank=True,
        max_length=500,
        help_text="Optional description or message for the pet owner"
    )

    # Timestamps - Make sure these are proper DateTimeFields
    uploaded_at = models.DateTimeField(auto_now_add=True, help_text="When this media was uploaded")
    updated_at = models.DateTimeField(auto_now=True, help_text="When this media was last updated")

    # Admin info
    uploaded_by = models.CharField(
        max_length=100,
        default='Pet Paradise Staff',
        help_text="Name of staff member who uploaded this"
    )

    # Visibility
    is_visible = models.BooleanField(
        default=True,
        help_text="Whether this media is visible to the pet owner"
    )

    # Technical fields
    file_size = models.BigIntegerField(blank=True, null=True, help_text="File size in bytes")
    thumbnail = models.ImageField(
        upload_to='pet_media/thumbnails/',
        blank=True,
        null=True,
        help_text="Auto-generated thumbnail for videos"
    )

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Pet Media Update'
        verbose_name_plural = 'Pet Media Updates'
        indexes = [
            models.Index(fields=['booking', '-uploaded_at']),
            models.Index(fields=['media_type', '-uploaded_at']),
        ]

    def save(self, *args, **kwargs):
        # Ensure uploaded_at is set properly
        if not self.uploaded_at:
            self.uploaded_at = timezone.now()

        # Auto-detect media type based on file extension
        if self.media_file and not self.media_type:
            file_ext = os.path.splitext(self.media_file.name)[1].lower()
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                self.media_type = 'photo'
            elif file_ext in ['.mp4', '.webm', '.avi', '.mov', '.m4v']:
                self.media_type = 'video'

        # Store file size
        if self.media_file and hasattr(self.media_file, 'size'):
            self.file_size = self.media_file.size

        super().save(*args, **kwargs)

    def __str__(self):
        # Ensure proper datetime formatting in string representation
        upload_time = self.uploaded_at
        if upload_time:
            if isinstance(upload_time, datetime.datetime):
                time_str = upload_time.strftime('%Y-%m-%d %H:%M')
            else:
                time_str = str(upload_time)
        else:
            time_str = 'Unknown time'

        return f"{self.booking.pet_name} - {self.get_media_type_display()} ({time_str})"

    @property
    def is_photo(self):
        return self.media_type == 'photo'

    @property
    def is_video(self):
        return self.media_type == 'video'

    @property
    def file_size_mb(self):
        """Return file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

    @property
    def file_extension(self):
        """Get file extension"""
        if self.media_file:
            return os.path.splitext(self.media_file.name)[1].lower()
        return ''

    def get_thumbnail_url(self):
        """Get thumbnail URL for display"""
        if self.is_photo:
            return self.media_file.url
        elif self.thumbnail:
            return self.thumbnail.url
        else:
            # Return default video thumbnail
            return '/static/images/video-placeholder.png'

    def get_upload_time_safe(self):
        """Get upload time as a safe datetime object for templates"""
        if not self.uploaded_at:
            return timezone.now()

        if isinstance(self.uploaded_at, datetime.datetime):
            return self.uploaded_at

        # If it's somehow a date, convert to datetime
        if isinstance(self.uploaded_at, datetime.date):
            dt = datetime.datetime.combine(self.uploaded_at, datetime.time.min)
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt

        return timezone.now()

    @staticmethod
    def get_media_for_booking(booking_id):
        """Get all visible media for a specific booking"""
        return PetMedia.objects.filter(
            booking_id=booking_id,
            is_visible=True
        ).order_by('-uploaded_at')

    @staticmethod
    def get_media_for_customer(customer_email):
        """Get all media for bookings belonging to a customer"""
        return PetMedia.objects.filter(
            booking__owner_email=customer_email,
            is_visible=True
        ).order_by('-uploaded_at')

    @staticmethod
    def get_recent_updates(limit=10):
        """Get recent media updates for admin dashboard"""
        return PetMedia.objects.filter(
            is_visible=True
        ).select_related('booking').order_by('-uploaded_at')[:limit]


class MediaViewLog(models.Model):
    """Track when customers view their pet's media updates"""

    media = models.ForeignKey(PetMedia, on_delete=models.CASCADE)
    customer_email = models.EmailField()
    viewed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        unique_together = ['media', 'customer_email']
        ordering = ['-viewed_at']

    def __str__(self):
        view_time = self.viewed_at
        if view_time:
            if isinstance(view_time, datetime.datetime):
                time_str = view_time.strftime('%Y-%m-%d %H:%M')
            else:
                time_str = str(view_time)
        else:
            time_str = 'Unknown time'

        return f"{self.customer_email} viewed {self.media.booking.pet_name}'s media at {time_str}"

    @staticmethod
    def mark_as_viewed(media, customer_email, ip_address=None):
        """Mark media as viewed by customer"""
        obj, created = MediaViewLog.objects.get_or_create(
            media=media,
            customer_email=customer_email,
            defaults={'ip_address': ip_address}
        )
        if not created:
            # Update the viewed_at time
            obj.viewed_at = timezone.now()
            obj.save(update_fields=['viewed_at'])
        return obj