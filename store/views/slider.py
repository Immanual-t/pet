# File: store/views/slider.py
# Fixed import path

from django.shortcuts import render
from django.views import View
from store.models import SliderImage  # Correct import path

class SliderView(View):
    def get(self, request):
        sliders = SliderImage.objects.filter(uploaded_at__isnull=False)
        return render(request, 'sliders.html', {'sliders': sliders})