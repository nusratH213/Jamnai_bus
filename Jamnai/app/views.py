from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Route, RouteStopage, Trip, Schedule, Card, Ticket
from django.contrib.auth import get_user_model
import json
from django.views.decorators.csrf import csrf_exempt
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    # Radius of Earth in km
    R = 6371  

    # Convert degrees → radians
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  

def send_location_page(request):
    return render(request, "app/send.html")

@csrf_exempt
def location_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            latitude = data.get("latitude")
            longitude = data.get("longitude")
            print("Location received:", latitude, longitude)  # Log in terminal

            response = {
                "received_latitude": latitude,
                "received_longitude": longitude,
                "message": "Location received successfully!"
            }
            return JsonResponse(response)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "POST request required"}, status=405)

def cap(request):
    return render(request, "app/cap.html")


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
                return redirect('search')  # Redirect to some home page or dashboard
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

from django.utils import timezone
from datetime import datetime, time, timedelta
import pytz

def get_bangladesh_time():
    bd_timezone = pytz.timezone('Asia/Dhaka')
    utc_now = datetime.utcnow()
    utc_aware = pytz.utc.localize(utc_now)
    bd_time = utc_aware.astimezone(bd_timezone)
    return bd_time.replace(tzinfo=None)  # Return naive datetime in BD time

def get_bangladesh_datetime_naive():
    return get_bangladesh_time()

def search_routes(request):
    routes_with_path = []
    buses_info = []

    if request.method == "POST":
        source = request.POST.get("source", "").strip().lower()
        destination = request.POST.get("destination", "").strip().lower()
        
        # Get current time in Bangladesh timezone (naive)
        current_time_bd = get_bangladesh_time()
        print(f"Current time in Bangladesh: {current_time_bd}")
        
        for route in Route.objects.all():
            route_stopages = list(RouteStopage.objects.filter(route=route).order_by('order'))
            stopage_names = [rs.stopage.name.strip().lower() for rs in route_stopages]
            if source in stopage_names and destination in stopage_names:
                source_index = stopage_names.index(source)+1
                dest_index = stopage_names.index(destination)+1

                if source_index < dest_index:
                    # Valid route in correct direction
                    original_names = [rs.stopage.name for rs in route_stopages]
                    routes_with_path.append({
                        'route': route,
                        'stopages': original_names
                    })
                    # Ongoing trips
                    trips = Trip.objects.filter(route=route, is_ended=False)
                    for trip in trips:
                        schedules = Schedule.objects.filter(trip=trip).order_by('departure_time')
                        it=Schedule.objects.filter(trip=trip).order_by('departure_time').exclude(departure_time__isnull=True)
                        big=None
                        for i in it:
                            if(big is None or i.departure_time > big.departure_time):
                                big=i
                        print(f"Schedules for trip {trip.trip_id}: {schedules}")
                        last_schedule = None
                        for sched in schedules:
                            if (sched.departure_time and sched.departure_time < current_time_bd.time()) or not sched.departure_time:
                                last_schedule = sched
                            else:
                                break
                        # print(f"Last schedule for trip {trip.trip_id}: {last_schedule}")
                        # Prioritize current location (no departure time) over past schedules
                        current_location_schedule = schedules.filter(departure_time__isnull=True).last()
                        last_schedule = current_location_schedule if current_location_schedule else last_schedule
                        
                        if last_schedule:
                            try:
                                stop_order = RouteStopage.objects.get(route=route, stopage=last_schedule.stopage).order
                                print(f"Stop order for last schedule: {stop_order} and source index: {source_index}")
                                if stop_order <= source_index:
                                    # Initialize estimated_time
                                    estimated_time = "Unknown"
                                    
                                    # Calculate estimated time using distance
                                    if str(last_schedule.stopage.name).lower() == str(source).lower():
                                        # Bus is at the source station
                                        current_local_time = current_time_bd
                                        estimated_time = current_local_time.strftime("%H:%M")
                                        print(f"Bus at source - Current Bangladesh time: {current_local_time}, formatted: {estimated_time}")
                                    else:
                                        try:
                                            # Get cumulative distances
                                            current_stopage_route = RouteStopage.objects.get(route=route, stopage=last_schedule.stopage)
                                            source_stopage_route = RouteStopage.objects.get(route=route, stopage__name__iexact=source)
                                            
                                            # Calculate distance difference (source distance - current distance)
                                            distance_to_travel = source_stopage_route.distance_from_last_stopage - current_stopage_route.distance_from_last_stopage
                                            
                                            print(f"Distance calculation: current={current_stopage_route.distance_from_last_stopage}, source={source_stopage_route.distance_from_last_stopage}, to_travel={distance_to_travel}")
                                            
                                            if distance_to_travel <= 0:
                                                current_local_time = current_time_bd
                                                estimated_time = current_local_time.strftime("%H:%M")
                                                print(f"Distance <= 0 - Current user time: {current_local_time}, formatted: {estimated_time}")
                                            else:
                                                # Calculate time: 3 minutes per kilometer
                                                travel_time_minutes = distance_to_travel * 3
                                                
                                                if last_schedule.departure_time:
                                                    # Bus has departed, add travel time to departure time
                                                    departure_datetime = datetime.combine(current_time_bd.date(), last_schedule.departure_time)
                                                    estimated_arrival = departure_datetime + timedelta(minutes=travel_time_minutes)
                                                    estimated_time = estimated_arrival.strftime("%H:%M")
                                                    print(f"Departed bus - Departure: {departure_datetime}, Estimated arrival: {estimated_arrival}, formatted: {estimated_time}")
                                                elif current_location_schedule:
                                                    # Bus is currently at station, estimate from now
                                                    current_datetime = current_time_bd
                                                    estimated_arrival = current_datetime + timedelta(minutes=travel_time_minutes)
                                                    estimated_time = estimated_arrival.strftime("%H:%M")
                                                    print(f"At station - Current: {current_datetime}, Estimated arrival: {estimated_arrival}, formatted: {estimated_time}")
                                                elif not (route.start_stopage.departure_time):
                                                    estimated_time ="Not Started Yet"
                                                else:
                                                    # Fallback: just show travel time as minutes
                                                    estimated_time = f"{int(travel_time_minutes)} mins"
                                        except RouteStopage.DoesNotExist as e:
                                            print(f"RouteStopage not found: {e}")
                                            # Fallback if route stopage data is missing
                                            estimated_time = "Soon"
                                        except Exception as e:
                                            print(f"Error calculating estimated time: {e}")
                                            estimated_time = "Unknown"
                                    
                                    print(f"Final estimated_time for bus {trip.bus.id}: '{estimated_time}' (type: {type(estimated_time)})")
                                    
                                    buses_info.append({
                                        'bus_id': trip.bus.id,
                                        'last_stopage': last_schedule.stopage.name,
                                        'last_departure': big.departure_time.strftime("%H:%M") if big and big.departure_time else "Not Departed",
                                        'estimated_time': estimated_time if big else "Infinity", 
                                        'updated_at': current_time_bd,
                                        'seat_available':trip.available_seats,
                                        'total_seat':trip.total_seats,
                                    })
                                print(buses_info)
                                # print(f"Bus {trip.bus.id} last stopage: {last_schedule.stopage.name if last_schedule else 'N/A'}")
                            except RouteStopage.DoesNotExist:
                                continue

    return render(request, 'app/user_dashboard.html', {
        'routes_with_path': routes_with_path,
        'buses_info': buses_info
    })

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.utils import timezone
import json

@csrf_exempt
@require_POST
def f(request):
    if request.method != "POST":
        return HttpResponse(
            json.dumps({"error": "Invalid request method"}),
            content_type="application/json",
            status=405
        )
    print(json.loads(request.body))
    try:
        data = json.loads(request.body)
        print(data)
        bus_id = data.get("busid")
        on_flag = int(data.get("on"))
        card_id = data.get("card_id")
        print(card_id)
    except Exception as e:
        return HttpResponse(
            json.dumps({"error": f"Invalid JSON data: {str(e)}"}),
            content_type="application/json",
            status=400
        )

    # Always use Bangladesh timezone
    bd_timezone = pytz.timezone('Asia/Dhaka')

    print(f"Received request for bus {bus_id}, on_flag: {on_flag}, card_id: {card_id}")

    if on_flag not in [1, 0, '1', '0', "1", "0"]:
        return HttpResponse(
            json.dumps({"error": "'on' must be '1' or '0'"}),
            content_type="application/json",
            status=400
        )

    today = get_bangladesh_time().date()  # Use Bangladesh date (naive)
    try:
        trip = Trip.objects.get(bus=bus_id, is_ended=False)
    except Trip.DoesNotExist:
        return HttpResponse(
            json.dumps({"error": "No active trip for this bus today"}),
            content_type="application/json",
            status=404
        )

    last_sched = (
        Schedule.objects
        .filter(trip=trip)
        .order_by("-arrival_time")
        .first()
    )
    current_stopage = last_sched.stopage if last_sched else None
    print(f"Current stopage for trip {trip.trip_id}: {current_stopage}")

    if not current_stopage:
        return HttpResponse(
            json.dumps({"error": "No stopage data available for current trip"}),
            content_type="application/json",
            status=404
        )

    # Handle start of journey
    if on_flag in [1, '1', "1"]:
        try:
            card = Card.objects.get(card_id=card_id, availability=True)
        except Card.DoesNotExist:
            return HttpResponse(
                json.dumps({"error": "Invalid or unavailable card"}),
                content_type="application/json",
                status=404
            )

        # Get current time in Bangladesh timezone (naive)
        current_time_bd = get_bangladesh_time()

        ticket = Ticket.objects.create(
            trip=trip,
            card=card,
            start_stopage=current_stopage,
            end_stopage=None,
            price=0,
            in_ticket_time=current_time_bd,  # Set boarding time in Bangladesh timezone
            is_completed=False  # Journey just started
        )
        trip.available_seats -= 1
        trip.save(update_fields=["available_seats"])

        card.availability = False
        card.save(update_fields=["availability"])

        return HttpResponse(
            json.dumps({
                "status": "journey_start_recorded",
                "trip_id": trip.trip_id,
                "start_stopage": current_stopage.name,
                "ticket_id": ticket.pk
            }),
            content_type="application/json"
        )

    # Handle end of journey
    elif on_flag in [0, '0', "0"]:
        try:
            card = Card.objects.get(card_id=card_id, availability=False)
        except Card.DoesNotExist:
            return HttpResponse(
                json.dumps({"error": "Card not found or not currently in use"}),
                content_type="application/json",
                status=404
            )

        try:
            ticket = Ticket.objects.filter(
                card=card,
                trip=trip,
                end_stopage__isnull=True
            ).latest('id')
        except Ticket.DoesNotExist:
            return HttpResponse(
                json.dumps({"error": "No active ticket found for this card"}),
                content_type="application/json",
                status=404
            )
        
        # Get current time in Bangladesh timezone for alighting (naive)
        current_time_bd = get_bangladesh_time()
        
        ticket.end_stopage = current_stopage
        ticket.out_ticket_time = current_time_bd  # Set alighting time in Bangladesh timezone
        ticket.is_completed = True  # Mark journey as completed
        ticket.save(update_fields=["end_stopage", "out_ticket_time", "is_completed"])
        costs=RouteStopage.objects.get(route_id=trip.route,stopage=ticket.start_stopage).distance_from_last_stopage
        coste=RouteStopage.objects.get(route_id=trip.route,stopage=current_stopage).distance_from_last_stopage
        cost=coste-costs
        cost*=2.5
        ticket.price=cost
        card.taka-=cost
        card.availability = True
        ticket.save(update_fields=["price"])
        card.save(update_fields=["availability","taka"])
        trip.available_seats += 1
        trip.save(update_fields=["available_seats"])
        return HttpResponse(
            json.dumps({
                "status": "journey_end_recorded",
                "trip_id": trip.trip_id,
                "start_stopage": ticket.start_stopage.name if ticket.start_stopage else None,
                "end_stopage": current_stopage.name,
                "ticket_id": ticket.pk
            }),
            content_type="application/json"
        )

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
        print(f"Road: {rid} {mp[rid]} {latest}")
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

    # Use Bangladesh timezone for consistent time recording (naive)
    current_time_bd = get_bangladesh_time()

    ImgNow.objects.create(
        stopage=stopage,
        road=road,
        value=value,
        time=current_time_bd
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
    current_bd_time = get_bangladesh_time()  # Get Bangladesh time (naive)
    
    trip = Trip.objects.create(
        trip_id=f"TRIP-{uuid4().hex[:8]}",
        route=route,
        bus=bus,
        date=current_bd_time.date(),  # Use Bangladesh date
        is_ended=False,
        available_seats=50,
        total_seats=50,
        start_time=current_bd_time.time(),
    )

    # Get first stopage of the route
    first_route_stopage = RouteStopage.objects.filter(route=route).order_by('order').first()
    if not first_route_stopage:
        return Response({"error": "Route has no stopages defined."}, status=status.HTTP_400_BAD_REQUEST)

    # Use Bangladesh timezone for schedule creation (naive)
    current_time_bd = get_bangladesh_time()

    # Create Schedule for first stopage with only arrival time
    Schedule.objects.create(
        trip=trip,
        stopage=first_route_stopage.stopage,
        arrival_time=current_time_bd.time(),  # Use Bangladesh time
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
@login_required 
@api_view(['GET'])
def getstop(request):
    bus_id=request.user.id
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
    at = set(
        Schedule.objects.filter(trip=trip,departure_time__isnull=True).values_list('stopage__id', flat=True)
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
            "next_stopage": next_stopage.name,
            "stat": 1 if len(at) != 0 else 0

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

    # Always use Bangladesh timezone
    bd_timezone = pytz.timezone('Asia/Dhaka')

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

    # Get current time in Bangladesh timezone (naive)
    current_time_bd = get_bangladesh_time()
    now_time = current_time_bd.time()  # Extract time component
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
        # Auto-complete all incomplete tickets when bus reaches final destination
        incomplete_tickets = Ticket.objects.filter(
            trip=trip,
            is_completed=False
        )
        
        completed_count = 0
        for ticket in incomplete_tickets:
            # Set out_ticket_time to current time if not already set
            if not ticket.out_ticket_time:
                ticket.out_ticket_time = current_time_bd  # Use Bangladesh timezone
            # Mark ticket as completed
            ticket.is_completed = True
            ticket.card.availability = 1
            cost = RouteStopage.objects.get(route_id=trip.route,stopage=ticket.start_stopage).distance_from_last_stopage - RouteStopage.objects.get(route_id=trip.route,stopage=stopage).distance_from_last_stopage
            cost=abs(cost)
            ticket.price=cost*2.5
            print(f"Auto-completing ticket {ticket.id} with start stopage {ticket.start_stopage.name} end stopage {stopage.name} price {ticket.price}")
            ticket.card.taka-=ticket.price
            ticket.end_stopage = stopage
            ticket.card.save(update_fields=['availability', 'taka'])
            ticket.save(update_fields=['out_ticket_time', 'is_completed', 'price', 'end_stopage'])
            trip.available_seats+=1
            trip.save(update_fields=["available_seats"])
            completed_count += 1
        trip.start_time = trip.start_time or current_time_bd
        trip.end_time = current_time_bd
        trip.is_ended = True
        trip.save(update_fields=["is_ended", "start_time", "end_time"])

        if completed_count > 0:
            message += f" Trip ended. {completed_count} incomplete tickets auto-completed."
        else:
            message += " Trip ended."
    schedule.save()
    return Response({
        "message": message,
        "trip_id": trip.trip_id,
        "stopage": stopage.name,
        "time": str(now_time),
        "end": trip.is_ended,
    }, status=status.HTTP_200_OK)

@login_required
def ownerview(request):
    if request.user.role != 'Owner':
        return HttpResponse("You are not authorized to view this page.", status=403)

    owner_id = request.user.id
    print(f"Rendering owner dashboard for owner_id: {owner_id}")

    # Fetch all buses owned by this owner
    owned_buses = Owner.objects.filter(owner__id=owner_id).values_list('bus__id', flat=True)
    buses = User.objects.filter(id__in=owned_buses, role='bus')

    return render(request, "app/owner_dashboard.html", {
        "buses": buses,
        "owner_id": owner_id
    })
@login_required
def bus_dashboard(request):
    if request.user.role != 'Bus':
        return HttpResponse("You are not authorized to view this page.", status=403)

    bus_id = request.user.id
    print(f"Rendering bus dashboard for bus_id: {bus_id}")

    # Fetch the active trip for this bus
    try:
        trip = Trip.objects.get(bus__id=bus_id, is_ended=False)
    except Trip.DoesNotExist:
        trip = None

    return render(request, "app/bus_dashboard.html", {
        "trip": trip,
        "bus_id": bus_id
    })
from django.http import JsonResponse
from app.models import Stopage

def gets(request):
    dest = Stopage.objects.all().values_list('name', flat=True)
    return JsonResponse({"destinations": list(dest)})

@login_required
def api_tester(request):
    """API Testing/Debugging Dashboard"""
    if not request.user.is_staff and request.user.role not in ['Owner', 'Admin']:
        return HttpResponse("You are not authorized to view this page.", status=403)
    
    # Import models that might not be imported yet
    from app.models import User, Owner, Road, Stopage
    
    # Get all available data for dropdowns
    users = User.objects.all()
    buses = User.objects.filter(role='bus')
    owners = User.objects.filter(role='Owner')
    routes = Route.objects.all()
    stopages = Stopage.objects.all()
    roads = Road.objects.all()
    cards = Card.objects.all()
    trips = Trip.objects.filter(is_ended=False)
    context = {
        'users': users,
        'buses': buses,
        'owners': owners,
        'routes': routes,
        'stopages': stopages,
        'roads': roads,
        'cards': cards,
        'trips': trips,
    }
    return render(request, "app/api_tester.html", context)


