from .models import CustomerReview

def home(request):
    slider_images = SliderImage.objects.all()
    services = Service.objects.all()
    customers = CustomerReview.objects.all()
    return render(request, 'your_template.html', {
        'slider_images': slider_images,
        'services': services,
        'customers': customers,
    })
