from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from app.models import Trip, Ticket, Schedule, Route, Card, ImgNow, User, Owner, Stopage, RouteStopage
import json
from collections import defaultdict
import pytz
# Import enhanced analytics functions
from app.enhanced_analytics import (
    get_hourly_analytics_with_time_tracking,
    get_daily_analytics_with_time_tracking,
    get_weekly_analytics_with_time_tracking,
    get_route_time_analytics,
    get_journey_duration_analytics
)

def get_bangladesh_time():
    """Helper function to get current time in Bangladesh timezone as naive datetime"""
    bd_timezone = pytz.timezone('Asia/Dhaka')
    utc_now = datetime.utcnow()
    utc_aware = pytz.utc.localize(utc_now)
    bd_time = utc_aware.astimezone(bd_timezone)
    return bd_time.replace(tzinfo=None)  # Return naive datetime in BD time
def analytics_dashboard(request):
    """Main analytics dashboard view"""
    return render(request, 'app/analytics.html')

def enhanced_analytics_dashboard(request):
    """Enhanced analytics dashboard with time tracking"""
    return render(request, 'enhanced_analytics_dashboard.html')

def analytics_api(request):
    """API endpoint for analytics data"""
    filter_type = request.GET.get('filter', 'total')  # total, route, bus, day, week, month
    filter_value = request.GET.get('value', '')
    time_period = request.GET.get('period', 'all')  # all, today, week, month, year
    start_time_str = request.GET.get('start_time', '')  # Format: HH:MM
    end_time_str = request.GET.get('end_time', '')    # Format: HH:MM
    hourly_analysis = request.GET.get('hourly_analysis', 'false').lower() == 'true'
    print(f"Analytics API called with:")
    print(f"  filter_type: {filter_type}")
    print(f"  filter_value: {filter_value}")
    print(f"  time_period: {time_period}")
    print(f"  start_time: {start_time_str}")
    print(f"  end_time: {end_time_str}")
    print(f"  hourly_analysis: {hourly_analysis}")
    # Parse time intervals if provided
    start_time = None
    end_time = None
    if start_time_str and end_time_str:
        try:
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
            print(f"  Parsed times: {start_time} - {end_time}")
        except ValueError:
            return JsonResponse({'error': 'Invalid time format. Use HH:MM'}, status=400)
    
    # Get date range based on time period (using Bangladesh time)
    end_date = get_bangladesh_time().date()
    if time_period == 'today':
        start_date = end_date
    elif time_period == 'week':
        start_date = end_date - timedelta(days=7)
    elif time_period == 'month':
        start_date = end_date - timedelta(days=30)
    elif time_period == 'year':
        start_date = end_date - timedelta(days=365)
    else:
        start_date = None
        
    print(f"  Date raenge: {start_date} to {end_date}")
    
    data = {}
    try:
        if hourly_analysis and time_period == 'today':
            print("Processing hourly analysis request...")
            if filter_type == 'total':
                data = get_hourly_total_analytics(start_date, None, None)  # Use full day
            elif filter_type == 'route':
                data = get_hourly_route_analytics(filter_value, start_date, None, None)
            elif filter_type == 'bus':
                data = get_hourly_bus_analytics(filter_value, start_date, None, None)
            else:
                data = get_hourly_total_analytics(start_date, None, None)
        
        elif request.GET.get('custom_analysis', '').lower() == 'true':
            custom_start_date = request.GET.get('start_date', '')
            custom_end_date = request.GET.get('end_date', '')
            
            if not custom_start_date or not custom_end_date:
                return JsonResponse({'error': 'start_date and end_date are required for custom analysis'}, status=400)
            
            try:
                start_date = datetime.strptime(custom_start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(custom_end_date, '%Y-%m-%d').date()
                print(f"Processing custom analysis from {start_date} to {end_date}")
                if filter_type == 'total':
                    data = get_custom_total_analytics(start_date, end_date, None, None)
                elif filter_type == 'route':
                    data = get_custom_route_analytics(filter_value, start_date, end_date, None, None)
                elif filter_type == 'bus':
                    data = get_custom_bus_analytics(filter_value, start_date, end_date, None, None)
                else:
                    data = get_custom_total_analytics(start_date, end_date, None, None)
            except ValueError:
                return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
        # Handle regular analytics requests
        elif filter_type == 'total':
            data = get_total_analytics(start_date, end_date)
        elif filter_type == 'route':
            data = get_route_analytics(filter_value, start_date, end_date, None, None)
        elif filter_type == 'bus':
            data = get_bus_analytics(filter_value, start_date, end_date)
        elif filter_type == 'daily':
            data = get_daily_analytics(start_date, end_date)
        elif filter_type == 'hourly':
            data = get_hourly_analytics(start_date, end_date)
        elif filter_type == 'enhanced_hourly':
            data = get_hourly_analytics_with_time_tracking(start_date, end_date)
        elif filter_type == 'enhanced_daily':
            data = get_daily_analytics_with_time_tracking(start_date, end_date)
        elif filter_type == 'enhanced_weekly':
            data = get_weekly_analytics_with_time_tracking()
        elif filter_type == 'journey_duration':
            data = get_journey_duration_analytics(start_date, end_date)
        elif filter_type == 'route_time':
            data = get_route_time_analytics(filter_value, start_date, end_date)
        else:
            data = get_total_analytics(start_date, end_date)
            
        print(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'List response'}")
        
    except Exception as e:
        print(f"Error in analytics API: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
    
    # Handle list responses (like hourly data) with safe=False
    if isinstance(data, list):
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse(data)

def get_total_analytics(start_date, end_date):
    """Get total system analytics"""
    # Filter trips by date range
    trips_filter = Q()
    tickets_filter = Q()
    
    if start_date:
        trips_filter &= Q(date__gte=start_date)
        tickets_filter &= Q(trip__date__gte=start_date)
    if end_date:
        trips_filter &= Q(date__lte=end_date)
        tickets_filter &= Q(trip__date__lte=end_date)
    
    trips = Trip.objects.filter(trips_filter)
    tickets = Ticket.objects.filter(tickets_filter)
    
    # Basic metrics
    total_trips = trips.count()
    completed_trips = trips.filter(is_ended=True).count()
    active_trips = trips.filter(is_ended=False).count()
    total_revenue = float(tickets.aggregate(Sum('price'))['price__sum'] or 0)
    total_tickets = tickets.count()
    avg_ticket_price = float(tickets.aggregate(Avg('price'))['price__avg'] or 0)
    
    # Route performance
    route_data = []
    for route in Route.objects.all():
        route_trips = trips.filter(route=route)
        route_tickets = tickets.filter(trip__route=route)
        route_revenue = float(route_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        
        route_data.append({
            'route_id': route.route_id,
            'name': f"{route.start_stopage.name} → {route.end_stopage.name}",
            'trips': route_trips.count(),
            'tickets': route_tickets.count(),
            'revenue': route_revenue,
            'start': route.start_stopage.name,
            'end': route.end_stopage.name
        })
    
    # Bus performance (Users with role 'bus')
    bus_data = []
    for bus in User.objects.filter(role='bus'):
        # Trip.bus field contains bus ID as string, so filter by ID
        bus_trips = trips.filter(bus=bus.id)
        bus_tickets = tickets.filter(trip__bus=bus.id)
        bus_revenue = float(bus_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        
        bus_data.append({
            'bus_id': bus.id,
            'bus_name': str(bus.id),  # Using ID as name since User model doesn't have separate name field
            'bus_number': str(bus.id),
            'trips': bus_trips.count(),
            'tickets': bus_tickets.count(),
            'revenue': bus_revenue
        })
    daily_revenue = []
    reference_date = end_date if end_date else get_bangladesh_time().date()
    for i in range(30):
        date = reference_date - timedelta(days=i)
        day_trips = trips.filter(date=date)
        day_tickets = tickets.filter(trip__date=date)
        day_revenue = float(day_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        daily_revenue.append({
            'date': date.strftime('%Y-%m-%d'),
            'day_name': date.strftime('%A'),
            'trips': day_trips.count(),
            'revenue': day_revenue,
            'tickets': day_tickets.count(),
            'avg_ticket_price': float(day_tickets.aggregate(Avg('price'))['price__avg'] or 0)
        })
    hourly_tickets = defaultdict(int)
    hourly_revenue = defaultdict(float)
    
    for ticket in tickets.filter(trip__start_time__isnull=False):
        if ticket.trip.start_time:
            hour = ticket.trip.start_time.hour
            hourly_tickets[hour] += 1
            hourly_revenue[hour] += float(ticket.price)
    
    hourly_data = []
    for hour in range(24):
        hourly_data.append({
            'hour': hour,
            'tickets': hourly_tickets[hour],
            'revenue': hourly_revenue[hour]
        })
    
    stopage_congestion = get_stopage_congestion_analysis(start_date, end_date)
    
    return {
        'summary': {
            'total_trips': total_trips,
            'completed_trips': completed_trips,
            'active_trips': active_trips,
            'total_revenue': total_revenue,
            'total_tickets': total_tickets,
            'avg_ticket_price': avg_ticket_price,
            'total_buses': User.objects.filter(role='bus').count(),
            'total_routes': Route.objects.count(),
            'available_cards': Card.objects.filter(availability=True).count()
        },
        'route_performance': route_data,
        'bus_performance': bus_data,
        'daily_trend': daily_revenue,
        'hourly_distribution': hourly_data,
        'stopage_congestion': stopage_congestion
    }

def get_route_analytics(route_id, start_date, end_date, start_time=None, end_time=None):
    """Get analytics for a specific route with optional time interval filtering"""
    try:
        route = Route.objects.get(route_id=route_id)
    except Route.DoesNotExist:
        return {'error': 'Route not found'}
    
    # Filter by date range
    trips_filter = Q(route=route)
    if start_date:
        trips_filter &= Q(date__gte=start_date)
    if end_date:
        trips_filter &= Q(date__lte=end_date)
    
    trips = Trip.objects.filter(trips_filter)
    tickets = Ticket.objects.filter(trip__in=trips)
    
    # Filter tickets by boarding time if time interval is provided
    if start_time and end_time:
        tickets = tickets.filter(
            in_ticket_time__time__gte=start_time,
            in_ticket_time__time__lte=end_time
        )
    
    # Daily performance for this route
    daily_performance = []
    for i in range(30):
        date = (end_date or get_bangladesh_time().date()) - timedelta(days=i)
        day_trips = trips.filter(date=date)
        day_tickets = tickets.filter(trip__date=date)
        day_revenue = float(day_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        
        daily_performance.append({
            'date': date.strftime('%Y-%m-%d'),
            'trips': day_trips.count(),
            'tickets': day_tickets.count(),
            'revenue': day_revenue
        })
    
    # Stopage congestion analysis for this specific route with time filtering
    route_stopage_congestion = get_route_stopage_analysis(route, start_date, end_date, start_time, end_time)
    
    # Time interval summary if time filtering is applied
    time_interval_info = None
    if start_time and end_time:
        time_interval_info = {
            'start_time': start_time.strftime('%H:%M'),
            'end_time': end_time.strftime('%H:%M'),
            'interval_trips': trips.count(),
            'interval_tickets': tickets.count(),
            'interval_revenue': float(tickets.aggregate(Sum('price'))['price__sum'] or 0)
        }
    
    return {
        'route_info': {
            'route_id': route.route_id,
            'name': f"{route.start_stopage.name} → {route.end_stopage.name}",
            'start': route.start_stopage.name,
            'end': route.end_stopage.name
        },
        'summary': {
            'total_trips': trips.count(),
            'total_tickets': tickets.count(),
            'total_revenue': float(tickets.aggregate(Sum('price'))['price__sum'] or 0),
            'avg_ticket_price': float(tickets.aggregate(Avg('price'))['price__avg'] or 0)
        },
        'daily_performance': daily_performance,
        'stopage_congestion': route_stopage_congestion,
        'time_interval': time_interval_info
    }

def get_bus_analytics(bus_id, start_date, end_date):
    """Get analytics for a specific bus"""
    try:
        bus = User.objects.get(id=bus_id, role='bus')
    except User.DoesNotExist:
        return {'error': 'Bus not found'}
    
    # Filter by date range
    trips_filter = Q(bus=bus.id)  # Use bus.id since Trip.bus is a string field
    if start_date:
        trips_filter &= Q(date__gte=start_date)
    if end_date:
        trips_filter &= Q(date__lte=end_date)
    
    trips = Trip.objects.filter(trips_filter)
    tickets = Ticket.objects.filter(trip__in=trips)
    
    # Route performance for this bus
    route_performance = []
    for route in Route.objects.all():
        route_trips = trips.filter(route=route)
        route_tickets = tickets.filter(trip__route=route)
        
        if route_trips.exists():
            route_performance.append({
                'route_id': route.route_id,
                'route_name': f"{route.start_stopage.name} → {route.end_stopage.name}",
                'trips': route_trips.count(),
                'tickets': route_tickets.count(),
                'revenue': float(route_tickets.aggregate(Sum('price'))['price__sum'] or 0)
            })
    
    # Daily performance - respect actual date range
    daily_performance = []
    
    # Calculate the actual date range
    actual_end_date = end_date or get_bangladesh_time().date()
    if start_date and start_date == actual_end_date:
        # If start_date equals end_date (like "today"), show only that day
        date_range = [actual_end_date]
    else:
        # Otherwise, show range from start_date to end_date (max 30 days for performance)
        actual_start_date = start_date or (actual_end_date - timedelta(days=29))
        days_diff = (actual_end_date - actual_start_date).days
        max_days = min(days_diff + 1, 30)  # Limit to 30 days max
        date_range = [actual_end_date - timedelta(days=i) for i in range(max_days)]
    
    for date in date_range:
        day_trips = trips.filter(date=date)
        day_tickets = tickets.filter(trip__date=date)
        
        daily_performance.append({
            'date': date.strftime('%Y-%m-%d'),
            'trips': day_trips.count(),
            'tickets': day_tickets.count(),
            'revenue': float(day_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        })
    
    # Get owner info
    try:
        owner = Owner.objects.get(bus=bus).owner
        owner_info = {'id': owner.id, 'name': owner.id}
    except Owner.DoesNotExist:
        owner_info = {'id': 'Unknown', 'name': 'Unknown'}
    
    return {
        'bus_info': {
            'bus_id': bus.id,
            'bus_name': bus.id,
            'bus_number': bus.id,
            'owner': owner_info
        },
        'summary': {
            'total_trips': trips.count(),
            'total_tickets': tickets.count(),
            'total_revenue': float(tickets.aggregate(Sum('price'))['price__sum'] or 0),
            'avg_ticket_price': float(tickets.aggregate(Avg('price'))['price__avg'] or 0),
            'routes_served': trips.values('route').distinct().count()
        },
        'route_performance': route_performance,
        'daily_performance': daily_performance
    }

def get_daily_analytics(start_date, end_date):
    """Get daily analytics breakdown"""
    if not end_date:
        end_date = get_bangladesh_time().date()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    daily_data = []
    current_date = start_date
    
    while current_date <= end_date:
        day_trips = Trip.objects.filter(date=current_date)
        day_tickets = Ticket.objects.filter(trip__date=current_date)
        
        # Weekend analysis
        is_weekend = current_date.weekday() >= 5
        
        daily_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': current_date.strftime('%A'),
            'is_weekend': is_weekend,
            'trips': day_trips.count(),
            'completed_trips': day_trips.filter(is_ended=True).count(),
            'tickets': day_tickets.count(),
            'revenue': float(day_tickets.aggregate(Sum('price'))['price__sum'] or 0),
            'avg_ticket_price': float(day_tickets.aggregate(Avg('price'))['price__avg'] or 0)
        })
        
        current_date += timedelta(days=1)
    
    return {
        'daily_breakdown': daily_data,
        'period_summary': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_days': (end_date - start_date).days + 1
        }
    }

def get_hourly_analytics(start_date, end_date):
    """Get hourly analytics breakdown"""
    tickets_filter = Q()
    if start_date:
        tickets_filter &= Q(trip__date__gte=start_date)
    if end_date:
        tickets_filter &= Q(trip__date__lte=end_date)
    
    tickets = Ticket.objects.filter(tickets_filter)
    
    # Since tickets don't have time, use trip start_time
    hourly_data = []
    for hour in range(24):
        hour_tickets = tickets.filter(trip__start_time__hour=hour)
        
        hourly_data.append({
            'hour': hour,
            'hour_label': f'{hour:02d}:00',
            'tickets': hour_tickets.count(),
            'revenue': float(hour_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        })
    
    return {
        'hourly_breakdown': hourly_data,
        'peak_hours': {
            'morning': {'start': 7, 'end': 10},
            'afternoon': {'start': 12, 'end': 14},
            'evening': {'start': 17, 'end': 20}
        }
    }

def get_filter_options(request):
    """Get available filter options for dropdowns"""
    routes = [{'id': r.route_id, 'name': f'{r.start_stopage.name} → {r.end_stopage.name}'} 
              for r in Route.objects.all()]
    
    buses = [{'id': b.id, 'name': f'{b.id}'} 
             for b in User.objects.filter(role='bus')]
    
    # Predefined time intervals
    time_intervals = [
        {'id': 'all_day', 'name': 'All Day', 'start': '00:00', 'end': '23:59'},
        {'id': 'morning_rush', 'name': 'Morning Rush (7:00 AM - 10:00 AM)', 'start': '07:00', 'end': '10:00'},
        {'id': 'midday', 'name': 'Midday (11:00 AM - 1:00 PM)', 'start': '11:00', 'end': '13:00'},
        {'id': 'afternoon', 'name': 'Afternoon (2:00 PM - 5:00 PM)', 'start': '14:00', 'end': '17:00'},
        {'id': 'evening_rush', 'name': 'Evening Rush (5:00 PM - 8:00 PM)', 'start': '17:00', 'end': '20:00'},
        {'id': 'night', 'name': 'Night (8:00 PM - 11:00 PM)', 'start': '20:00', 'end': '23:00'},
        {'id': 'custom', 'name': 'Custom Time Range', 'start': '', 'end': ''}
    ]
    
    return JsonResponse({
        'routes': routes,
        'buses': buses,
        'time_periods': [
            {'id': 'today', 'name': 'Today'},
            {'id': 'week', 'name': 'Last 7 Days'},
            {'id': 'month', 'name': 'Last 30 Days'},
            {'id': 'year', 'name': 'Last Year'},
            {'id': 'all', 'name': 'All Time'}
        ],
        'time_intervals': time_intervals
    })

def get_route_stopage_analysis(route, start_date, end_date, start_time=None, end_time=None):
    """Analyze congestion at each stopage for a specific route with optional time filtering"""
    # Filter tickets by route and date range
    tickets_filter = Q(trip__route=route)
    if start_date:
        tickets_filter &= Q(trip__date__gte=start_date)
    if end_date:
        tickets_filter &= Q(trip__date__lte=end_date)
    
    # Add time filtering if provided - use ticket boarding time instead of trip start time
    if start_time and end_time:
        # Filter by actual boarding time (in_ticket_time) when time range is specified
        tickets_filter &= Q(
            in_ticket_time__time__gte=start_time, 
            in_ticket_time__time__lte=end_time,
            in_ticket_time__isnull=False
        )
    
    tickets = Ticket.objects.filter(tickets_filter)
    
    # Get all stopages for this route in order
    route_stopages = RouteStopage.objects.filter(route=route).order_by('order')
    
    stopage_analysis = []
    
    for route_stopage in route_stopages:
        stopage = route_stopage.stopage
        
        # Count boarding and alighting at this stopage
        # Calculate boarding and alighting for this stopage
        # Calculate boarding and alighting for this stopage
        boarding_count = tickets.filter(start_stopage=stopage).count()
        alighting_count = tickets.filter(end_stopage=stopage).count()
        boarding_revenue = float(tickets.filter(start_stopage=stopage).aggregate(Sum('price'))['price__sum'] or 0)
        
        stopage_analysis.append({
            'stopage_id': stopage.id,
            'stopage_name': stopage.name,
            'position': route_stopage.order,
            'distance_from_start': route_stopage.distance_from_last_stopage,
            'boarding_count': boarding_count,
            'alighting_count': alighting_count,
            'total_traffic': boarding_count + alighting_count,
            'revenue': boarding_revenue
        })
    
    return stopage_analysis

def get_stopage_congestion_analysis(start_date, end_date):
    """Analyze congestion/traffic at each stopage by counting boarding and alighting passengers"""
    # Filter tickets by date range
    tickets_filter = Q()
    if start_date:
        tickets_filter &= Q(trip__date__gte=start_date)
    if end_date:
        tickets_filter &= Q(trip__date__lte=end_date)
    
    tickets = Ticket.objects.filter(tickets_filter)
    
    # Count boarding (start_stopage) and alighting (end_stopage) at each stopage
    stopage_data = {}
    
    # Get all stopages
    all_stopages = Stopage.objects.all()
    
    for stopage in all_stopages:
        # Count tickets starting from this stopage (boarding)
        boarding_count = tickets.filter(start_stopage=stopage).count()
        boarding_revenue = float(tickets.filter(start_stopage=stopage).aggregate(Sum('price'))['price__sum'] or 0)
        
        # Count tickets ending at this stopage (alighting)
        alighting_count = tickets.filter(end_stopage=stopage).count()
        
        # Get stopage position in routes (if available)
        route_stopage = RouteStopage.objects.filter(stopage=stopage).first()
        position = route_stopage.order if route_stopage else None
        
        stopage_data[stopage.name] = {
            'stopage_id': stopage.id,
            'stopage_name': stopage.name,
            'position': position,
            'boarding_count': boarding_count,
            'alighting_count': alighting_count,
            'total_traffic': boarding_count + alighting_count,
            'revenue': boarding_revenue
        }
    
    # Sort by total traffic (most congested first)
    stopage_list = list(stopage_data.values())
    stopage_list.sort(key=lambda x: x['total_traffic'], reverse=True)
    
    return stopage_list

def get_hourly_total_analytics(target_date, start_time, end_time):
    """Get hourly analytics for total system within specified time range"""
    print(f"Getting hourly total analytics for {target_date} from {start_time} to {end_time}")
    
    # Filter tickets by date and time range
    tickets = Ticket.objects.filter(
        trip__date=target_date,
        in_ticket_time__time__gte=start_time,
        in_ticket_time__time__lte=end_time,
        in_ticket_time__isnull=False  # Only tickets with boarding time
    )
    
    print(f"Found {tickets.count()} tickets in time range")
    
    # Generate hourly breakdown
    hourly_breakdown = []
    hourly_trend = []
    hourly_distribution = []
    
    current_hour = start_time.hour
    end_hour = end_time.hour
    
    # Handle time ranges that span midnight
    if end_hour < current_hour:
        end_hour += 24
    
    total_trips = 0
    total_revenue = 0
    total_tickets = 0
    peak_hour = None
    max_tickets = 0
    active_buses = set()
    
    while current_hour <= end_hour:
        hour_24 = current_hour % 24
        
        # Filter tickets for this hour
        hour_tickets = tickets.filter(in_ticket_time__time__hour=hour_24)
        hour_count = hour_tickets.count()
        hour_revenue = float(hour_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        hour_trips = hour_tickets.values('trip').distinct().count()
        
        # Track peak hour
        if hour_count > max_tickets:
            max_tickets = hour_count
            peak_hour = f"{hour_24:02d}:00"
        
        # Collect active buses
        hour_buses = hour_tickets.values_list('trip__bus', flat=True).distinct()
        active_buses.update(hour_buses)
        
        # Accumulate totals
        total_trips += hour_trips
        total_revenue += hour_revenue
        total_tickets += hour_count
        
        # Add to data structures
        hourly_breakdown.append({
            'hour': hour_24,
            'trips': hour_trips,
            'tickets': hour_count,
            'revenue': hour_revenue,
            'avg_ticket_price': hour_revenue / hour_count if hour_count > 0 else 0,
            'time_period': get_time_period_name(hour_24)
        })
        
        hourly_trend.append({
            'hour': hour_24,
            'revenue': hour_revenue,
            'trips': hour_trips
        })
        
        hourly_distribution.append({
            'hour': hour_24,
            'tickets': hour_count
        })
        
        current_hour += 1
    
    # Get route performance for this time range
    route_performance = []
    for route in Route.objects.all():
        route_tickets = tickets.filter(trip__route=route)
        if route_tickets.exists():
            route_performance.append({
                'route_id': route.route_id,
                'route_name': f"{route.start_stopage.name} → {route.end_stopage.name}",
                'tickets': route_tickets.count(),
                'revenue': float(route_tickets.aggregate(Sum('price'))['price__sum'] or 0),
                'trips': route_tickets.values('trip').distinct().count()
            })
    
    # Get bus performance for this time range
    bus_performance = []
    for bus_id in active_buses:
        if bus_id:  # Skip None values
            bus_tickets = tickets.filter(trip__bus=bus_id)
            if bus_tickets.exists():
                bus_performance.append({
                    'bus_id': bus_id,
                    'tickets': bus_tickets.count(),
                    'revenue': float(bus_tickets.aggregate(Sum('price'))['price__sum'] or 0),
                    'trips': bus_tickets.values('trip').distinct().count()
                })
    
    return {
        'hourly_summary': {
            'total_trips': total_trips,
            'total_revenue': total_revenue,
            'total_tickets': total_tickets,
            'active_buses': len(active_buses),
            'peak_hour': peak_hour or 'N/A'
        },
        'hourly_breakdown': hourly_breakdown,
        'hourly_trend': hourly_trend,
        'hourly_distribution': hourly_distribution,
        'hourly_route_performance': route_performance,
        'hourly_bus_performance': bus_performance
    }

def get_hourly_route_analytics(route_id, target_date, start_time, end_time):
    """Get hourly analytics for a specific route within specified time range"""
    print(f"Getting hourly route analytics for route {route_id} on {target_date} from {start_time} to {end_time}")
    
    try:
        route = Route.objects.get(route_id=route_id)
    except Route.DoesNotExist:
        return {'error': 'Route not found'}
    
    # Filter tickets by route, date and time range
    tickets = Ticket.objects.filter(
        trip__route=route,
        trip__date=target_date,
        in_ticket_time__time__gte=start_time,
        in_ticket_time__time__lte=end_time,
        in_ticket_time__isnull=False
    )
    
    print(f"Found {tickets.count()} tickets for route in time range")
    
    # Generate hourly breakdown
    hourly_breakdown = []
    hourly_trend = []
    hourly_distribution = []
    
    current_hour = start_time.hour
    end_hour = end_time.hour
    
    if end_hour < current_hour:
        end_hour += 24
    
    total_trips = 0
    total_revenue = 0
    total_tickets = 0
    peak_hour = None
    max_tickets = 0
    
    while current_hour <= end_hour:
        hour_24 = current_hour % 24
        
        hour_tickets = tickets.filter(in_ticket_time__time__hour=hour_24)
        hour_count = hour_tickets.count()
        hour_revenue = float(hour_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        hour_trips = hour_tickets.values('trip').distinct().count()
        
        if hour_count > max_tickets:
            max_tickets = hour_count
            peak_hour = f"{hour_24:02d}:00"
        
        total_trips += hour_trips
        total_revenue += hour_revenue
        total_tickets += hour_count
        
        hourly_breakdown.append({
            'hour': hour_24,
            'trips': hour_trips,
            'tickets': hour_count,
            'revenue': hour_revenue,
            'avg_ticket_price': hour_revenue / hour_count if hour_count > 0 else 0
        })
        
        hourly_trend.append({
            'hour': hour_24,
            'revenue': hour_revenue,
            'trips': hour_trips
        })
        
        hourly_distribution.append({
            'hour': hour_24,
            'tickets': hour_count
        })
        
        current_hour += 1
    
    # Get stopage analysis for this time range
    stopage_analysis = get_route_stopage_analysis(route, target_date, target_date, start_time, end_time)
    
    return {
        'route_info': {
            'route_id': route.route_id,
            'name': f"{route.start_stopage.name} → {route.end_stopage.name}",
            'start': route.start_stopage.name,
            'end': route.end_stopage.name
        },
        'hourly_summary': {
            'total_trips': total_trips,
            'total_revenue': total_revenue,
            'total_tickets': total_tickets,
            'peak_hour': peak_hour or 'N/A'
        },
        'hourly_breakdown': hourly_breakdown,
        'hourly_trend': hourly_trend,
        'hourly_distribution': hourly_distribution,
        'hourly_stopage_analysis': stopage_analysis
    }

def get_hourly_bus_analytics(bus_id, target_date, start_time, end_time):
    """Get hourly analytics for a specific bus within specified time range"""
    print(f"Getting hourly bus analytics for bus {bus_id} on {target_date} from {start_time} to {end_time}")
    
    try:
        bus = User.objects.get(id=bus_id, role='bus')
    except User.DoesNotExist:
        return {'error': 'Bus not found'}
    
    # Filter tickets by bus, date and time range
    tickets = Ticket.objects.filter(
        trip__bus=bus.id,
        trip__date=target_date,
        in_ticket_time__time__gte=start_time,
        in_ticket_time__time__lte=end_time,
        in_ticket_time__isnull=False
    )
    
    print(f"Found {tickets.count()} tickets for bus in time range")
    
    # Generate hourly breakdown
    hourly_breakdown = []
    hourly_trend = []
    hourly_distribution = []
    
    current_hour = start_time.hour
    end_hour = end_time.hour
    
    if end_hour < current_hour:
        end_hour += 24
    
    total_trips = 0
    total_revenue = 0
    total_tickets = 0
    peak_hour = None
    max_tickets = 0
    routes_covered = set()
    
    while current_hour <= end_hour:
        hour_24 = current_hour % 24
        
        hour_tickets = tickets.filter(in_ticket_time__time__hour=hour_24)
        hour_count = hour_tickets.count()
        hour_revenue = float(hour_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        hour_trips = hour_tickets.values('trip').distinct().count()
        
        # Track routes covered in this hour
        hour_routes = hour_tickets.values_list('trip__route', flat=True).distinct()
        routes_covered.update(hour_routes)
        
        if hour_count > max_tickets:
            max_tickets = hour_count
            peak_hour = f"{hour_24:02d}:00"
        
        total_trips += hour_trips
        total_revenue += hour_revenue
        total_tickets += hour_count
        
        hourly_breakdown.append({
            'hour': hour_24,
            'trips': hour_trips,
            'tickets': hour_count,
            'revenue': hour_revenue,
            'avg_ticket_price': hour_revenue / hour_count if hour_count > 0 else 0
        })
        
        hourly_trend.append({
            'hour': hour_24,
            'revenue': hour_revenue,
            'trips': hour_trips
        })
        
        hourly_distribution.append({
            'hour': hour_24,
            'tickets': hour_count
        })
        
        current_hour += 1
    
    # Get route distribution for this bus in this time range
    route_distribution = []
    for route_id in routes_covered:
        if route_id:
            try:
                route = Route.objects.get(id=route_id)
                route_tickets = tickets.filter(trip__route=route)
                route_distribution.append({
                    'route_id': route.route_id,
                    'route_name': f"{route.start_stopage.name} → {route.end_stopage.name}",
                    'tickets': route_tickets.count(),
                    'revenue': float(route_tickets.aggregate(Sum('price'))['price__sum'] or 0),
                    'trips': route_tickets.values('trip').distinct().count()
                })
            except Route.DoesNotExist:
                continue
    
    return {
        'bus_info': {
            'bus_id': bus.id,
            'bus_name': str(bus.id),
            'bus_number': str(bus.id)
        },
        'hourly_summary': {
            'total_trips': total_trips,
            'total_revenue': total_revenue,
            'total_tickets': total_tickets,
            'routes_covered': len(routes_covered),
            'peak_hour': peak_hour or 'N/A'
        },
        'hourly_breakdown': hourly_breakdown,
        'hourly_trend': hourly_trend,
        'hourly_distribution': hourly_distribution,
        'hourly_route_distribution': route_distribution
    }

def get_time_period_name(hour):
    """Get time period name for a given hour"""
    if 6 <= hour < 12:
        return 'Morning'
    elif 12 <= hour < 18:
        return 'Afternoon'
    elif 18 <= hour < 22:
        return 'Evening'
    else:
        return 'Night'

def get_route_stopage_analysis(route, start_date, end_date, start_time=None, end_time=None):
    """Get stopage analysis for a route within optional time range"""
    try:
        routestopages = RouteStopage.objects.filter(route=route).order_by('order')
        
        stopage_data = []
        for rs in routestopages:
            # Base query for tickets involving this stopage and route
            base_tickets_query = Ticket.objects.filter(
                trip__route=route,
                trip__date__gte=start_date,
                trip__date__lte=end_date
            )
            
            # Add time filtering if provided
            if start_time and end_time:
                base_tickets_query = base_tickets_query.filter(
                    in_ticket_time__time__gte=start_time,
                    in_ticket_time__time__lte=end_time,
                    in_ticket_time__isnull=False
                )
            
            # Calculate boarding (passengers getting on at this stopage)
            boarding_count = base_tickets_query.filter(start_stopage=rs.stopage).count()
            
            # Calculate alighting (passengers getting off at this stopage)
            alighting_count = base_tickets_query.filter(end_stopage=rs.stopage).count()
            
            # Calculate revenue from boarding at this stopage
            boarding_revenue = float(base_tickets_query.filter(start_stopage=rs.stopage).aggregate(Sum('price'))['price__sum'] or 0)
            
            stopage_data.append({
                'stopage_id': rs.stopage.id,
                'stopage_name': rs.stopage.name,
                'position': rs.order if rs.order is not None else 'N/A',  # Ensure it's never None
                'order': rs.order if rs.order is not None else 'N/A',     # Keep 'order' for backward compatibility
                'boarding_count': boarding_count,
                'alighting_count': alighting_count,
                'total_traffic': boarding_count + alighting_count,
                'tickets': boarding_count,  # For backward compatibility
                'revenue': boarding_revenue,
                'avg_revenue_per_ticket': float(boarding_revenue / boarding_count) if boarding_count > 0 else 0,
                'congestion_level': get_congestion_level(boarding_count + alighting_count)
            })
        
        return stopage_data
    except Exception as e:
        print(f"Error in route stopage analysis: {e}")
        return []

def get_custom_total_analytics(start_date, end_date, start_time=None, end_time=None):
    """Get custom date/time range analytics for total system"""
    print(f"Getting custom total analytics from {start_date} to {end_date}")
    
    # Base ticket query
    tickets_query = Ticket.objects.filter(
        trip__date__gte=start_date,
        trip__date__lte=end_date
    )
    
    # Apply time filtering if provided
    if start_time and end_time:
        tickets_query = tickets_query.filter(
            in_ticket_time__time__gte=start_time,
            in_ticket_time__time__lte=end_time,
            in_ticket_time__isnull=False
        )
    
    print(f"Found {tickets_query.count()} tickets in custom range")
    
    # Summary calculations
    total_tickets = tickets_query.count()
    total_revenue = float(tickets_query.aggregate(Sum('price'))['price__sum'] or 0)
    total_trips = tickets_query.values('trip').distinct().count()
    active_routes = tickets_query.values('trip__route').distinct().count()
    avg_ticket_price = total_revenue / total_tickets if total_tickets > 0 else 0
    
    # Daily trend within the date range
    daily_trend = []
    current_date = start_date
    while current_date <= end_date:
        day_tickets_query = tickets_query.filter(trip__date=current_date)
        
        # Apply time filter for daily data too
        if start_time and end_time:
            day_tickets_query = day_tickets_query.filter(
                in_ticket_time__time__gte=start_time,
                in_ticket_time__time__lte=end_time,
                in_ticket_time__isnull=False
            )
        
        day_trips = day_tickets_query.values('trip').distinct().count()
        day_tickets = day_tickets_query.count()
        day_revenue = float(day_tickets_query.aggregate(Sum('price'))['price__sum'] or 0)
        
        daily_trend.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': current_date.strftime('%A'),
            'trips': day_trips,
            'tickets': day_tickets,
            'revenue': day_revenue,
            'avg_ticket_price': day_revenue / day_tickets if day_tickets > 0 else 0
        })
        
        current_date += timedelta(days=1)
    
    # Hourly distribution for the entire period
    hourly_distribution = []
    for hour in range(24):
        hour_tickets = tickets_query.filter(
            in_ticket_time__hour=hour,
            in_ticket_time__isnull=False
        ).count()
        
        hourly_distribution.append({
            'hour': hour,
            'tickets': hour_tickets
        })
    
    # Route performance for the period
    route_performance = []
    for route in Route.objects.all():
        route_tickets = tickets_query.filter(trip__route=route)
        if route_tickets.exists():
            route_performance.append({
                'route_id': route.route_id,
                'start': route.start_stopage.name,
                'end': route.end_stopage.name,
                'tickets': route_tickets.count(),
                'revenue': float(route_tickets.aggregate(Sum('price'))['price__sum'] or 0),
                'trips': route_tickets.values('trip').distinct().count()
            })
    
    # Bus performance for the period
    bus_performance = []
    active_buses = tickets_query.values_list('trip__bus', flat=True).distinct()
    for bus_id in active_buses:
        if bus_id:
            bus_tickets = tickets_query.filter(trip__bus=bus_id)
            bus_performance.append({
                'bus_id': bus_id,
                'tickets': bus_tickets.count(),
                'revenue': float(bus_tickets.aggregate(Sum('price'))['price__sum'] or 0),
                'trips': bus_tickets.values('trip').distinct().count()
            })
    
    # Enhanced stopage congestion analysis
    stopage_congestion = get_custom_stopage_congestion_analysis(start_date, end_date, start_time, end_time)
    
    return {
        'summary': {
            'total_trips': total_trips,
            'total_revenue': total_revenue,
            'total_tickets': total_tickets,
            'active_routes': active_routes,
            'avg_ticket_price': avg_ticket_price,
            'peak_congestion_level': get_peak_congestion_level(stopage_congestion)
        },
        'daily_trend': daily_trend,
        'hourly_distribution': hourly_distribution,
        'route_performance': route_performance,
        'bus_performance': bus_performance,
        'stopage_congestion': stopage_congestion
    }

def get_custom_route_analytics(route_id, start_date, end_date, start_time=None, end_time=None):
    """Get custom date/time range analytics for a specific route"""
    print(f"Getting custom route analytics for route {route_id} from {start_date} to {end_date}")
    
    try:
        route = Route.objects.get(route_id=route_id)
    except Route.DoesNotExist:
        return {'error': 'Route not found'}
    
    # Base ticket query for this route
    tickets_query = Ticket.objects.filter(
        trip__route=route,
        trip__date__gte=start_date,
        trip__date__lte=end_date
    )
    
    # Apply time filtering if provided
    if start_time and end_time:
        tickets_query = tickets_query.filter(
            in_ticket_time__time__gte=start_time,
            in_ticket_time__time__lte=end_time,
            in_ticket_time__isnull=False
        )
    
    print(f"Found {tickets_query.count()} tickets for route in custom range")
    
    # Summary calculations
    total_tickets = tickets_query.count()
    total_revenue = float(tickets_query.aggregate(Sum('price'))['price__sum'] or 0)
    total_trips = tickets_query.values('trip').distinct().count()
    avg_ticket_price = total_revenue / total_tickets if total_tickets > 0 else 0
    
    # Daily performance within the date range
    daily_performance = []
    current_date = start_date
    while current_date <= end_date:
        day_tickets_query = tickets_query.filter(trip__date=current_date)
        
        day_trips = day_tickets_query.values('trip').distinct().count()
        day_tickets = day_tickets_query.count()
        day_revenue = float(day_tickets_query.aggregate(Sum('price'))['price__sum'] or 0)
        
        daily_performance.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': current_date.strftime('%A'),
            'trips': day_trips,
            'tickets': day_tickets,
            'revenue': day_revenue,
            'avg_ticket_price': day_revenue / day_tickets if day_tickets > 0 else 0
        })
        
        current_date += timedelta(days=1)
    
    # Hourly pattern for this route
    hourly_pattern = []
    for hour in range(24):
        hour_tickets = tickets_query.filter(
            in_ticket_time__hour=hour,
            in_ticket_time__isnull=False
        ).count()
        
        hourly_pattern.append({
            'hour': hour,
            'tickets': hour_tickets
        })
    
    # Stopage congestion analysis for this route
    stopage_congestion = get_route_stopage_analysis(route, start_date, end_date, start_time, end_time)
    
    # Enhanced stopage analysis with boarding/alighting details
    enhanced_stopage_congestion = []
    for stopage_data in stopage_congestion:
        stopage_id = stopage_data['stopage_id']
        
        # Calculate boarding and alighting for this stopage
        boarding_count = tickets_query.filter(start_stopage_id=stopage_id).count()
        # For alighting, we need to check tickets where this stopage is the destination
        alighting_count = tickets_query.filter(end_stopage_id=stopage_id).count()
        
        enhanced_stopage_congestion.append({
            'stopage_name': stopage_data['stopage_name'],
            'position': stopage_data['order'],
            'boarding_count': boarding_count,
            'alighting_count': alighting_count,
            'revenue': stopage_data['revenue']
        })
    
    return {
        'route_info': {
            'route_id': route.route_id,
            'name': f"{route.start_stopage.name} → {route.end_stopage.name}",
            'start': route.start_stopage.name,
            'end': route.end_stopage.name
        },
        'summary': {
            'total_trips': total_trips,
            'total_revenue': total_revenue,
            'total_tickets': total_tickets,
            'avg_ticket_price': avg_ticket_price
        },
        'daily_performance': daily_performance,
        'hourly_pattern': hourly_pattern,
        'stopage_congestion': enhanced_stopage_congestion
    }

def get_bus_stopage_analysis(bus, start_date, end_date, start_time=None, end_time=None):
    """Get stopage analysis for a bus within optional time range"""
    try:
        # Base query for tickets involving this bus
        base_tickets_query = Ticket.objects.filter(
            trip__bus=bus.id,
            trip__date__gte=start_date,
            trip__date__lte=end_date
        )
        
        # Add time filtering if provided
        if start_time and end_time:
            base_tickets_query = base_tickets_query.filter(
                in_ticket_time__time__gte=start_time,
                in_ticket_time__time__lte=end_time,
                in_ticket_time__isnull=False
            )
        
        # Get all stopages that have activity with this bus in this period
        active_stopages = set()
        active_stopages.update(base_tickets_query.values_list('start_stopage', flat=True))
        active_stopages.update(base_tickets_query.values_list('end_stopage', flat=True))
        active_stopages.discard(None)  # Remove None values
        
        stopage_analysis = []
        
        for stopage_id in active_stopages:
            try:
                stopage = Stopage.objects.get(id=stopage_id)
                
                # Calculate boarding (passengers getting on at this stopage)
                boarding_count = base_tickets_query.filter(start_stopage=stopage).count()
                
                # Calculate alighting (passengers getting off at this stopage)
                alighting_count = base_tickets_query.filter(end_stopage=stopage).count()
                
                # Calculate revenue generated from this stopage
                stopage_revenue = float(base_tickets_query.filter(start_stopage=stopage).aggregate(Sum('price'))['price__sum'] or 0)
                
                # Determine position if this stopage belongs to any route
                position = 'N/A'
                try:
                    route_stopage = RouteStopage.objects.filter(stopage=stopage).first()
                    if route_stopage:
                        position = route_stopage.order
                except RouteStopage.DoesNotExist:
                    pass
                
                stopage_analysis.append({
                    'stopage_id': stopage.id,
                    'stopage_name': stopage.name,
                    'position': position,
                    'boarding_count': boarding_count,
                    'alighting_count': alighting_count,
                    'total_traffic': boarding_count + alighting_count,
                    'revenue': stopage_revenue
                })
            except Stopage.DoesNotExist:
                continue
        return stopage_analysis
    except Exception as e:
        print(f"Error in bus stopage analysis: {e}")
        return []


def get_custom_bus_analytics(bus_id, start_date, end_date, start_time=None, end_time=None):
    """Get custom date/time range analytics for a specific bus"""
    print(f"Getting custom bus analytics for bus {bus_id} from {start_date} to {end_date}")
    try:
        bus = User.objects.get(id=bus_id, role='bus')
    except User.DoesNotExist:
        return {'error': 'Bus not found'}
    
    # Base ticket query for this bus
    tickets_query = Ticket.objects.filter(
        trip__bus=bus.id,
        trip__date__gte=start_date,
        trip__date__lte=end_date
    )
    
    # Apply time filtering if provided
    if start_time and end_time:
        tickets_query = tickets_query.filter(
            in_ticket_time__time__gte=start_time,
            in_ticket_time__time__lte=end_time,
            in_ticket_time__isnull=False
        )
    
    print(f"Found {tickets_query.count()} tickets for bus in custom range")
    
    # Summary calculations
    total_tickets = tickets_query.count()
    total_revenue = float(tickets_query.aggregate(Sum('price'))['price__sum'] or 0)
    total_trips = tickets_query.values('trip').distinct().count()
    routes_served = tickets_query.values('trip__route').distinct().count()
    
    # Daily performance within the date range
    daily_performance = []
    current_date = start_date
    while current_date <= end_date:
        day_tickets_query = tickets_query.filter(trip__date=current_date)
        
        day_trips = day_tickets_query.values('trip').distinct().count()
        day_tickets = day_tickets_query.count()
        day_revenue = float(day_tickets_query.aggregate(Sum('price'))['price__sum'] or 0)
        
        daily_performance.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': current_date.strftime('%A'),
            'trips': day_trips,
            'tickets': day_tickets,
            'revenue': day_revenue
        })
        
        current_date += timedelta(days=1)
    
    # Route distribution for this bus
    route_performance = []
    active_routes = tickets_query.values_list('trip__route', flat=True).distinct()
    for route_id in active_routes:
        if route_id:
            try:
                route = Route.objects.get(id=route_id)
                route_tickets = tickets_query.filter(trip__route=route)
                route_performance.append({
                    'route_id': route.route_id,
                    'route_name': f"{route.start_stopage.name} → {route.end_stopage.name}",
                    'tickets': route_tickets.count(),
                    'revenue': float(route_tickets.aggregate(Sum('price'))['price__sum'] or 0),
                    'trips': route_tickets.values('trip').distinct().count()
                })
            except Route.DoesNotExist:
                continue
    stopage_analysis = get_bus_stopage_analysis(bus, start_date, end_date, start_time, end_time)
    return {
        'bus_info': {
            'bus_id': bus.id,
            'bus_name': str(bus.id),
            'bus_number': str(bus.id)
        },
        'summary': {
            'total_trips': total_trips,
            'total_revenue': total_revenue,
            'total_tickets': total_tickets,
            'routes_served': routes_served
        },
        'daily_performance': daily_performance,
        'route_performance': route_performance,
        'stopage_congestion': stopage_analysis
    }
def get_custom_stopage_congestion_analysis(start_date, end_date, start_time=None, end_time=None):
    """Get enhanced stopage congestion analysis for custom date/time range"""
    print(f"Getting custom stopage congestion analysis from {start_date} to {end_date}")
    
    # Base ticket query
    tickets_query = Ticket.objects.filter(
        trip__date__gte=start_date,
        trip__date__lte=end_date
    )
    
    # Apply time filtering if provided
    if start_time and end_time:
        tickets_query = tickets_query.filter(
            in_ticket_time__time__gte=start_time,
            in_ticket_time__time__lte=end_time,
            in_ticket_time__isnull=False
        )
    
    stopage_data = []
    
    # Get all stopages that have activity in this period
    active_stopages = set()
    active_stopages.update(tickets_query.values_list('start_stopage', flat=True))
    active_stopages.update(tickets_query.values_list('end_stopage', flat=True))
    active_stopages.discard(None)  # Remove None values
    
    for stopage_id in active_stopages:
        try:
            stopage = Stopage.objects.get(id=stopage_id)
            
            # Calculate boarding (passengers getting on at this stopage)
            boarding_count = tickets_query.filter(start_stopage=stopage).count()
            
            # Calculate alighting (passengers getting off at this stopage)
            alighting_count = tickets_query.filter(end_stopage=stopage).count()
            
            # Calculate revenue generated from this stopage
            stopage_revenue = float(tickets_query.filter(start_stopage=stopage).aggregate(Sum('price'))['price__sum'] or 0)
            
            # Determine position if this stopage belongs to any route
            position = 'N/A'
            try:
                route_stopage = RouteStopage.objects.filter(stopage=stopage).first()
                if route_stopage and route_stopage.order is not None:
                    position = route_stopage.order
            except Exception:
                pass
            
            stopage_data.append({
                'stopage_id': stopage.id,
                'stopage_name': stopage.name,
                'position': position,
                'boarding_count': boarding_count,
                'alighting_count': alighting_count,
                'total_traffic': boarding_count + alighting_count,
                'revenue': stopage_revenue,
                'congestion_level': get_congestion_level(boarding_count + alighting_count)
            })
            
        except Stopage.DoesNotExist:
            continue
    
    # Sort by total traffic (most congested first)
    stopage_data.sort(key=lambda x: x['total_traffic'], reverse=True)
    
    print(f"Found {len(stopage_data)} active stopages in custom range")
    return stopage_data

def get_congestion_level(total_traffic):
    """Determine congestion level based on total traffic"""
    if total_traffic > 50:
        return 'High'
    elif total_traffic > 20:
        return 'Medium'
    else:
        return 'Low'

def get_peak_congestion_level(stopage_congestion):
    """Get the peak congestion level from stopage data"""
    if not stopage_congestion:
        return 'N/A'
    
    max_traffic = max([s.get('total_traffic', 0) for s in stopage_congestion], default=0)
    return get_congestion_level(max_traffic)

def traffic_analytics(request):
    """Get traffic analytics from ImgNow data"""
    period = request.GET.get('period', 'week')
    
    end_time = timezone.now()
    if period == 'today':
        start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_time = end_time - timedelta(days=7)
    elif period == 'month':
        start_time = end_time - timedelta(days=30)
    else:
        start_time = end_time - timedelta(days=7)
    
    traffic_data = ImgNow.objects.filter(
        time__gte=start_time,
        time__lte=end_time
    ).order_by('time')
    
    # Group by road
    traffic_by_road = defaultdict(list)
    for record in traffic_data:
        traffic_by_road[record.road.name].append({
            'time': record.time.strftime('%Y-%m-%d %H:%M'),
            'value': record.value
        })
    
    return JsonResponse({
        'traffic_data': dict(traffic_by_road),
        'period': period,
        'total_records': traffic_data.count()
    })