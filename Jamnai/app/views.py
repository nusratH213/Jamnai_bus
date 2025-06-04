from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from django.shortcuts import render

def hello_view(request):
    return render(request, "app/user_dashboard.html")

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

def user_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # print(f"User {username} logged in successfully.")
                # messages.success(request, f"Welcome, {username}!")
                return redirect('home')  # Redirect to some home page or dashboard
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
        print("GET request received for login")
    return render(request, "app/login.html", {"form": form})

from django.contrib.auth import logout

def user_logout(request):
    logout(request)
    return redirect('login')
