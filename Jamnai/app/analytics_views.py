from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from app.models import Trip, Ticket, Schedule, Route, Card, ImgNow, User, Owner, Stopage, RouteStopage
import json
from collections import defaultdict

def analytics_dashboard(request):
    """Main analytics dashboard view"""
    return render(request, 'app/analytics.html')

def analytics_api(request):
    """API endpoint for analytics data"""
    filter_type = request.GET.get('filter', 'total')  # total, route, bus, day, week, month
    filter_value = request.GET.get('value', '')
    time_period = request.GET.get('period', 'all')  # all, today, week, month, year
    
    # Get date range based on time period
    end_date = timezone.now().date()
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
    
    data = {}
    
    try:
        if filter_type == 'total':
            data = get_total_analytics(start_date, end_date)
        elif filter_type == 'route':
            data = get_route_analytics(filter_value, start_date, end_date)
        elif filter_type == 'bus':
            data = get_bus_analytics(filter_value, start_date, end_date)
        elif filter_type == 'daily':
            data = get_daily_analytics(start_date, end_date)
        elif filter_type == 'hourly':
            data = get_hourly_analytics(start_date, end_date)
        else:
            data = get_total_analytics(start_date, end_date)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
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
        bus_trips = trips.filter(bus=bus)
        bus_tickets = tickets.filter(trip__bus=bus)
        bus_revenue = float(bus_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        
        bus_data.append({
            'bus_id': bus.id,
            'bus_name': bus.id,  # Using ID as name since User model doesn't have separate name field
            'bus_number': bus.id,
            'trips': bus_trips.count(),
            'tickets': bus_tickets.count(),
            'revenue': bus_revenue
        })
    
    # Daily revenue trend (last 30 days)
    daily_revenue = []
    for i in range(30):
        date = end_date - timedelta(days=i)
        day_tickets = tickets.filter(trip__date=date)
        day_revenue = float(day_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        
        daily_revenue.append({
            'date': date.strftime('%Y-%m-%d'),
            'revenue': day_revenue,
            'tickets': day_tickets.count()
        })
    
    # Hourly distribution based on trip start times (since tickets don't have time field)
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
    
    # Stopage congestion analysis
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

def get_route_analytics(route_id, start_date, end_date):
    """Get analytics for a specific route"""
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
    
    # Daily performance for this route
    daily_performance = []
    for i in range(30):
        date = (end_date or timezone.now().date()) - timedelta(days=i)
        day_trips = trips.filter(date=date)
        day_tickets = tickets.filter(trip__date=date)
        day_revenue = float(day_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        
        daily_performance.append({
            'date': date.strftime('%Y-%m-%d'),
            'trips': day_trips.count(),
            'tickets': day_tickets.count(),
            'revenue': day_revenue
        })
    
    # Stopage congestion analysis for this specific route
    route_stopage_congestion = get_route_stopage_analysis(route, start_date, end_date)
    
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
        'stopage_congestion': route_stopage_congestion
    }

def get_bus_analytics(bus_id, start_date, end_date):
    """Get analytics for a specific bus"""
    try:
        bus = User.objects.get(id=bus_id, role='bus')
    except User.DoesNotExist:
        return {'error': 'Bus not found'}
    
    # Filter by date range
    trips_filter = Q(bus=bus)
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
    
    # Daily performance
    daily_performance = []
    for i in range(30):
        date = (end_date or timezone.now().date()) - timedelta(days=i)
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
        end_date = timezone.now().date()
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
    
    return JsonResponse({
        'routes': routes,
        'buses': buses,
        'time_periods': [
            {'id': 'today', 'name': 'Today'},
            {'id': 'week', 'name': 'Last 7 Days'},
            {'id': 'month', 'name': 'Last 30 Days'},
            {'id': 'year', 'name': 'Last Year'},
            {'id': 'all', 'name': 'All Time'}
        ]
    })

def get_route_stopage_analysis(route, start_date, end_date):
    """Analyze congestion at each stopage for a specific route"""
    # Filter tickets by route and date range
    tickets_filter = Q(trip__route=route)
    if start_date:
        tickets_filter &= Q(trip__date__gte=start_date)
    if end_date:
        tickets_filter &= Q(trip__date__lte=end_date)
    
    tickets = Ticket.objects.filter(tickets_filter)
    
    # Get all stopages for this route in order
    route_stopages = RouteStopage.objects.filter(route=route).order_by('order')
    
    stopage_analysis = []
    
    for route_stopage in route_stopages:
        stopage = route_stopage.stopage
        
        # Count boarding and alighting at this stopage
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