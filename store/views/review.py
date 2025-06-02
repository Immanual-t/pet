# File: store/views/review.py
# Fixed import path

from django.shortcuts import render
from django.views import View
from store.models import CustomerReview  # Correct import path

class ReviewView(View):
    def get(self, request):
        reviews = CustomerReview.objects.all()
        return render(request, 'reviews.html', {'reviews': reviews})