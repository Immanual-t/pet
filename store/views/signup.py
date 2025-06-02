# File: store/views/signup.py

from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password
from store.models.customer import Customer
from django.views import View
from django.http import HttpResponseRedirect


class Signup(View):
    def get(self, request):
        return_url = request.GET.get('return_url', '')
        return render(request, 'signup.html', {'return_url': return_url})

    def post(self, request):
        postData = request.POST
        first_name = postData.get('firstname')
        last_name = postData.get('lastname')
        phone = postData.get('phone')
        email = postData.get('email')
        password = postData.get('password')
        return_url = postData.get('return_url', '')

        # validation
        value = {
            'first_name': first_name,
            'last_name': last_name,
            'phone': phone,
            'email': email
        }

        customer = Customer(first_name=first_name,
                            last_name=last_name,
                            phone=phone,
                            email=email,
                            password=password)
        error_messege = self.validateCustomer(customer)

        if not error_messege:
            customer.password = make_password(customer.password)
            customer.register()

            # Log the user in automatically after signup
            request.session['customer'] = customer.id

            # Redirect to return URL if provided, otherwise to homepage
            if return_url:
                return HttpResponseRedirect(return_url)
            else:
                return redirect('homepage')
        else:
            data = {
                'error': error_messege,
                'values': value,
                'return_url': return_url
            }
            return render(request, 'signup.html', data)

    def validateCustomer(self, customer):
        error_messege = None
        if (not customer.first_name):
            error_messege = "First Name Required!!"
        elif len(customer.first_name) < 4:
            error_messege = "First Name must be 4 char long or more"
        elif not customer.last_name:
            error_messege = "Last Name required"
        elif len(customer.last_name) < 4:
            error_messege = "Last Name must be 4 char long or more"
        elif not customer.phone:
            error_messege = "Phone Number required"
        elif len(customer.phone) < 10:
            error_messege = "Phone Number must be 10 char long"
        elif len(customer.phone) < 6:
            error_messege = "Phone Number must be 6 char long"
        elif len(customer.email) < 5:
            error_messege = "Email must be 5 char long"
        elif customer.isExists():
            error_messege = 'Email address already registered..'

        return error_messege