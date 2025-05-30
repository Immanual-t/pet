from .models import SliderImage

def home(request):
    slider_images = SliderImage.objects.all()

    context = {
        'slider_images': slider_images,
        # ... other context data
    }
    return render(request, 'home.html', context)
