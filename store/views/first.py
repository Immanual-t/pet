# File: store/views/first.py (Enhanced)

from django.shortcuts import render
from django.views import View
from django.urls import reverse
from store.models import SliderImage, CustomerReview
from store.models.boarding import PetBoardingBooking
from store.models.customer import Customer
from django.db.models import Count
from django.utils import timezone
import datetime


class First(View):
    def get(self, request):
        # Get slider images
        slider_images = SliderImage.objects.all().order_by('-uploaded_at')

        # Enhanced services with better descriptions and icons
        services = [
            {
                "name": "Pet Boarding",
                "image": "images/boarding.jpeg",
                "description": "Premium boarding facility with 24/7 care, spacious accommodations, and personalized attention for your beloved pets.",
                "href": "/boarding/",
                "features": ["24/7 Professional Care", "Spacious Accommodations", "Daily Updates", "Emergency Support"]
            },
            {
                "name": "Pet Training",
                "image": "images/training1.jpg",
                "description": "Expert trainers using positive reinforcement techniques to help your pet learn essential skills and good behavior.",
                "href": "#",
                "features": ["Positive Reinforcement", "Behavior Modification", "Obedience Training", "Socialization"]
            },
            {
                "name": "Pet Products",
                "image": "images/products1.jpg",
                "description": "Premium quality food, toys, accessories, and grooming supplies for all your pet's needs and happiness.",
                "href": reverse('homepage'),
                "features": ["Premium Food", "Interactive Toys", "Grooming Supplies", "Health Products"]
            },
            {
                "name": "Veterinary Care",
                "image": "images/vet1.jpg",
                "description": "Comprehensive veterinary services including health checkups, vaccinations, and emergency medical care.",
                "href": "#",
                "features": ["Health Checkups", "Vaccinations", "Emergency Care", "Dental Services"]
            }
        ]

        # Get customer reviews
        customers = CustomerReview.objects.all().order_by('-id')

        # Add some enhanced statistics for the homepage
        stats = self.get_homepage_stats()

        # Get recent activity (if user is logged in)
        recent_activity = None
        customer_info = None
        if request.session.get('customer'):
            try:
                customer = Customer.objects.get(id=request.session.get('customer'))
                customer_info = {
                    'name': f"{customer.first_name} {customer.last_name}",
                    'email': customer.email
                }
                recent_activity = self.get_customer_recent_activity(customer.email)
            except Customer.DoesNotExist:
                pass

        context = {
            'slider_images': slider_images,
            'services': services,
            'customers': customers,
            'stats': stats,
            'customer_info': customer_info,
            'recent_activity': recent_activity,
            'current_year': timezone.now().year,
        }

        return render(request, 'home.html', context)

    def get_homepage_stats(self):
        """Get statistics to display on homepage"""
        try:
            total_bookings = PetBoardingBooking.objects.count()
            happy_customers = Customer.objects.count()
            completed_bookings = PetBoardingBooking.objects.filter(status='completed').count()
            active_bookings = PetBoardingBooking.objects.filter(status='approved').count()

            # Calculate customer satisfaction (based on reviews with rating >= 4)
            positive_reviews = CustomerReview.objects.filter(rating__gte=4).count()
            total_reviews = CustomerReview.objects.count()
            satisfaction_rate = (positive_reviews / total_reviews * 100) if total_reviews > 0 else 100

            return {
                'total_bookings': total_bookings,
                'happy_customers': happy_customers,
                'completed_services': completed_bookings,
                'active_bookings': active_bookings,
                'satisfaction_rate': round(satisfaction_rate, 1),
                'years_experience': timezone.now().year - 2020,  # Assuming started in 2020
            }
        except Exception as e:
            # Return default stats if database query fails
            return {
                'total_bookings': 0,
                'happy_customers': 0,
                'completed_services': 0,
                'active_bookings': 0,
                'satisfaction_rate': 100.0,
                'years_experience': 5,
            }

    def get_customer_recent_activity(self, customer_email):
        """Get recent activity for logged-in customer"""
        try:
            # Get recent bookings
            recent_bookings = PetBoardingBooking.objects.filter(
                owner_email=customer_email
            ).order_by('-created_at')[:3]

            # Get upcoming bookings
            today = timezone.now().date()
            upcoming_bookings = PetBoardingBooking.objects.filter(
                owner_email=customer_email,
                status='approved',
                start_date__gte=today
            ).order_by('start_date')[:2]

            return {
                'recent_bookings': recent_bookings,
                'upcoming_bookings': upcoming_bookings,
                'total_bookings': PetBoardingBooking.objects.filter(owner_email=customer_email).count()
            }
        except Exception:
            return None