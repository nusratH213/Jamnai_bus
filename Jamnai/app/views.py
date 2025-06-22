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

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.http import JsonResponse
from .models import Trip, Schedule, Card, Ticket

@csrf_exempt
@require_POST
def f(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    bus_id = request.POST.get("busid")
    on_flag = request.POST.get("on")
    card_id = request.POST.get("card_id")

    if on_flag not in ["1", "0"]:
        return JsonResponse({"error": "'on' must be '1' or '0'"}, status=400)

    # Find today's active trip for this bus
    today = timezone.localdate()
    try:
        trip = Trip.objects.get(bus=bus_id, date=today, is_ended=False)
    except Trip.DoesNotExist:
        return JsonResponse({"error": "No active trip for this bus today"}, status=404)

    # Determine current stopage = last arrival on this trip
    last_sched = (
        Schedule.objects
        .filter(trip=trip)
        .order_by("-arrival_time")
        .first()
    )
    current_stopage = last_sched.stopage if last_sched else None

    if not current_stopage:
        return JsonResponse({"error": "No stopage data available for current trip"}, status=404)

    # Handle start of journey
    if on_flag == "1":
        try:
            card = Card.objects.get(card_id=card_id, availability=True)
        except Card.DoesNotExist:
            return JsonResponse({"error": "Invalid or unavailable card"}, status=404)

        # Create ticket with start_stopage
        ticket = Ticket.objects.create(
            trip=trip,
            card=card,
            start_stopage=current_stopage,
            end_stopage=None,
            price=0
        )
        trip.available_seats -= 1
        trip.save(update_fields=["available_seats"])
        # Mark card unavailable
        card.availability = False
        card.save(update_fields=["availability"])
        return JsonResponse({
            "status": "journey_start_recorded",
            "trip_id": trip.trip_id,
            "start_stopage": current_stopage.name,
            "ticket_id": ticket.pk
        })

    # Handle end of journey
    elif on_flag == "0":
        try:
            card = Card.objects.get(card_id=card_id, availability=False)
        except Card.DoesNotExist:
            return JsonResponse({"error": "Card not found or not currently in use"}, status=404)

        try:
            ticket = Ticket.objects.filter(card=card, trip=trip, end_stopage__isnull=True).latest('id')
        except Ticket.DoesNotExist:
            return JsonResponse({"error": "No active ticket found for this card"}, status=404)

        # Update ticket with end stopage and price (if needed)
        ticket.end_stopage = current_stopage
        ticket.save(update_fields=["end_stopage"])

        # Mark card available again
        card.availability = True
        card.save(update_fields=["availability"])
        trip.available_seats += 1
        trip.save(update_fields=["available_seats"])    
        return JsonResponse({
            "status": "journey_end_recorded",
            "trip_id": trip.trip_id,
            "start_stopage": ticket.start_stopage.name if ticket.start_stopage else None,
            "end_stopage": current_stopage.name,
            "ticket_id": ticket.pk
        })
    
from django.http import JsonResponse
from app.models import Road, Stopage, ImgNow 

def g(request):
    road_ids = request.GET.getlist('roadid[]')  # Get list of road IDs
    stopage_id = request.GET.get('stopageid')

    if not road_ids or not stopage_id:
        return JsonResponse({"error": "Missing roadid[] or stopageid"}, status=400)

    try:
        stopage = Stopage.objects.get(pk=stopage_id)
    except Stopage.DoesNotExist:
        return JsonResponse({"error": "Stopage not found"}, status=404)

    data = []

    for rid in road_ids:
        try:
            road = Road.objects.get(pk=rid)
        except Road.DoesNotExist:
            data.append(None)  # Or skip, depending on your choice
            continue

        # Get latest ImgNow for this road and stopage
        latest = ImgNow.objects.filter(road=road, stopage=stopage).order_by('-time').first()

        data.append(latest.value if latest else None)

    return JsonResponse({
        "stopage_id": stopage_id,
        "road_ids": road_ids,
        "data": data  # List of latest values per road
    })

from .models import ImgNow, Road, Stopage
from django.utils.timezone import now
@csrf_exempt
def setg_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    stopage_id = request.POST.get("stopageid")
    road_id = request.POST.get("roadid")
    val = request.POST.get("val")

    if not (stopage_id and road_id and val):
        return JsonResponse({"error": "Missing parameters"}, status=400)
    try:
        stopage = Stopage.objects.get(pk=stopage_id)
        road = Road.objects.get(pk=road_id)
        value = int(val)
    except Stopage.DoesNotExist:
        return JsonResponse({"error": "Stopage not found"}, status=404)
    except Road.DoesNotExist:
        return JsonResponse({"error": "Road not found"}, status=404)
    except ValueError:
        return JsonResponse({"error": "Invalid value"}, status=400)

    ImgNow.objects.create(
        stopage=stopage,
        road=road,
        value=value,
        time=now()
    )

    return JsonResponse({
        "status": "value inserted",
        "stopage": stopage.name,
        "road": road.name,
        "value": value
    })

