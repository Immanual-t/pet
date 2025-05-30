# File: store/views/pet_media_customer.py

from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from store.models.boarding import PetBoardingBooking
from store.models.pet_media import PetMedia, MediaViewLog
from store.models.customer import Customer
from store.middlewares.auth import CustomerRequiredMixin
import datetime


class PetUpdatesView(CustomerRequiredMixin, View):
    """Customer dashboard to view their pet's media updates"""

    def get(self, request):
        customer_id = request.session.get('customer')
        customer = get_object_or_404(Customer, id=customer_id)

        # Get all customer's bookings with media
        bookings_with_media = PetBoardingBooking.objects.filter(
            owner_email=customer.email
        ).prefetch_related('media_updates').order_by('-start_date')

        # Filter bookings that have media
        bookings_with_updates = []
        for booking in bookings_with_media:
            media_count = booking.media_updates.filter(is_visible=True).count()
            if media_count > 0:
                booking.media_count = media_count
                booking.latest_media = booking.media_updates.filter(
                    is_visible=True
                ).first()
                bookings_with_updates.append(booking)

        # Get recent media across all bookings
        recent_media = PetMedia.get_media_for_customer(customer.email)[:6]

        # Statistics
        stats = {
            'total_updates': PetMedia.get_media_for_customer(customer.email).count(),
            'bookings_with_media': len(bookings_with_updates),
            'updates_this_week': PetMedia.objects.filter(
                booking__owner_email=customer.email,
                is_visible=True,
                uploaded_at__gte=timezone.now() - datetime.timedelta(days=7)
            ).count(),
        }

        context = {
            'customer': customer,
            'bookings_with_updates': bookings_with_updates,
            'recent_media': recent_media,
            'stats': stats,
        }
        return render(request, 'pet_media/customer_dashboard.html', context)


class BookingMediaView(CustomerRequiredMixin, View):
    """View all media for a specific booking"""

    def get(self, request, booking_id):
        customer_id = request.session.get('customer')
        customer = get_object_or_404(Customer, id=customer_id)

        # Get booking and verify ownership
        booking = get_object_or_404(
            PetBoardingBooking,
            id=booking_id,
            owner_email=customer.email
        )

        # Get filter parameters
        media_type = request.GET.get('type', 'all')  # all, photo, video
        sort_by = request.GET.get('sort', 'newest')  # newest, oldest

        # Get media for this booking
        media_query = PetMedia.objects.filter(
            booking=booking,
            is_visible=True
        )

        # Apply filters
        if media_type != 'all':
            media_query = media_query.filter(media_type=media_type)

        # Apply sorting
        if sort_by == 'oldest':
            media_query = media_query.order_by('uploaded_at')
        else:
            media_query = media_query.order_by('-uploaded_at')

        # Pagination
        paginator = Paginator(media_query, 12)  # 12 items per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Mark media as viewed
        ip_address = self.get_client_ip(request)
        for media in page_obj:
            MediaViewLog.mark_as_viewed(media, customer.email, ip_address)

        # Get media counts by type
        media_counts = {
            'total': media_query.count(),
            'photos': PetMedia.objects.filter(
                booking=booking, is_visible=True, media_type='photo'
            ).count(),
            'videos': PetMedia.objects.filter(
                booking=booking, is_visible=True, media_type='video'
            ).count(),
        }

        context = {
            'customer': customer,
            'booking': booking,
            'media_list': page_obj,
            'media_counts': media_counts,
            'current_type': media_type,
            'current_sort': sort_by,
        }
        return render(request, 'pet_media/booking_media.html', context)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class MediaTimelineView(CustomerRequiredMixin, View):
    """Timeline view of all pet media updates for customer"""

    def get(self, request):
        customer_id = request.session.get('customer')
        customer = get_object_or_404(Customer, id=customer_id)

        # Get all media for customer's pets
        all_media = PetMedia.get_media_for_customer(customer.email)

        # Group by date
        grouped_media = {}
        for media in all_media:
            date_key = media.uploaded_at.date()
            if date_key not in grouped_media:
                grouped_media[date_key] = []
            grouped_media[date_key].append(media)

        # Sort dates in descending order
        sorted_dates = sorted(grouped_media.keys(), reverse=True)

        # Pagination by dates (5 dates per page)
        paginator = Paginator(sorted_dates, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Build timeline data
        timeline_data = []
        for date in page_obj:
            timeline_data.append({
                'date': date,
                'media_list': grouped_media[date],
                'count': len(grouped_media[date])
            })

        context = {
            'customer': customer,
            'timeline_data': timeline_data,
            'page_obj': page_obj,
            'total_media': all_media.count(),
        }
        return render(request, 'pet_media/timeline.html', context)


class MediaDetailView(CustomerRequiredMixin, View):
    """Detailed view of a single media item"""

    def get(self, request, media_id):
        customer_id = request.session.get('customer')
        customer = get_object_or_404(Customer, id=customer_id)

        # Get media and verify access
        media = get_object_or_404(
            PetMedia,
            id=media_id,
            booking__owner_email=customer.email,
            is_visible=True
        )

        # Mark as viewed
        ip_address = self.get_client_ip(request)
        MediaViewLog.mark_as_viewed(media, customer.email, ip_address)

        # Get related media from same booking
        related_media = PetMedia.objects.filter(
            booking=media.booking,
            is_visible=True
        ).exclude(id=media_id).order_by('-uploaded_at')[:6]

        context = {
            'customer': customer,
            'media': media,
            'related_media': related_media,
        }
        return render(request, 'pet_media/media_detail.html', context)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class MediaSearchView(CustomerRequiredMixin, View):
    """Search media by caption or date"""

    def get(self, request):
        customer_id = request.session.get('customer')
        customer = get_object_or_404(Customer, id=customer_id)

        query = request.GET.get('q', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        media_type = request.GET.get('type', 'all')

        # Start with customer's media
        media_query = PetMedia.get_media_for_customer(customer.email)

        # Apply search filters
        if query:
            media_query = media_query.filter(
                Q(caption__icontains=query) |
                Q(booking__pet_name__icontains=query) |
                Q(uploaded_by__icontains=query)
            )

        if date_from:
            try:
                from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
                media_query = media_query.filter(uploaded_at__date__gte=from_date)
            except ValueError:
                pass

        if date_to:
            try:
                to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
                media_query = media_query.filter(uploaded_at__date__lte=to_date)
            except ValueError:
                pass

        if media_type != 'all':
            media_query = media_query.filter(media_type=media_type)

        # Pagination
        paginator = Paginator(media_query, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'customer': customer,
            'media_list': page_obj,
            'search_query': query,
            'date_from': date_from,
            'date_to': date_to,
            'media_type': media_type,
            'total_results': media_query.count(),
        }
        return render(request, 'pet_media/search_results.html', context)