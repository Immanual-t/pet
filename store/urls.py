# File: store/urls.py
# Complete version with training URLs

from django.contrib import admin
from django.urls import path
from store.views import home, login, signup, cart, checkout, orders, first, boarding, my_bookings, pet_media_admin, pet_media_customer, training
from .middlewares.auth import auth_middleware

urlpatterns = [
    path('', home.Index.as_view(), name='homepage'),
    path('signup', signup.Signup.as_view(), name='signup'),
    path('login', login.Login.as_view(), name='login'),
    path('logout', login.logout, name='logout'),
    path('cart', cart.Cart.as_view(), name='cart'),
    path('check-out', checkout.Checkout.as_view(), name='checkout'),
    path('orders', auth_middleware(orders.OrderView.as_view()), name='orders'),
    path('first', first.First.as_view(), name='first'),

    # Pet Boarding URLs
    path('boarding/', boarding.PetBoardingView.as_view(), name='pet_boarding'),
    path('boarding/success/<int:booking_id>/', boarding.BookingSuccessView.as_view(), name='boarding_success'),
    path('boarding/check-availability/', boarding.CheckAvailabilityView.as_view(), name='check_availability'),
    path('boarding/calculate-price/', boarding.CalculatePriceView.as_view(), name='calculate_price'),

    # Pet Training URLs
    path('training/', training.PetTrainingView.as_view(), name='pet_training'),
    path('training/success/<int:booking_id>/', training.TrainingSuccessView.as_view(), name='training_success'),
    path('training/check-availability/', training.CheckTrainingAvailabilityView.as_view(), name='check_training_availability'),

    # Customer Training Management URLs
    path('my-training-bookings/', training.MyTrainingBookingsView.as_view(), name='my_training_bookings'),
    path('my-training-bookings/<int:booking_id>/', training.TrainingDetailView.as_view(), name='training_detail'),

    # Admin Training Management URLs
    path('training/admin/', training.TrainingAdminView.as_view(), name='training_admin'),
    path('training/admin/update-status/<int:booking_id>/', training.UpdateTrainingStatusView.as_view(), name='update_training_status'),
    path('training/admin/progress/<int:booking_id>/', training.TrainingProgressUpdateView.as_view(), name='training_progress_update'),

    # My Bookings URLs
    path('my-bookings/', my_bookings.MyBookingsView.as_view(), name='my_bookings'),
    path('my-bookings/<int:booking_id>/', my_bookings.BookingDetailView.as_view(), name='booking_detail'),
    path('my-bookings/<int:booking_id>/cancel/', my_bookings.CancelBookingView.as_view(), name='cancel_booking'),

    # Pet Media Admin URLs
    path('media/admin/', pet_media_admin.MediaAdminDashboardView.as_view(), name='media_admin_dashboard'),
    path('media/upload/', pet_media_admin.MediaUploadView.as_view(), name='media_upload'),
    path('media/upload/<int:booking_id>/', pet_media_admin.MediaUploadView.as_view(), name='media_upload_booking'),
    path('media/manage/<int:booking_id>/', pet_media_admin.MediaManageView.as_view(), name='media_manage'),
    path('media/delete/<int:media_id>/', pet_media_admin.MediaDeleteView.as_view(), name='media_delete'),
    path('media/toggle/<int:media_id>/', pet_media_admin.MediaToggleVisibilityView.as_view(), name='media_toggle'),
    path('media/bulk-actions/', pet_media_admin.MediaBulkActionsView.as_view(), name='media_bulk_actions'),
    path('media/analytics/', pet_media_admin.MediaAnalyticsView.as_view(), name='media_analytics'),

    # Pet Media Customer URLs
    path('pet-updates/', pet_media_customer.PetUpdatesView.as_view(), name='pet_updates'),
    path('pet-updates/booking/<int:booking_id>/', pet_media_customer.BookingMediaView.as_view(), name='booking_media'),
    path('pet-updates/timeline/', pet_media_customer.MediaTimelineView.as_view(), name='media_timeline'),
    path('pet-updates/media/<int:media_id>/', pet_media_customer.MediaDetailView.as_view(), name='media_detail'),
    path('pet-updates/search/', pet_media_customer.MediaSearchView.as_view(), name='media_search'),

    # Admin URLs for boarding management
    path('boarding/admin/', boarding.BoardingAdminView.as_view(), name='boarding_admin'),
    path('boarding/admin/update-status/<int:booking_id>/', boarding.UpdateBookingStatusView.as_view(),
         name='update_booking_status'),
    path('boarding/admin/slots/', boarding.SlotManagementView.as_view(), name='slot_management'),
]