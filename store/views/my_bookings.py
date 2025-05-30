# File: store/views/my_bookings.py

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from store.models.boarding import PetBoardingBooking
from store.models.customer import Customer
import datetime

# File: store/views/my_bookings.py

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from store.models.boarding import PetBoardingBooking
from store.models.customer import Customer
from store.middlewares.auth import CustomerRequiredMixin
import datetime


def update_booking_statuses():
    """
    Automatically update booking statuses based on current date and time.
    This is a standalone function until the model method is properly added.
    """
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


def booking_is_active(booking):
    """Check if booking is currently active (pet is being boarded)"""
    today = datetime.date.today()
    now = datetime.datetime.now().time()

    if booking.status != 'approved':
        return False

    # Check if we're within the booking period
    if booking.start_date <= today <= booking.end_date:
        # If it's the start date, check if start time has passed
        if booking.start_date == today and booking.start_time > now:
            return False
        # If it's the end date, check if end time has passed
        if booking.end_date == today and booking.end_time <= now:
            return False
        return True

    return False


def booking_is_upcoming(booking):
    """Check if booking is upcoming (approved but not started)"""
    today = datetime.date.today()
    now = datetime.datetime.now().time()

    if booking.status != 'approved':
        return False

    if booking.start_date > today:
        return True
    elif booking.start_date == today and booking.start_time > now:
        return True

    return False


def booking_is_completed(booking):
    """Check if booking should be considered completed"""
    today = datetime.date.today()
    now = datetime.datetime.now().time()

    if booking.status == 'completed':
        return True

    # Auto-detect completion
    if booking.status == 'approved':
        if booking.end_date < today:
            return True
        elif booking.end_date == today and booking.end_time <= now:
            return True

    return False


def get_booking_display_status(booking):
    """Get display status with additional context"""
    today = datetime.date.today()
    now = datetime.datetime.now().time()

    if booking.status == 'pending':
        return 'Pending Approval'
    elif booking.status == 'approved':
        if booking.start_date > today:
            return 'Upcoming'
        elif booking.start_date <= today and booking.end_date >= today:
            if booking.start_date == today and booking.start_time > now:
                return 'Check-in Today'
            elif booking.end_date == today and booking.end_time <= now:
                return 'Ready for Checkout'
            else:
                return 'Currently Boarding'
        else:
            return 'Completed'  # This should trigger auto-update
    elif booking.status == 'completed':
        return 'Completed'
    elif booking.status == 'cancelled':
        return 'Cancelled'
    elif booking.status == 'rejected':
        return 'Rejected'
    else:
        return booking.get_status_display()


def get_booking_time_status(booking):
    """Get detailed time-based status information"""
    today = datetime.date.today()
    now = datetime.datetime.now().time()

    if booking.status != 'approved':
        return None

    start_datetime = datetime.datetime.combine(booking.start_date, booking.start_time)
    end_datetime = datetime.datetime.combine(booking.end_date, booking.end_time)
    current_datetime = datetime.datetime.combine(today, now)

    if current_datetime < start_datetime:
        time_until = start_datetime - current_datetime
        if time_until.days > 0:
            return f"Starts in {time_until.days} day{'s' if time_until.days != 1 else ''}"
        else:
            hours = time_until.seconds // 3600
            return f"Starts in {hours} hour{'s' if hours != 1 else ''}"
    elif current_datetime > end_datetime:
        return "Should be completed"
    else:
        time_remaining = end_datetime - current_datetime
        if time_remaining.days > 0:
            return f"{time_remaining.days} day{'s' if time_remaining.days != 1 else ''} remaining"
        else:
            hours = time_remaining.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} remaining"


class MyBookingsView(CustomerRequiredMixin, View):
    """Customer's personal booking history and management"""

    def get(self, request):
        # Customer is guaranteed to be logged in due to CustomerRequiredMixin
        customer_id = request.session.get('customer')

        # Auto-update booking statuses before displaying
        update_result = update_booking_statuses()
        if update_result['total_updated'] > 0:
            messages.info(request,
                          f"{update_result['total_updated']} booking(s) automatically updated to completed status.")

        # Get filter parameters
        status_filter = request.GET.get('status', 'all')

        # Get customer's bookings
        customer = get_object_or_404(Customer, id=customer_id)
        bookings = PetBoardingBooking.objects.filter(
            owner_email=customer.email
        ).order_by('-created_at')

        # Apply status filter
        if status_filter != 'all':
            bookings = bookings.filter(status=status_filter)

        # Separate bookings by actual status using helper functions
        today = datetime.date.today()
        now = datetime.datetime.now().time()

        # Current bookings - actually being boarded right now
        current_bookings = []
        # Upcoming bookings - approved but not started
        upcoming_bookings = []
        # Past bookings - completed, cancelled, or overdue
        past_bookings = []

        for booking in PetBoardingBooking.objects.filter(owner_email=customer.email):
            # Add helper methods to booking objects
            booking.is_active = lambda b=booking: booking_is_active(b)
            booking.is_upcoming = lambda b=booking: booking_is_upcoming(b)
            booking.is_completed = lambda b=booking: booking_is_completed(b)
            booking.get_display_status = lambda b=booking: get_booking_display_status(b)
            booking.get_time_status = lambda b=booking: get_booking_time_status(b)

            if booking.is_active():
                current_bookings.append(booking)
            elif booking.is_upcoming():
                upcoming_bookings.append(booking)
            elif booking.is_completed() or booking.status in ['completed', 'cancelled', 'rejected']:
                past_bookings.append(booking)

        # Sort the lists
        current_bookings.sort(key=lambda x: x.end_date)
        upcoming_bookings.sort(key=lambda x: x.start_date)
        past_bookings.sort(key=lambda x: x.end_date, reverse=True)

        # Add helper methods to all bookings for template
        for booking in bookings:
            booking.is_active = lambda b=booking: booking_is_active(b)
            booking.is_upcoming = lambda b=booking: booking_is_upcoming(b)
            booking.is_completed = lambda b=booking: booking_is_completed(b)
            booking.get_display_status = lambda b=booking: get_booking_display_status(b)
            booking.get_time_status = lambda b=booking: get_booking_time_status(b)

        # Pagination for all bookings
        paginator = Paginator(bookings, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Get statistics
        stats = {
            'total_bookings': PetBoardingBooking.objects.filter(owner_email=customer.email).count(),
            'upcoming_bookings': len(upcoming_bookings),
            'current_bookings': len(current_bookings),
            'past_bookings': len(past_bookings),
            'pending_bookings': PetBoardingBooking.objects.filter(owner_email=customer.email, status='pending').count(),
        }

        context = {
            'customer': customer,
            'bookings': page_obj,
            'upcoming_bookings': upcoming_bookings[:5],  # Show only 5 most recent
            'current_bookings': current_bookings,
            'past_bookings': past_bookings[:5],  # Show only 5 most recent
            'stats': stats,
            'status_choices': PetBoardingBooking.STATUS_CHOICES,
            'current_status': status_filter,
            'today': today,
            'now': now,
        }
        return render(request, 'boarding/my_bookings.html', context)


class BookingDetailView(CustomerRequiredMixin, View):
    """View individual booking details"""

    def get(self, request, booking_id):
        # Customer is guaranteed to be logged in due to CustomerRequiredMixin
        customer_id = request.session.get('customer')

        customer = get_object_or_404(Customer, id=customer_id)
        booking = get_object_or_404(
            PetBoardingBooking,
            id=booking_id,
            owner_email=customer.email  # Ensure customer can only see their own bookings
        )

        # Add helper methods to booking object
        booking.is_active = lambda: booking_is_active(booking)
        booking.is_upcoming = lambda: booking_is_upcoming(booking)
        booking.is_completed = lambda: booking_is_completed(booking)
        booking.get_display_status = lambda: get_booking_display_status(booking)
        booking.get_time_status = lambda: get_booking_time_status(booking)

        context = {
            'customer': customer,
            'booking': booking,
            'today': datetime.date.today(),
        }
        return render(request, 'boarding/booking_detail.html', context)


class CancelBookingView(CustomerRequiredMixin, View):
    """Cancel a booking (only if pending or approved and future date)"""

    def post(self, request, booking_id):
        # Customer is guaranteed to be logged in due to CustomerRequiredMixin
        customer_id = request.session.get('customer')

        customer = get_object_or_404(Customer, id=customer_id)
        booking = get_object_or_404(
            PetBoardingBooking,
            id=booking_id,
            owner_email=customer.email
        )

        # Check if booking can be cancelled
        today = datetime.date.today()
        if booking.status in ['completed', 'cancelled']:
            messages.error(request, 'This booking cannot be cancelled.')
        elif booking.start_date <= today:
            messages.error(request, 'Cannot cancel bookings that have already started.')
        else:
            booking.status = 'cancelled'
            booking.admin_notes += f"\nCancelled by customer on {datetime.date.today()}"
            booking.save()
            messages.success(request, f'Booking #{booking.id} has been cancelled successfully.')

        return redirect('my_bookings')