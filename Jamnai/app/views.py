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
    print(f"Received request for bus {bus_id}, on_flag: {on_flag}, card_id: {card_id}")

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
mp={'1': "left", '2': "right", '3': "top"}
def g(request):
    road_ids = request.GET.getlist('roadid[]')  # Get list of road IDs
    stopage_id = request.GET.get('stopageid')

    if not road_ids or not stopage_id:
        return JsonResponse({"error": "Missing roadid[] or stopageid"}, status=400)
    try:
        stopage = Stopage.objects.get(pk=stopage_id)
    except Stopage.DoesNotExist:
        return JsonResponse({"error": "Stopage not found"}, status=404)
    data = {}

    for rid in road_ids:
        try:
            road = Road.objects.get(pk=rid)
        except Road.DoesNotExist:
            data[mp[rid]] = 0
            continue

        # Get latest ImgNow for this road and stopage
        latest = ImgNow.objects.filter(road=road, stopage=stopage).order_by('-time').first()
        data[mp[rid]] =latest.value if latest else 0  # Get the value or None if no record found

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




from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from app.models import User, Owner, Trip



@api_view(['GET'])
def get_buses(request):
    owner_id = request.query_params.get('owner_id')
    print(f"Received request to get buses for owner_id: {owner_id}")

    if not owner_id:
        return Response({"error": "Missing owner_id parameter"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        owner = User.objects.get(id=owner_id, role='Owner')
    except User.DoesNotExist:
        return Response({"error": "Owner not found or invalid role"}, status=status.HTTP_404_NOT_FOUND)
    # Step 1: Get all buses owned by this owner
    owned_bus_ids = Owner.objects.filter(owner=owner).values_list('bus__id', flat=True)

    # Step 2: Get buses in ongoing trips (not ended)
    active_bus_ids = Trip.objects.filter(is_ended=False).values_list('bus__id', flat=True)

    # Step 3: Exclude active buses from owned buses
    available_buses = User.objects.filter(id__in=owned_bus_ids).exclude(id__in=active_bus_ids)
    # Step 4: Serialize the result
    buses_data = [{"id": bus.id} for bus in available_buses]  # You can extend this with other fields
    routes=Route.objects.all().values('route_id', 'start_stopage__name', 'end_stopage__name')
    data={
        "buses": buses_data,
        "routes": list(routes)
    }
    return Response(data, status=status.HTTP_200_OK)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from app.models import Trip, Owner, RouteStopage, Schedule, Route

@api_view(['POST'])
# @permission_classes([IsAuthenticated])  # Use IsAdminUser if you have that set up
def setbus(request):

    data = request.data
    print(f"Received request to set bus with data: {data}")
    admin_user =User.objects.get(id=data["owner_id"], role='Owner')  # Assuming you have a way to get the admin user

    # Only admin users allowed
    if admin_user.role != 'Owner':
        return Response({"error": "Only admins can perform this action."}, status=status.HTTP_403_FORBIDDEN)

    bus_id = data.get('bus_id')
    route_id = data.get('route_id')
    owner_id = data.get('owner_id')
    print(f"Bus ID: {bus_id}, Route ID: {route_id}, Owner ID: {owner_id}")

    # Basic validation
    if not all([bus_id, route_id, owner_id]):
        return Response({"error": "bus_id, route_id, and owner_id are required."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check bus exists and has role 'bus'
    try:
        bus = User.objects.get(id=bus_id, role='bus')
    except User.DoesNotExist:
        return Response({"error": "Bus not found or invalid role."}, status=status.HTTP_404_NOT_FOUND)

    # Check owner exists and has role 'owner'
    try:
        owner = User.objects.get(id=owner_id, role='owner')
    except User.DoesNotExist:
        return Response({"error": "Owner not found or invalid role."}, status=status.HTTP_404_NOT_FOUND)

    # Check if the bus is actually owned by the owner
    if not Owner.objects.filter(bus=bus, owner=owner).exists():
        return Response({"error": "This bus does not belong to the specified owner."}, status=status.HTTP_403_FORBIDDEN)

    # Get the route
    try:
        route = Route.objects.get(route_id=route_id)
    except Route.DoesNotExist:
        return Response({"error": "Route not found."}, status=status.HTTP_404_NOT_FOUND)

    # Create new Trip
    from uuid import uuid4
    trip = Trip.objects.create(
        trip_id=f"TRIP-{uuid4().hex[:8]}",
        route=route,
        bus=bus,
        date=timezone.now().date(),
        is_ended=False,
        available_seats=50,
        total_seats=50,
        start_time=None
    )

    # Get first stopage of the route
    first_route_stopage = RouteStopage.objects.filter(route=route).order_by('order').first()
    if not first_route_stopage:
        return Response({"error": "Route has no stopages defined."}, status=status.HTTP_400_BAD_REQUEST)

    # Create Schedule for first stopage with only arrival time
    Schedule.objects.create(
        trip=trip,
        stopage=first_route_stopage.stopage,
        arrival_time=timezone.now().time(),  # Use current time
    )

        # departure_time=timezone.now().time()  # Optional: can leave as same or None

    return Response({
        "message": "Trip and initial schedule created successfully.",
        "trip_id": trip.trip_id,
        "bus_id": bus_id,
        "route_id": route_id,
        "stopage": first_route_stopage.stopage.name
    }, status=status.HTTP_201_CREATED)


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from app.models import Trip, RouteStopage, Schedule

@api_view(['GET'])
def getstop(request):
    bus_id = request.query_params.get('bus_id')
    print(f"Received request to get next stopage for bus_id: {bus_id}")

    if not bus_id:
        return Response({"error": "Missing bus_id"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        bus = User.objects.get(id=bus_id, role='Bus')
    except User.DoesNotExist:
        return Response({"error": "Invalid bus_id or not a bus role"}, status=status.HTTP_404_NOT_FOUND)

    # Find active trip
    try:
        trip = Trip.objects.get(bus_id=bus, is_ended=0)
    except Trip.DoesNotExist:
        return Response({"message": "Wait until owner starts the trip."}, status=status.HTTP_200_OK)

    route = trip.route
    # All stopages in the route in order
    route_stopages = list(RouteStopage.objects.filter(route=route).order_by('order'))

    # All stopages that have been departed from (departure_time set in schedule)
    departed_stopage_ids = set(
        Schedule.objects.filter(trip=trip).exclude(departure_time__isnull=True).values_list('stopage__id', flat=True)
    )

    # Find index of last departed stopage in the route
    last_index = -1
    for i, rs in enumerate(route_stopages):
        if rs.stopage.id in departed_stopage_ids:
            last_index = i

    # Determine next stopage
    next_index = last_index + 1
    if next_index < len(route_stopages):
        next_stopage = route_stopages[next_index].stopage
        return Response({
            "next_stopage": next_stopage.name
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            "message": "Trip completed or no further stopages."
        }, status=status.HTTP_200_OK)
    



from rest_framework.response import Response
from rest_framework import status
from app.models import Trip, Schedule, Stopage


@api_view(['POST'])
def updatestop(request):
    data = request.data
    bus_id = data.get('bus_id')
    stopage_id = data.get('stopage_id')
    arrive_flag = data.get('arrive')
    print(f"Received request to update stopage for bus_id: {bus_id}, stopage_id: {stopage_id}, arrive_flag: {arrive_flag}")

    # Validate input
    if not all([bus_id, stopage_id]) or arrive_flag not in [0, 1, '0', '1']:
        return Response({"error": "bus_id, stopage_id, and arrive (0 or 1) are required."}, status=status.HTTP_400_BAD_REQUEST)

    # Convert to integer
    arrive_flag = int(arrive_flag)

    # Validate bus
    try:
        bus = User.objects.get(id=bus_id, role='bus')
    except User.DoesNotExist:
        return Response({"error": "Invalid bus_id or user is not a bus."}, status=status.HTTP_404_NOT_FOUND)

    # Validate stopage
    try:
        stopage = Stopage.objects.get(name=stopage_id)
    except Stopage.DoesNotExist:
        return Response({"error": "Stopage not found."}, status=status.HTTP_404_NOT_FOUND)

    # Get active trip
    try:
        trip = Trip.objects.get(bus=bus, is_ended=False)
    except Trip.DoesNotExist:
        return Response({"error": "No active trip for this bus."}, status=status.HTTP_404_NOT_FOUND)


    now_time = timezone.now().time()
    if arrive_flag == 1:
        try:
            schedule = Schedule.objects.get(trip=trip, stopage=stopage)
            return Response({"error": "Schedule for this stopage already exists in this trip."}, status=status.HTTP_400_BAD_REQUEST)
        except Schedule.DoesNotExist:
            schedule=Schedule.objects.create(
                trip=trip,
                stopage=stopage,
                arrival_time=now_time,
                departure_time=None 
            )
            message = "Arrival time updated."

    else:
        try:
            schedule = Schedule.objects.get(trip=trip, stopage=stopage)
        except Schedule.DoesNotExist:
            return Response({"error": "Schedule for this stopage not found in this trip."}, status=status.HTTP_404_NOT_FOUND)
        schedule.departure_time = now_time
        message = "Departure time updated."
    routes= Route.objects.get(route_id=trip.route.route_id)
    if str(stopage.name) == str(routes.end_stopage.name):
        trip.is_ended = True
        trip.save(update_fields=["is_ended"])
        message += " Trip ended."
    schedule.save()
    return Response({
        "message": message,
        "trip_id": trip.trip_id,
        "stopage": stopage.name,
        "time": str(now_time),
        "end": trip.is_ended,
    }, status=status.HTTP_200_OK)
