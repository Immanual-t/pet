# File: store/views/boarding.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import models
from store.models.boarding import PetBoardingBooking, PetBoardingSlot
from store.models.customer import Customer
import json
import datetime


class PetBoardingView(View):
    """Main pet boarding page with booking form"""

    def get(self, request):
        # Check if customer is logged in
        customer_id = request.session.get('customer')
        if not customer_id:
            # If not logged in, show landing page with login prompt
            context = {
                'user_authenticated': False,
                'login_url': '/login?return_url=/boarding/',
                'signup_url': '/signup'
            }
            return render(request, 'boarding/boarding.html', context)

        # If logged in, get customer data and show booking form
        customer = get_object_or_404(Customer, id=customer_id)
        today = timezone.now().date()

        context = {
            'user_authenticated': True,
            'customer': customer,
            'today': today,
            'pet_types': PetBoardingBooking.PET_TYPE_CHOICES,
            'pricing_types': PetBoardingBooking.PRICING_TYPE_CHOICES,
        }
        return render(request, 'boarding/boarding.html', context)

    def post(self, request):
        # Check if customer is logged in
        customer_id = request.session.get('customer')
        if not customer_id:
            messages.error(request, 'Please login to make a booking.')
            return redirect('/login?return_url=/boarding/')

        try:
            # Get the logged-in customer
            customer = Customer.objects.get(id=customer_id)

            # Extract form data
            data = {
                'pet_name': request.POST.get('pet_name'),
                'pet_type': request.POST.get('pet_type'),
                'pet_age': int(request.POST.get('pet_age', 1)),
                'pet_breed': request.POST.get('pet_breed', ''),
                'owner_name': request.POST.get('owner_name'),
                'owner_phone': request.POST.get('owner_phone'),
                'owner_email': request.POST.get('owner_email'),
                'emergency_contact': request.POST.get('emergency_contact', ''),
                'start_date': datetime.datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date(),
                'start_time': datetime.datetime.strptime(request.POST.get('start_time'), '%H:%M').time(),
                'end_date': datetime.datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date(),
                'end_time': datetime.datetime.strptime(request.POST.get('end_time'), '%H:%M').time(),
                'pricing_type': request.POST.get('pricing_type'),
                'special_instructions': request.POST.get('special_instructions', ''),
                'medical_conditions': request.POST.get('medical_conditions', ''),
                'feeding_instructions': request.POST.get('feeding_instructions', ''),
            }

            # Validate dates
            if data['start_date'] < timezone.now().date():
                messages.error(request, 'Start date cannot be in the past.')
                context = {
                    'form_data': data,
                    'user_authenticated': True,
                    'customer': customer,
                    'today': timezone.now().date(),
                    'pet_types': PetBoardingBooking.PET_TYPE_CHOICES,
                    'pricing_types': PetBoardingBooking.PRICING_TYPE_CHOICES,
                }
                return render(request, 'boarding/boarding.html', context)

            if data['end_date'] < data['start_date']:
                messages.error(request, 'End date cannot be before start date.')
                context = {
                    'form_data': data,
                    'user_authenticated': True,
                    'customer': customer,
                    'today': timezone.now().date(),
                    'pet_types': PetBoardingBooking.PET_TYPE_CHOICES,
                    'pricing_types': PetBoardingBooking.PRICING_TYPE_CHOICES,
                }
                return render(request, 'boarding/boarding.html', context)

            # Check availability
            available, message = PetBoardingBooking.check_availability(data['start_date'], data['end_date'])
            if not available:
                messages.error(request, f'Booking not available: {message}')
                context = {
                    'form_data': data,
                    'user_authenticated': True,
                    'customer': customer,
                    'today': timezone.now().date(),
                    'pet_types': PetBoardingBooking.PET_TYPE_CHOICES,
                    'pricing_types': PetBoardingBooking.PRICING_TYPE_CHOICES,
                }
                return render(request, 'boarding/boarding.html', context)

            # Ensure owner email matches logged-in customer email
            # This is crucial for the booking to appear in "My Bookings"
            data['owner_email'] = customer.email

            # If owner name is not provided, use customer's name
            if not data['owner_name']:
                data['owner_name'] = f"{customer.first_name} {customer.last_name}"

            # If owner phone is not provided, use customer's phone
            if not data['owner_phone']:
                data['owner_phone'] = customer.phone

            # Create booking
            booking = PetBoardingBooking(**data)
            booking.save()

            messages.success(request,
                             f'Booking submitted successfully! Booking ID: {booking.id}. Total cost: ₹{booking.total_price}')
            return redirect('boarding_success', booking_id=booking.id)

        except Customer.DoesNotExist:
            messages.error(request, 'Customer account not found. Please login again.')
            return redirect('/login?return_url=/boarding/')
        except Exception as e:
            messages.error(request, f'Error creating booking: {str(e)}')
            context = {
                'form_data': request.POST,
                'user_authenticated': True,
                'customer': customer,
                'today': timezone.now().date(),
                'pet_types': PetBoardingBooking.PET_TYPE_CHOICES,
                'pricing_types': PetBoardingBooking.PRICING_TYPE_CHOICES,
            }
            return render(request, 'boarding/boarding.html', context)


class BookingSuccessView(View):
    """Booking confirmation page"""

    def get(self, request, booking_id):
        booking = get_object_or_404(PetBoardingBooking, id=booking_id)
        return render(request, 'boarding/booking_success.html', {'booking': booking})


class CheckAvailabilityView(View):
    """AJAX endpoint to check slot availability"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            start_date = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(data['end_date'], '%Y-%m-%d').date()

            available, message = PetBoardingBooking.check_availability(start_date, end_date)

            return JsonResponse({
                'available': available,
                'message': message
            })
        except Exception as e:
            return JsonResponse({
                'available': False,
                'message': f'Error checking availability: {str(e)}'
            })


class CalculatePriceView(View):
    """AJAX endpoint to calculate booking price"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            start_date = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            start_time = datetime.datetime.strptime(data['start_time'], '%H:%M').time()
            end_date = datetime.datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            end_time = datetime.datetime.strptime(data['end_time'], '%H:%M').time()
            pricing_type = data['pricing_type']

            # Create temporary booking to calculate price
            temp_booking = PetBoardingBooking(
                start_date=start_date,
                start_time=start_time,
                end_date=end_date,
                end_time=end_time,
                pricing_type=pricing_type,
                pet_name='temp',
                owner_name='temp',
                owner_phone='temp',
                owner_email='temp@temp.com'
            )
            temp_booking.calculate_duration_and_price()

            return JsonResponse({
                'total_days': temp_booking.total_days,
                'total_hours': temp_booking.total_hours,
                'total_price': float(temp_booking.total_price),
                'pricing_type': pricing_type
            })
        except Exception as e:
            return JsonResponse({
                'error': f'Error calculating price: {str(e)}'
            })


# Admin Views
class BoardingAdminView(View):
    """Admin dashboard for managing bookings"""

    def get(self, request):
        # Auto-update booking statuses before displaying
        PetBoardingBooking.update_booking_statuses()

        # Get filter parameters
        status_filter = request.GET.get('status', 'all')
        date_filter = request.GET.get('date', '')

        # Base queryset
        bookings = PetBoardingBooking.objects.all().order_by('-created_at')

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
            'total_bookings': PetBoardingBooking.objects.count(),
            'pending_bookings': PetBoardingBooking.objects.filter(status='pending').count(),
            'approved_bookings': PetBoardingBooking.objects.filter(status='approved').count(),
            'completed_bookings': PetBoardingBooking.objects.filter(status='completed').count(),
            'current_bookings': PetBoardingBooking.get_current_bookings().count(),
        }

        context = {
            'bookings': page_obj,
            'stats': stats,
            'status_choices': PetBoardingBooking.STATUS_CHOICES,
            'current_status': status_filter,
            'current_date': date_filter,
        }
        return render(request, 'boarding/admin_dashboard.html', context)


class UpdateBookingStatusView(View):
    """Update booking status (approve/reject)"""

    def post(self, request, booking_id):
        try:
            booking = get_object_or_404(PetBoardingBooking, id=booking_id)
            new_status = request.POST.get('status')
            admin_notes = request.POST.get('admin_notes', '')

            if new_status in dict(PetBoardingBooking.STATUS_CHOICES):
                booking.status = new_status
                booking.admin_notes = admin_notes
                booking.save()

                messages.success(request, f'Booking {booking_id} status updated to {new_status}.')
            else:
                messages.error(request, 'Invalid status.')

        except Exception as e:
            messages.error(request, f'Error updating booking: {str(e)}')

        return redirect('boarding_admin')


class SlotManagementView(View):
    """Manage daily slot availability"""

    def get(self, request):
        # Get next 30 days of slots
        today = timezone.now().date()
        end_date = today + datetime.timedelta(days=30)

        slots = []
        current_date = today
        while current_date <= end_date:
            slot = PetBoardingSlot.objects.filter(date=current_date).first()
            if not slot:
                slot = PetBoardingSlot.objects.create(date=current_date)
            slots.append(slot)
            current_date += datetime.timedelta(days=1)

        return render(request, 'boarding/slot_management.html', {'slots': slots, 'today': today})

    def post(self, request):
        try:
            slot_id = request.POST.get('slot_id')
            available_slots = int(request.POST.get('available_slots'))

            slot = get_object_or_404(PetBoardingSlot, id=slot_id)
            slot.available_slots = available_slots
            slot.save()

            messages.success(request, f'Slot availability updated for {slot.date}.')
        except Exception as e:
            messages.error(request, f'Error updating slot: {str(e)}')

        return redirect('slot_management')


class PetBoardingView(View):
    """Main pet boarding page with booking form"""

    def get(self, request):
        # Check if customer is logged in
        customer_id = request.session.get('customer')
        if not customer_id:
            # If not logged in, show landing page with login prompt
            context = {
                'user_authenticated': False,
                'login_url': '/login?return_url=/boarding/',
                'signup_url': '/signup'
            }
            return render(request, 'boarding/boarding.html', context)

        # If logged in, get customer data and show booking form
        customer = get_object_or_404(Customer, id=customer_id)
        today = timezone.now().date()

        context = {
            'user_authenticated': True,
            'customer': customer,
            'today': today,
            'pet_types': PetBoardingBooking.PET_TYPE_CHOICES,
            'pricing_types': PetBoardingBooking.PRICING_TYPE_CHOICES,
        }
        return render(request, 'boarding/boarding.html', context)

    def post(self, request):
        # Check if customer is logged in
        customer_id = request.session.get('customer')
        if not customer_id:
            messages.error(request, 'Please login to make a booking.')
            return redirect('/login?return_url=/boarding/')

        try:
            # Get the logged-in customer
            customer = Customer.objects.get(id=customer_id)

            # Extract form data
            data = {
                'pet_name': request.POST.get('pet_name'),
                'pet_type': request.POST.get('pet_type'),
                'pet_age': int(request.POST.get('pet_age', 1)),
                'pet_breed': request.POST.get('pet_breed', ''),
                'owner_name': request.POST.get('owner_name'),
                'owner_phone': request.POST.get('owner_phone'),
                'owner_email': request.POST.get('owner_email'),
                'emergency_contact': request.POST.get('emergency_contact', ''),
                'start_date': datetime.datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date(),
                'start_time': datetime.datetime.strptime(request.POST.get('start_time'), '%H:%M').time(),
                'end_date': datetime.datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date(),
                'end_time': datetime.datetime.strptime(request.POST.get('end_time'), '%H:%M').time(),
                'pricing_type': request.POST.get('pricing_type'),
                'special_instructions': request.POST.get('special_instructions', ''),
                'medical_conditions': request.POST.get('medical_conditions', ''),
                'feeding_instructions': request.POST.get('feeding_instructions', ''),
            }

            # Validate dates
            if data['start_date'] < timezone.now().date():
                messages.error(request, 'Start date cannot be in the past.')
                context = {
                    'form_data': data,
                    'user_authenticated': True,
                    'customer': customer,
                    'today': timezone.now().date(),
                    'pet_types': PetBoardingBooking.PET_TYPE_CHOICES,
                    'pricing_types': PetBoardingBooking.PRICING_TYPE_CHOICES,
                }
                return render(request, 'boarding/boarding.html', context)

            if data['end_date'] < data['start_date']:
                messages.error(request, 'End date cannot be before start date.')
                context = {
                    'form_data': data,
                    'user_authenticated': True,
                    'customer': customer,
                    'today': timezone.now().date(),
                    'pet_types': PetBoardingBooking.PET_TYPE_CHOICES,
                    'pricing_types': PetBoardingBooking.PRICING_TYPE_CHOICES,
                }
                return render(request, 'boarding/boarding.html', context)

            # Check availability
            available, message = PetBoardingBooking.check_availability(data['start_date'], data['end_date'])
            if not available:
                messages.error(request, f'Booking not available: {message}')
                context = {
                    'form_data': data,
                    'user_authenticated': True,
                    'customer': customer,
                    'today': timezone.now().date(),
                    'pet_types': PetBoardingBooking.PET_TYPE_CHOICES,
                    'pricing_types': PetBoardingBooking.PRICING_TYPE_CHOICES,
                }
                return render(request, 'boarding/boarding.html', context)

            # Ensure owner email matches logged-in customer email
            # This is crucial for the booking to appear in "My Bookings"
            data['owner_email'] = customer.email

            # If owner name is not provided, use customer's name
            if not data['owner_name']:
                data['owner_name'] = f"{customer.first_name} {customer.last_name}"

            # If owner phone is not provided, use customer's phone
            if not data['owner_phone']:
                data['owner_phone'] = customer.phone

            # Create booking
            booking = PetBoardingBooking(**data)
            booking.save()

            messages.success(request,
                             f'Booking submitted successfully! Booking ID: {booking.id}. Total cost: ₹{booking.total_price}')
            return redirect('boarding_success', booking_id=booking.id)

        except Customer.DoesNotExist:
            messages.error(request, 'Customer account not found. Please login again.')
            return redirect('/login?return_url=/boarding/')
        except Exception as e:
            messages.error(request, f'Error creating booking: {str(e)}')
            context = {
                'form_data': request.POST,
                'user_authenticated': True,
                'today': timezone.now().date(),
                'pet_types': PetBoardingBooking.PET_TYPE_CHOICES,
                'pricing_types': PetBoardingBooking.PRICING_TYPE_CHOICES,
            }
            return render(request, 'boarding/boarding.html', context)


class BookingSuccessView(View):
    """Booking confirmation page"""

    def get(self, request, booking_id):
        booking = get_object_or_404(PetBoardingBooking, id=booking_id)
        return render(request, 'boarding/booking_success.html', {'booking': booking})


class CheckAvailabilityView(View):
    """AJAX endpoint to check slot availability"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            start_date = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(data['end_date'], '%Y-%m-%d').date()

            available, message = PetBoardingBooking.check_availability(start_date, end_date)

            return JsonResponse({
                'available': available,
                'message': message
            })
        except Exception as e:
            return JsonResponse({
                'available': False,
                'message': f'Error checking availability: {str(e)}'
            })


class CalculatePriceView(View):
    """AJAX endpoint to calculate booking price"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            start_date = datetime.datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            start_time = datetime.datetime.strptime(data['start_time'], '%H:%M').time()
            end_date = datetime.datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            end_time = datetime.datetime.strptime(data['end_time'], '%H:%M').time()
            pricing_type = data['pricing_type']

            # Create temporary booking to calculate price
            temp_booking = PetBoardingBooking(
                start_date=start_date,
                start_time=start_time,
                end_date=end_date,
                end_time=end_time,
                pricing_type=pricing_type,
                pet_name='temp',
                owner_name='temp',
                owner_phone='temp',
                owner_email='temp@temp.com'
            )
            temp_booking.calculate_duration_and_price()

            return JsonResponse({
                'total_days': temp_booking.total_days,
                'total_hours': temp_booking.total_hours,
                'total_price': float(temp_booking.total_price),
                'pricing_type': pricing_type
            })
        except Exception as e:
            return JsonResponse({
                'error': f'Error calculating price: {str(e)}'
            })


# Admin Views
class BoardingAdminView(View):
    """Admin dashboard for managing bookings"""

    def get(self, request):
        # Get filter parameters
        status_filter = request.GET.get('status', 'all')
        date_filter = request.GET.get('date', '')

        # Base queryset
        bookings = PetBoardingBooking.objects.all().order_by('-created_at')

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
            'total_bookings': PetBoardingBooking.objects.count(),
            'pending_bookings': PetBoardingBooking.objects.filter(status='pending').count(),
            'approved_bookings': PetBoardingBooking.objects.filter(status='approved').count(),
            'completed_bookings': PetBoardingBooking.objects.filter(status='completed').count(),
        }

        context = {
            'bookings': page_obj,
            'stats': stats,
            'status_choices': PetBoardingBooking.STATUS_CHOICES,
            'current_status': status_filter,
            'current_date': date_filter,
        }
        return render(request, 'boarding/admin_dashboard.html', context)


class UpdateBookingStatusView(View):
    """Update booking status (approve/reject)"""

    def post(self, request, booking_id):
        try:
            booking = get_object_or_404(PetBoardingBooking, id=booking_id)
            new_status = request.POST.get('status')
            admin_notes = request.POST.get('admin_notes', '')

            if new_status in dict(PetBoardingBooking.STATUS_CHOICES):
                booking.status = new_status
                booking.admin_notes = admin_notes
                booking.save()

                messages.success(request, f'Booking {booking_id} status updated to {new_status}.')
            else:
                messages.error(request, 'Invalid status.')

        except Exception as e:
            messages.error(request, f'Error updating booking: {str(e)}')

        return redirect('boarding_admin')


class SlotManagementView(View):
    """Manage daily slot availability"""

    def get(self, request):
        # Get next 30 days of slots
        today = timezone.now().date()
        end_date = today + datetime.timedelta(days=30)

        slots = []
        current_date = today
        while current_date <= end_date:
            slot = PetBoardingSlot.objects.filter(date=current_date).first()
            if not slot:
                slot = PetBoardingSlot.objects.create(date=current_date)
            slots.append(slot)
            current_date += datetime.timedelta(days=1)

        return render(request, 'boarding/slot_management.html', {'slots': slots})

    def post(self, request):
        try:
            slot_id = request.POST.get('slot_id')
            available_slots = int(request.POST.get('available_slots'))

            slot = get_object_or_404(PetBoardingSlot, id=slot_id)
            slot.available_slots = available_slots
            slot.save()

            messages.success(request, f'Slot availability updated for {slot.date}.')
        except Exception as e:
            messages.error(request, f'Error updating slot: {str(e)}')

        return redirect('slot_management')