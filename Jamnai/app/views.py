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

from datetime import datetime, timedelta
from django.utils import timezone
from app.models import Route, RouteStopage, Trip, Schedule, Stopage


def search_routes(request):
    routes_with_path = []
    buses_info = []

    if request.method == "POST":
        source = request.POST.get("source").strip().lower()
        destination = request.POST.get("destination").strip().lower()
        print(f"Searching routes from {source} to {destination}")

        current_time = timezone.localtime().time()
        for route in Route.objects.all():
            route_stopages = RouteStopage.objects.filter(route=route).order_by('order')
            stopage_names = [rs.stopage.name for rs in route_stopages]
            stopage_names = [name.strip().lower() for name in stopage_names]

            # print(f"Checking route {route.route_id} with stopages: {stopage_names}")

            if source in stopage_names and destination in stopage_names:
                source_index = stopage_names.index(source)
                dest_index = stopage_names.index(destination)

                if source_index < dest_index:
                    # Valid route with ordered source → destination
                    original_names = [rs.stopage.name for rs in route_stopages]
                    routes_with_path.append({
                        'route': route,
                        'stopages': original_names
                    })
                    # print(f"Found valid route {route.route_id} from {source} to {destination}")

                    # Fetch all ongoing trips for this route
                    trips = Trip.objects.filter(route=route, is_ended=False)

                    for trip in trips:
                        schedules = Schedule.objects.filter(trip=trip).order_by('departure_time')

                        last_schedule = None
                        for sched in schedules:
                            if sched.departure_time < current_time:
                                last_schedule = sched
                            else:
                                break

                        if last_schedule:
                            try:
                                stop_order = route_stopages.get(stopage=last_schedule.stopage).order
                                if stop_order < source_index:
                                    buses_info.append({
                                        'bus_id': trip.bus.id,
                                        'last_stopage': last_schedule.stopage.name,
                                        'last_departure': last_schedule.departure_time,
                                        'estimated': (datetime.combine(datetime.today(), last_schedule.departure_time) + timedelta(minutes=30)).time(),
                                        'updated_at': timezone.now()
                                    })
                            except RouteStopage.DoesNotExist:
                                continue
    # print(f"Found {len(routes_with_path)} routes with path from {source} to {destination}")
    # print(f"Found {len(buses_info)} buses with info for the given routes")
    return render(request, 'app/user_dashboard.html', {
        'routes_with_path': routes_with_path,
        'buses_info': buses_info
    })
