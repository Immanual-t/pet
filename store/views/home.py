# File: store/views/home.py

from django.shortcuts import render, redirect
from django.db import models
from store.models.product import Product
from store.models.category import Category
from django.views import View


class Index(View):
    def get(self, request):
        cart = request.session.get('cart')
        if not cart:
            request.session['cart'] = {}

        products = None
        categories = Category.get_all_categories()
        categoryID = request.GET.get('category')
        selected_category = None

        # Handle category filtering
        if categoryID:
            try:
                categoryID = int(categoryID)
                products = Product.get_all_products_by_categoryid(categoryID)
                # Get the selected category object
                selected_category = Category.objects.get(id=categoryID)
            except (ValueError, Category.DoesNotExist):
                products = Product.get_all_products()
                selected_category = None
        else:
            products = Product.get_all_products()

        # Handle search functionality
        search_query = request.GET.get('search', '').strip()
        if search_query:
            products = products.filter(
                models.Q(name__icontains=search_query) |
                models.Q(description__icontains=search_query)
            )

        # Handle sorting
        sort_by = request.GET.get('sort', 'featured')
        if sort_by == 'price-low':
            products = products.order_by('price')
        elif sort_by == 'price-high':
            products = products.order_by('-price')
        elif sort_by == 'name':
            products = products.order_by('name')
        else:  # featured or default
            products = products.order_by('-id')  # Newest first as default

        # Handle price filtering
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')

        if min_price:
            try:
                min_price = float(min_price)
                products = products.filter(price__gte=min_price)
            except ValueError:
                pass

        if max_price:
            try:
                max_price = float(max_price)
                products = products.filter(price__lte=max_price)
            except ValueError:
                pass

        # Get product statistics
        total_products = Product.objects.count()
        products_in_category = products.count() if products else 0

        data = {
            'products': products,
            'categories': categories,
            'selected_category': selected_category,
            'search_query': search_query,
            'sort_by': sort_by,
            'min_price': request.GET.get('min_price', ''),
            'max_price': request.GET.get('max_price', ''),
            'total_products': total_products,
            'products_in_category': products_in_category,
        }

        print('you are : ', request.session.get('email'))
        return render(request, 'index.html', data)

    def post(self, request):
        product = request.POST.get('product')
        remove = request.POST.get('remove')
        cart = request.session.get('cart')

        if cart:
            quantity = cart.get(product)
            if quantity:
                if remove:
                    if quantity <= 1:
                        cart.pop(product)
                    else:
                        cart[product] = quantity - 1
                else:
                    cart[product] = quantity + 1
            else:
                cart[product] = 1
        else:
            cart = {}
            cart[product] = 1

        request.session['cart'] = cart
        print('cart :', request.session['cart'])

        # Return to the same page with filters preserved
        redirect_url = request.META.get('HTTP_REFERER', '/')
        return redirect(redirect_url)