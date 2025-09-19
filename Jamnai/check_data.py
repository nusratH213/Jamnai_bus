#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Jamnai.settings')
django.setup()

from app.models import Route, User, Trip, Ticket, Stopage

print("=== Database Data Check ===")

print(f"\nRoutes: {Route.objects.count()}")
for route in Route.objects.all()[:5]:
    print(f"  - Route {route.route_id}: {route.start_stopage.name} → {route.end_stopage.name}")

print(f"\nBus Users: {User.objects.filter(role='bus').count()}")
for bus in User.objects.filter(role='bus')[:5]:
    print(f"  - Bus {bus.id}: {getattr(bus, 'username', 'No username')} (role: {bus.role})")

print(f"\nTrips: {Trip.objects.count()}")
for trip in Trip.objects.all()[:5]:
    print(f"  - Trip {trip.id}: {trip.route.route_id if trip.route else 'No route'} on {trip.date}")

print(f"\nTickets: {Ticket.objects.count()}")
for ticket in Ticket.objects.all()[:5]:
    print(f"  - Ticket {ticket.id}: ${ticket.price} from {ticket.start_stopage.name if ticket.start_stopage else 'Unknown'} to {ticket.end_stopage.name if ticket.end_stopage else 'Unknown'}")

print(f"\nStopages: {Stopage.objects.count()}")
for stopage in Stopage.objects.all()[:5]:
    print(f"  - Stopage {stopage.id}: {stopage.name}")

print("\n=== Testing Analytics Query ===")
from app.analytics_views import get_total_analytics

# First check Trip model fields
print("\n=== Trip Model Debug ===")
from app.models import Trip
if Trip.objects.exists():
    sample_trip = Trip.objects.first()
    print(f"Sample trip fields:")
    for field in sample_trip._meta.fields:
        field_name = field.name
        field_value = getattr(sample_trip, field_name, 'N/A')
        print(f"  {field_name}: {field_value}")

try:
    analytics_data = get_total_analytics(None, None)  # Get all time data
    print(f"\nTotal trips in analytics: {analytics_data.get('summary', {}).get('total_trips', 0)}")
    print(f"Total revenue in analytics: ${analytics_data.get('summary', {}).get('total_revenue', 0)}")
    print(f"Total tickets in analytics: {analytics_data.get('summary', {}).get('total_tickets', 0)}")
    
    print(f"\nRoute data entries: {len(analytics_data.get('route_performance', []))}")
    print(f"Bus data entries: {len(analytics_data.get('bus_performance', []))}")
    
    # Show first few route data entries
    route_data = analytics_data.get('route_performance', [])
    if route_data:
        print(f"\nFirst route data entry: {route_data[0]}")
    else:
        print("\nNo route data found. Let's debug...")
        # Test manual route filtering
        from app.models import Route, Trip, Ticket
        test_route = Route.objects.first()
        print(f"Testing with route: {test_route.route_id}")
        
        test_trips = Trip.objects.filter(route=test_route)
        print(f"Trips for this route: {test_trips.count()}")
        
        test_tickets = Ticket.objects.filter(trip__route=test_route)
        print(f"Tickets for this route: {test_tickets.count()}")
        
        if test_trips.exists():
            print(f"Sample trip: {test_trips.first()}")
        if test_tickets.exists():
            print(f"Sample ticket: {test_tickets.first()}")
    
except Exception as e:
    print(f"Error in analytics: {e}")
    import traceback
    traceback.print_exc()