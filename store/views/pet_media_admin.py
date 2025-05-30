# File: store/views/pet_media_admin.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from store.models.boarding import PetBoardingBooking
from store.models.pet_media import PetMedia, MediaViewLog
from store.views.my_bookings import booking_is_active  # Import helper function
import json
import datetime


class MediaAdminDashboardView(View):
    """Admin dashboard for managing pet media updates"""

    def get(self, request):
        # Get currently boarded pets
        current_bookings = []
        for booking in PetBoardingBooking.objects.filter(status='approved'):
            if booking_is_active(booking):
                # Count existing media for this booking
                media_count = PetMedia.objects.filter(booking=booking).count()
                booking.media_count = media_count
                current_bookings.append(booking)

        # Sort by check-in date
        current_bookings.sort(key=lambda x: x.start_date)

        # Get recent media uploads
        recent_media = PetMedia.get_recent_updates(limit=10)

        # Get statistics
        stats = {
            'active_boardings': len(current_bookings),
            'total_media': PetMedia.objects.count(),
            'recent_uploads': PetMedia.objects.filter(
                uploaded_at__gte=timezone.now() - datetime.timedelta(days=7)
            ).count(),
            'total_views': MediaViewLog.objects.count(),
        }

        context = {
            'current_bookings': current_bookings,
            'recent_media': recent_media,
            'stats': stats,
        }
        return render(request, 'pet_media/admin_dashboard.html', context)


class MediaUploadView(View):
    """Upload media for a specific pet boarding"""

    def get(self, request, booking_id=None):
        # Get current bookings for dropdown
        current_bookings = []
        for booking in PetBoardingBooking.objects.filter(status='approved'):
            if booking_is_active(booking):
                current_bookings.append(booking)

        current_bookings.sort(key=lambda x: x.start_date)

        # Get selected booking if provided
        selected_booking = None
        if booking_id:
            try:
                selected_booking = get_object_or_404(PetBoardingBooking, id=booking_id)
                if not booking_is_active(selected_booking):
                    messages.warning(request, 'This pet is not currently being boarded.')
                    selected_booking = None
            except:
                messages.error(request, 'Booking not found.')

        context = {
            'current_bookings': current_bookings,
            'selected_booking': selected_booking,
        }
        return render(request, 'pet_media/upload_form.html', context)

    def post(self, request, booking_id=None):
        try:
            # Get booking
            booking_id = booking_id or request.POST.get('booking_id')
            booking = get_object_or_404(PetBoardingBooking, id=booking_id)

            # Verify booking is currently active
            if not booking_is_active(booking):
                messages.error(request, 'Can only upload media for pets currently being boarded.')
                return redirect('media_upload')

            # Get form data
            caption = request.POST.get('caption', '')
            uploaded_by = request.POST.get('uploaded_by', 'Pet Paradise Staff')

            # Process uploaded files
            uploaded_files = request.FILES.getlist('media_files')
            if not uploaded_files:
                messages.error(request, 'Please select at least one file to upload.')
                return redirect('media_upload', booking_id=booking_id)

            success_count = 0
            error_count = 0

            for file in uploaded_files:
                try:
                    # Create media object
                    media = PetMedia(
                        booking=booking,
                        media_file=file,
                        caption=caption,
                        uploaded_by=uploaded_by
                    )
                    media.save()
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    messages.error(request, f'Error uploading {file.name}: {str(e)}')

            if success_count > 0:
                messages.success(request,
                                 f'Successfully uploaded {success_count} file(s) for {booking.pet_name}!')

            if error_count > 0:
                messages.warning(request, f'{error_count} file(s) failed to upload.')

            return redirect('media_manage', booking_id=booking_id)

        except Exception as e:
            messages.error(request, f'Error processing upload: {str(e)}')
            return redirect('media_upload')


class MediaManageView(View):
    """Manage media for a specific booking"""

    def get(self, request, booking_id):
        booking = get_object_or_404(PetBoardingBooking, id=booking_id)

        # Get all media for this booking
        media_list = PetMedia.objects.filter(booking=booking).order_by('-uploaded_at')

        # Pagination
        paginator = Paginator(media_list, 12)  # 12 items per page for grid layout
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Get view statistics
        total_views = MediaViewLog.objects.filter(
            media__booking=booking
        ).count()

        context = {
            'booking': booking,
            'media_list': page_obj,
            'total_media': media_list.count(),
            'total_views': total_views,
            'is_currently_boarding': booking_is_active(booking),
        }
        return render(request, 'pet_media/manage_media.html', context)


class MediaDeleteView(View):
    """Delete a media file"""

    def post(self, request, media_id):
        try:
            media = get_object_or_404(PetMedia, id=media_id)
            booking_id = media.booking.id
            pet_name = media.booking.pet_name

            # Delete the file and database record
            if media.media_file:
                media.media_file.delete()
            if media.thumbnail:
                media.thumbnail.delete()

            media.delete()

            messages.success(request, f'Media deleted successfully for {pet_name}.')

        except Exception as e:
            messages.error(request, f'Error deleting media: {str(e)}')
            booking_id = request.POST.get('booking_id', '')

        return redirect('media_manage', booking_id=booking_id)


class MediaToggleVisibilityView(View):
    """Toggle media visibility"""

    def post(self, request, media_id):
        try:
            media = get_object_or_404(PetMedia, id=media_id)
            media.is_visible = not media.is_visible
            media.save()

            status = 'visible' if media.is_visible else 'hidden'
            messages.success(request, f'Media is now {status} to the pet owner.')

            return JsonResponse({
                'success': True,
                'is_visible': media.is_visible,
                'message': f'Media is now {status}'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })


class MediaBulkActionsView(View):
    """Handle bulk actions on media"""

    def post(self, request):
        try:
            action = request.POST.get('action')
            media_ids = request.POST.getlist('media_ids')

            if not media_ids:
                messages.error(request, 'Please select at least one media file.')
                return redirect(request.META.get('HTTP_REFERER', '/'))

            media_objects = PetMedia.objects.filter(id__in=media_ids)

            if action == 'delete':
                count = media_objects.count()
                for media in media_objects:
                    if media.media_file:
                        media.media_file.delete()
                    if media.thumbnail:
                        media.thumbnail.delete()
                media_objects.delete()
                messages.success(request, f'Deleted {count} media file(s).')

            elif action == 'hide':
                count = media_objects.update(is_visible=False)
                messages.success(request, f'Hidden {count} media file(s) from pet owners.')

            elif action == 'show':
                count = media_objects.update(is_visible=True)
                messages.success(request, f'Made {count} media file(s) visible to pet owners.')

            else:
                messages.error(request, 'Invalid action.')

        except Exception as e:
            messages.error(request, f'Error performing bulk action: {str(e)}')

        return redirect(request.META.get('HTTP_REFERER', '/'))


# File: store/views/pet_media_admin.py (Updated MediaAnalyticsView)

class MediaAnalyticsView(View):
    """Analytics for media uploads and views - Updated to include today"""

    def get(self, request):
        # Get date range from query params
        days = int(request.GET.get('days', 30))
        today = timezone.now().date()
        start_date = today - datetime.timedelta(days=days - 1)  # Include today in the count

        # Upload statistics
        uploads_by_day = {}
        views_by_day = {}

        # Initialize all dates with 0 (including today)
        current_date = start_date
        while current_date <= today:
            date_key = current_date.isoformat()
            uploads_by_day[date_key] = 0
            views_by_day[date_key] = 0
            current_date += datetime.timedelta(days=1)

        # Get uploads and views data (including today)
        uploads = PetMedia.objects.filter(uploaded_at__date__gte=start_date, uploaded_at__date__lte=today)
        views = MediaViewLog.objects.filter(viewed_at__date__gte=start_date, viewed_at__date__lte=today)

        # Process data for charts (including today)
        for media in uploads:
            date_key = media.uploaded_at.date().isoformat()
            if date_key in uploads_by_day:
                uploads_by_day[date_key] += 1

        for view in views:
            date_key = view.viewed_at.date().isoformat()
            if date_key in views_by_day:
                views_by_day[date_key] += 1

        # Sort by date (most recent first, so today appears at top)
        uploads_by_day = dict(sorted(uploads_by_day.items(), reverse=True))
        views_by_day = dict(sorted(views_by_day.items(), reverse=True))

        # Convert date keys to readable format while preserving order
        uploads_by_day_formatted = {}
        views_by_day_formatted = {}

        for date_str, count in uploads_by_day.items():
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if date_obj == today:
                formatted_date = f"Today ({date_obj.strftime('%b %d')})"
            elif date_obj == today - datetime.timedelta(days=1):
                formatted_date = f"Yesterday ({date_obj.strftime('%b %d')})"
            else:
                formatted_date = date_obj.strftime('%b %d, %Y')
            uploads_by_day_formatted[formatted_date] = count

        for date_str, count in views_by_day.items():
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if date_obj == today:
                formatted_date = f"Today ({date_obj.strftime('%b %d')})"
            elif date_obj == today - datetime.timedelta(days=1):
                formatted_date = f"Yesterday ({date_obj.strftime('%b %d')})"
            else:
                formatted_date = date_obj.strftime('%b %d, %Y')
            views_by_day_formatted[formatted_date] = count

        # Today's specific stats
        today_uploads = uploads.filter(uploaded_at__date=today).count()
        today_views = views.filter(viewed_at__date=today).count()

        # Get current active boardings (pets currently being boarded)
        from store.views.my_bookings import booking_is_active
        active_boardings = 0
        pending_uploads = 0

        for booking in PetBoardingBooking.objects.filter(status='approved'):
            if booking_is_active(booking):
                active_boardings += 1
                # Check if this pet has received updates today
                today_media = PetMedia.objects.filter(
                    booking=booking,
                    uploaded_at__date=today
                ).count()
                if today_media == 0:
                    pending_uploads += 1

        # Top performing content
        popular_media = PetMedia.objects.annotate(
            view_count=Count('mediaviewlog')
        ).order_by('-view_count')[:10]

        context = {
            'uploads_by_day': uploads_by_day_formatted,
            'views_by_day': views_by_day_formatted,
            'popular_media': popular_media,
            'total_uploads': uploads.count(),
            'total_views': views.count(),
            'today_uploads': today_uploads,
            'today_views': today_views,
            'today_date': f"Today ({today.strftime('%b %d')})",
            'active_boardings': active_boardings,
            'pending_uploads': pending_uploads,
            'days': days,
        }
        return render(request, 'pet_media/analytics.html', context)