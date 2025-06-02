# File: store/views/training.py
# Create this new file in store/views/ directory

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from store.models.training import PetTrainingBooking, PetTrainingSlot, PetTrainingProgress
from store.models.customer import Customer
from store.models.pet_media import PetMedia
import json
import datetime
from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
from store.models import PetTrainingBooking


class PetTrainingView(View):
    def get(self, request):
        return render(request, 'training/training.html', {
            'user_authenticated': False,
            'training_schedule': {}
        })

class TrainingSuccessView(View):
    def get(self, request, booking_id):
        return render(request, 'training/training_success.html', {})

class CheckTrainingAvailabilityView(View):
    def post(self, request):
        return JsonResponse({'available': True, 'message': 'Available'})

class PetTrainingView(View):
    """Main pet training page with booking form"""

    def get(self, request):
        # Check if customer is logged in
        customer_id = request.session.get('customer')
        if not customer_id:
            # If not logged in, show landing page with login prompt
            context = {
                'user_authenticated': False,
                'login_url': '/login?return_url=/training/',
                'signup_url': '/signup',
                'training_schedule': PetTrainingBooking.get_training_schedule(),
            }
            return render(request, 'training/training.html', context)

        # If logged in, get customer data and show booking form
        customer = get_object_or_404(Customer, id=customer_id)
        today = timezone.now().date()

        context = {
            'user_authenticated': True,
            'customer': customer,
            'today': today,
            'pet_types': PetTrainingBooking.PET_TYPE_CHOICES,
            'skill_levels': PetTrainingBooking.SKILL_LEVELS,
            'time_slots': [
                ('morning', 'Morning (9:00 AM - 12:00 PM)'),
                ('afternoon', 'Afternoon (1:00 PM - 4:00 PM)'),
                ('evening', 'Evening (5:00 PM - 8:00 PM)'),
            ],
            'training_schedule': PetTrainingBooking.get_training_schedule(),
        }
        return render(request, 'training/training.html', context)

    def post(self, request):
        # Check if customer is logged in
        customer_id = request.session.get('customer')
        if not customer_id:
            messages.error(request, 'Please login to book training.')
            return redirect('/login?return_url=/training/')

        try:
            # Get the logged-in customer
            customer = Customer.objects.get(id=customer_id)

            # Extract form data
            data = {
                'pet_name': request.POST.get('pet_name'),
                'pet_type': request.POST.get('pet_type'),
                'pet_age': int(request.POST.get('pet_age', 1)),
                'pet_breed': request.POST.get('pet_breed', ''),
                'current_skill_level': request.POST.get('current_skill_level'),
                'owner_name': request.POST.get('owner_name'),
                'owner_phone': request.POST.get('owner_phone'),
                'owner_email': request.POST.get('owner_email'),
                'emergency_contact': request.POST.get('emergency_contact', ''),
                'start_date': datetime.datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date(),
                'training_time_slot': request.POST.get('training_time_slot'),
                'training_goals': request.POST.get('training_goals', ''),
                'behavioral_issues': request.POST.get('behavioral_issues', ''),
                'previous_training': request.POST.get('previous_training', ''),
                'special_requirements': request.POST.get('special_requirements', ''),
            }

            # Validate dates
            if data['start_date'] < timezone.now().date():
                messages.error(request, 'Start date cannot be in the past.')
                return self._render_form_with_data(request, customer, data)

            # Check availability
            available, message = PetTrainingBooking.check_availability(data['start_date'])
            if not available:
                messages.error(request, f'Training not available: {message}')
                return self._render_form_with_data(request, customer, data)

            # Ensure owner email matches logged-in customer email
            data['owner_email'] = customer.email

            # If owner name is not provided, use customer's name
            if not data['owner_name']:
                data['owner_name'] = f"{customer.first_name} {customer.last_name}"

            # If owner phone is not provided, use customer's phone
            if not data['owner_phone']:
                data['owner_phone'] = customer.phone

            # Create training booking
            training = PetTrainingBooking(**data)
            training.save()

            messages.success(request,
                             f'Training booking submitted successfully! Booking ID: {training.id}. '
                             f'Total cost: ₹{training.total_price}. Training duration: 1 week.')
            return redirect('training_success', booking_id=training.id)

        except Customer.DoesNotExist:
            messages.error(request, 'Customer account not found. Please login again.')
            return redirect('/login?return_url=/training/')
        except Exception as e:
            messages.error(request, f'Error creating training booking: {str(e)}')
            return self._render_form_with_data(request, customer, request.POST)

    def _render_form_with_data(self, request, customer, form_data):
        """Helper method to render form with existing data"""
        today = timezone.now().date()
        context = {
            'form_data': form_data,
            'user_authenticated': True,
            'customer': customer,
            'today': today,
            'pet_types': PetTrainingBooking.PET_TYPE_CHOICES,
            'skill_levels': PetTrainingBooking.SKILL_LEVELS,
            'time_slots': [
                ('morning', 'Morning (9:00 AM - 12:00 PM)'),
                ('afternoon', 'Afternoon (1:00 PM - 4:00 PM)'),
                ('evening', 'Evening (5:00 PM - 8:00 PM)'),
            ],
            'training_schedule': PetTrainingBooking.get_training_schedule(),
        }
        return render(request, 'training/training.html', context)


class TrainingSuccessView(View):
    """Training booking confirmation page"""

    def get(self, request, booking_id):
        booking = get_object_or_404(PetTrainingBooking, id=booking_id)
        training_schedule = PetTrainingBooking.get_training_schedule()

        context = {
            'booking': booking,
            'training_schedule': training_schedule,
        }
        return render(request, 'training/training_success.html', context)


class CheckTrainingAvailabilityView(View):
    """AJAX endpoint to check training slot availability"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            start_date = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d').date()

            available, message = PetTrainingBooking.check_availability(start_date)

            # Calculate training cost based on pet type
            pet_type = data.get('pet_type', 'dog')
            if pet_type == 'dog':
                cost = 2500
            elif pet_type == 'cat':
                cost = 2000
            else:
                cost = 2500

            return JsonResponse({
                'available': available,
                'message': message,
                'cost': cost,
                'end_date': (start_date + datetime.timedelta(days=7)).strftime('%Y-%m-%d')
            })
        except Exception as e:
            return JsonResponse({
                'available': False,
                'message': f'Error checking availability: {str(e)}'
            })


class MyTrainingBookingsView(View):
    """View customer's training bookings"""

    def get(self, request):
        # Check if customer is logged in
        customer_id = request.session.get('customer')
        if not customer_id:
            messages.error(request, 'Please login to view your training bookings.')
            return redirect('/login?return_url=/my-training-bookings/')

        try:
            customer = Customer.objects.get(id=customer_id)

            # Get customer's training bookings
            bookings = PetTrainingBooking.objects.filter(
                owner_email=customer.email
            ).order_by('-created_at')

            # Add progress percentage to each booking
            for booking in bookings:
                if booking.status in ['in_progress', 'completed']:
                    # Get progress entries for this booking
                    progress_entries = PetTrainingProgress.objects.filter(
                        booking=booking, completed=True
                    ).order_by('day_number')
                    booking.progress_entries = progress_entries
                else:
                    booking.progress_entries = []

            # Pagination
            paginator = Paginator(bookings, 6)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)

            context = {
                'bookings': page_obj,
                'customer': customer,
                'training_schedule': PetTrainingBooking.get_training_schedule(),
            }
            return render(request, 'training/my_training_bookings.html', context)

        except Customer.DoesNotExist:
            messages.error(request, 'Customer account not found.')
            return redirect('/login')


class TrainingDetailView(View):
    """Detailed view of a specific training booking"""

    def get(self, request, booking_id):
        # Check if customer is logged in
        customer_id = request.session.get('customer')
        if not customer_id:
            messages.error(request, 'Please login to view training details.')
            return redirect('/login')

        try:
            customer = Customer.objects.get(id=customer_id)
            booking = get_object_or_404(
                PetTrainingBooking,
                id=booking_id,
                owner_email=customer.email
            )

            # Get training progress
            progress_entries = PetTrainingProgress.objects.filter(
                booking=booking
            ).order_by('day_number')

            # Get media updates for this training
            media_updates = PetMedia.objects.filter(
                booking__id=booking_id,  # This might need to be adjusted based on your media system
                is_visible=True
            ).order_by('-uploaded_at')[:10]

            # Get training schedule
            training_schedule = PetTrainingBooking.get_training_schedule()

            context = {
                'booking': booking,
                'progress_entries': progress_entries,
                'media_updates': media_updates,
                'training_schedule': training_schedule,
            }
            return render(request, 'training/training_detail.html', context)

        except Customer.DoesNotExist:
            messages.error(request, 'Customer account not found.')
            return redirect('/login')


# Admin Views for Training Management

class TrainingAdminView(View):
    """Admin dashboard for managing training bookings"""

    def get(self, request):
        # Get filter parameters
        status_filter = request.GET.get('status', 'all')
        date_filter = request.GET.get('date', '')

        # Base queryset
        bookings = PetTrainingBooking.objects.all().order_by('-created_at')

        # Apply filters
        if status_filter != 'all':
            bookings = bookings.filter(status=status_filter)

        if date_filter:
            filter_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
            bookings = bookings.filter(start_date=filter_date)

        # Pagination
        paginator = Paginator(bookings, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Get statistics
        stats = {
            'total_bookings': PetTrainingBooking.objects.count(),
            'pending_bookings': PetTrainingBooking.objects.filter(status='pending').count(),
            'approved_bookings': PetTrainingBooking.objects.filter(status='approved').count(),
            'in_progress_bookings': PetTrainingBooking.objects.filter(status='in_progress').count(),
            'completed_bookings': PetTrainingBooking.objects.filter(status='completed').count(),
            'average_score': PetTrainingBooking.objects.filter(
                status='completed'
            ).aggregate(
                avg_score=Avg('obedience_score')
            )['avg_score'] or 0,
        }

        context = {
            'bookings': page_obj,
            'stats': stats,
            'status_choices': PetTrainingBooking.STATUS_CHOICES,
            'current_status': status_filter,
            'current_date': date_filter,
            'training_schedule': PetTrainingBooking.get_training_schedule(),
        }
        return render(request, 'training/admin_dashboard.html', context)


class UpdateTrainingStatusView(View):
    """Update training booking status"""

    def post(self, request, booking_id):
        try:
            booking = get_object_or_404(PetTrainingBooking, id=booking_id)
            new_status = request.POST.get('status')
            admin_notes = request.POST.get('admin_notes', '')

            if new_status in dict(PetTrainingBooking.STATUS_CHOICES):
                booking.status = new_status
                booking.admin_notes = admin_notes
                booking.save()

                messages.success(request, f'Training booking {booking_id} status updated to {new_status}.')
            else:
                messages.error(request, 'Invalid status.')

        except Exception as e:
            messages.error(request, f'Error updating training booking: {str(e)}')

        return redirect('training_admin')


class TrainingProgressUpdateView(View):
    """Update daily training progress"""

    def get(self, request, booking_id):
        booking = get_object_or_404(PetTrainingBooking, id=booking_id)

        # Get existing progress entries
        progress_entries = PetTrainingProgress.objects.filter(
            booking=booking
        ).order_by('day_number')

        # Create missing progress entries
        for day in range(1, 8):
            if not progress_entries.filter(day_number=day).exists():
                date = booking.start_date + datetime.timedelta(days=day - 1)
                PetTrainingProgress.objects.create(
                    booking=booking,
                    day_number=day,
                    date=date
                )

        # Refresh progress entries
        progress_entries = PetTrainingProgress.objects.filter(
            booking=booking
        ).order_by('day_number')

        context = {
            'booking': booking,
            'progress_entries': progress_entries,
            'training_schedule': PetTrainingBooking.get_training_schedule(),
        }
        return render(request, 'training/progress_update.html', context)

    def post(self, request, booking_id):
        try:
            booking = get_object_or_404(PetTrainingBooking, id=booking_id)
            day_number = int(request.POST.get('day_number'))

            progress, created = PetTrainingProgress.objects.get_or_create(
                booking=booking,
                day_number=day_number,
                defaults={
                    'date': booking.start_date + datetime.timedelta(days=day_number - 1)
                }
            )

            # Update scores
            progress.obedience_score = int(request.POST.get('obedience_score', 0))
            progress.socialization_score = int(request.POST.get('socialization_score', 0))
            progress.leash_training_score = int(request.POST.get('leash_training_score', 0))
            progress.basic_commands_score = int(request.POST.get('basic_commands_score', 0))

            # Update notes
            progress.trainer_notes = request.POST.get('trainer_notes', '')
            progress.behavior_observations = request.POST.get('behavior_observations', '')
            progress.homework_for_owner = request.POST.get('homework_for_owner', '')

            # Mark as completed
            progress.completed = True
            progress.save()

            messages.success(request, f'Day {day_number} progress updated for {booking.pet_name}!')
            return redirect('training_progress_update', booking_id=booking_id)

        except Exception as e:
            messages.error(request, f'Error updating progress: {str(e)}')
            return redirect('training_progress_update', booking_id=booking_id)