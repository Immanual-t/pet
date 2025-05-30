# File: store/middlewares/auth.py (Alternative improved version)

from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


def auth_middleware(get_response):
    """Original middleware for function-based views"""

    def middleware(request):
        print(request.user)
        return_url = request.META['PATH_INFO']
        if request.session.get('customer'):
            return get_response(request)
        else:
            return redirect(f'/login?return_url={return_url}')

    return middleware


def customer_required(view_func):
    """Decorator for function-based views that require customer authentication"""

    def wrapped_view(request, *args, **kwargs):
        if request.session.get('customer'):
            return view_func(request, *args, **kwargs)
        else:
            return_url = request.META['PATH_INFO']
            return redirect(f'/login?return_url={return_url}')

    return wrapped_view


class CustomerRequiredMixin:
    """Mixin for class-based views that require customer authentication"""

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('customer'):
            return_url = request.META['PATH_INFO']
            return redirect(f'/login?return_url={return_url}')
        return super().dispatch(request, *args, **kwargs)


# Decorator for class-based views
def customer_login_required(view_class):
    """
    Decorator for class-based views that require customer authentication.
    Works with URL parameters unlike the middleware.
    """

    class WrappedView(CustomerRequiredMixin, view_class):
        pass

    return WrappedView