from django.shortcuts import render
from django.views import View
from django.urls import reverse
from store.models import SliderImage, CustomerReview

class First(View):
    def get(self, request):
        slider_images = SliderImage.objects.all()
        services = [
            {
                "name": "Pet Boarding",
                "image": "images/boarding.jpeg",
                "description": "Safe and comfy space while you're away.",
                "href": "#"
            },
            {
                "name": "Pet Training",
                "image": "images/training1.jpg",
                "description": "Professional trainers to help your pet.",
                "href": "#"
            },
            {
                "name": "Pet Products",
                "image": "images/products1.jpg",
                "description": "Food, toys, grooming kits, and more.",
                "href": reverse('homepage')
            },
            {
                "name": "Veterinary Care",
                "image": "images/vet1.jpg",
                "description": "Expert vet consultation and emergency care.",
                "href": "#"
            }
        ]
        customers = CustomerReview.objects.all()  # ✅ Dynamic content from DB
        return render(request, 'home.html', {
            'slider_images': slider_images,
            'services': services,
            'customers': customers
        })
