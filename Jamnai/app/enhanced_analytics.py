"""
Enhanced Analytics Functions with Time Tracking
This module provides advanced analytics using the new time tracking fields:
- in_ticket_time: When passenger boards the bus
- out_ticket_time: When passenger alights from the bus
- is_completed: Whether the journey is completed
"""

from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import datetime, timedelta, time
from app.models import Trip, Ticket, Schedule, Route, Stopage
from collections import defaultdict
import pytz


def get_bangladesh_time():
    """Helper function to get current time in Bangladesh timezone"""
    bd_timezone = pytz.timezone('Asia/Dhaka')
    return timezone.now().astimezone(bd_timezone)


def get_hourly_analytics_with_time_tracking(start_date=None, end_date=None):
    """
    Get hourly analytics using actual boarding/alighting times
    Uses in_ticket_time for boarding analysis and out_ticket_time for alighting analysis
    """
    # Filter tickets by date range
    tickets_filter = Q()
    if start_date:
        tickets_filter &= Q(trip__date__gte=start_date)
    if end_date:
        tickets_filter &= Q(trip__date__lte=end_date)
    
    tickets = Ticket.objects.filter(tickets_filter)
    
    hourly_data = []
    for hour in range(24):
        # Count boarding passengers by hour (using in_ticket_time)
        boarding_tickets = tickets.filter(
            in_ticket_time__isnull=False,
            in_ticket_time__hour=hour
        )
        
        # Count alighting passengers by hour (using out_ticket_time)
        alighting_tickets = tickets.filter(
            out_ticket_time__isnull=False,
            out_ticket_time__hour=hour
        )
        
        # Revenue from tickets that started in this hour
        boarding_revenue = float(boarding_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        
        # Count completed vs incomplete journeys starting in this hour
        completed_in_hour = boarding_tickets.filter(is_completed=True).count()
        incomplete_in_hour = boarding_tickets.filter(is_completed=False).count()
        
        # Calculate average journey duration for completed tickets in this hour
        completed_tickets = boarding_tickets.filter(
            is_completed=True,
            out_ticket_time__isnull=False
        )
        
        total_duration_minutes = 0
        duration_count = 0
        for ticket in completed_tickets:
            if ticket.in_ticket_time and ticket.out_ticket_time:
                # Convert times to datetime for calculation
                in_datetime = datetime.combine(ticket.trip.date, ticket.in_ticket_time)
                out_datetime = datetime.combine(ticket.trip.date, ticket.out_ticket_time)
                
                # Handle case where out_time is next day
                if ticket.out_ticket_time < ticket.in_ticket_time:
                    out_datetime += timedelta(days=1)
                
                duration = (out_datetime - in_datetime).total_seconds() / 60
                total_duration_minutes += duration
                duration_count += 1
        
        avg_duration = total_duration_minutes / duration_count if duration_count > 0 else 0
        
        hourly_data.append({
            'hour': hour,
            'hour_label': f'{hour:02d}:00',
            'boarding_count': boarding_tickets.count(),
            'alighting_count': alighting_tickets.count(),
            'boarding_revenue': boarding_revenue,
            'completed_journeys': completed_in_hour,
            'incomplete_journeys': incomplete_in_hour,
            'avg_journey_duration_minutes': round(avg_duration, 2),
            'completion_rate': round((completed_in_hour / (completed_in_hour + incomplete_in_hour)) * 100, 2) if (completed_in_hour + incomplete_in_hour) > 0 else 0
        })
    
    return {
        'hourly_breakdown': hourly_data,
        'analysis_type': 'time_tracking_enhanced',
        'peak_boarding_hours': sorted(hourly_data, key=lambda x: x['boarding_count'], reverse=True)[:3],
        'peak_alighting_hours': sorted(hourly_data, key=lambda x: x['alighting_count'], reverse=True)[:3]
    }


def get_daily_analytics_with_time_tracking(start_date=None, end_date=None):
    """
    Get daily analytics using actual time tracking data
    """
    if not end_date:
        end_date = get_bangladesh_time().date()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    daily_data = []
    current_date = start_date
    
    while current_date <= end_date:
        day_tickets = Ticket.objects.filter(trip__date=current_date)
        
        # Boarding analysis
        boarding_tickets = day_tickets.filter(in_ticket_time__isnull=False)
        
        # Alighting analysis
        alighting_tickets = day_tickets.filter(out_ticket_time__isnull=False)
        
        # Journey completion analysis
        completed_tickets = day_tickets.filter(is_completed=True)
        incomplete_tickets = day_tickets.filter(is_completed=False)
        
        # Revenue analysis
        day_revenue = float(day_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        
        # Average journey duration for the day
        total_duration = 0
        duration_count = 0
        for ticket in completed_tickets.filter(in_ticket_time__isnull=False, out_ticket_time__isnull=False):
            if ticket.in_ticket_time and ticket.out_ticket_time:
                in_datetime = datetime.combine(current_date, ticket.in_ticket_time)
                out_datetime = datetime.combine(current_date, ticket.out_ticket_time)
                
                if ticket.out_ticket_time < ticket.in_ticket_time:
                    out_datetime += timedelta(days=1)
                
                duration = (out_datetime - in_datetime).total_seconds() / 60
                total_duration += duration
                duration_count += 1
        
        avg_duration = total_duration / duration_count if duration_count > 0 else 0
        
        # Peak hours for the day
        hourly_boarding = defaultdict(int)
        hourly_alighting = defaultdict(int)
        
        for ticket in boarding_tickets:
            hourly_boarding[ticket.in_ticket_time.hour] += 1
        
        for ticket in alighting_tickets:
            hourly_alighting[ticket.out_ticket_time.hour] += 1
        
        peak_boarding_hour = max(hourly_boarding.items(), key=lambda x: x[1])[0] if hourly_boarding else None
        peak_alighting_hour = max(hourly_alighting.items(), key=lambda x: x[1])[0] if hourly_alighting else None
        
        daily_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': current_date.strftime('%A'),
            'is_weekend': current_date.weekday() >= 5,
            'total_tickets': day_tickets.count(),
            'boarding_count': boarding_tickets.count(),
            'alighting_count': alighting_tickets.count(),
            'completed_journeys': completed_tickets.count(),
            'incomplete_journeys': incomplete_tickets.count(),
            'completion_rate': round((completed_tickets.count() / day_tickets.count()) * 100, 2) if day_tickets.count() > 0 else 0,
            'revenue': day_revenue,
            'avg_journey_duration_minutes': round(avg_duration, 2),
            'peak_boarding_hour': peak_boarding_hour,
            'peak_alighting_hour': peak_alighting_hour
        })
        
        current_date += timedelta(days=1)
    
    return {
        'daily_breakdown': daily_data,
        'period_summary': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_days': (end_date - start_date).days + 1,
            'total_completed_journeys': sum(day['completed_journeys'] for day in daily_data),
            'total_incomplete_journeys': sum(day['incomplete_journeys'] for day in daily_data),
            'overall_completion_rate': round(
                (sum(day['completed_journeys'] for day in daily_data) / 
                 sum(day['total_tickets'] for day in daily_data)) * 100, 2
            ) if sum(day['total_tickets'] for day in daily_data) > 0 else 0
        }
    }


def get_weekly_analytics_with_time_tracking():
    """
    Get weekly analytics with time tracking insights
    """
    end_date = get_bangladesh_time().date()
    start_date = end_date - timedelta(days=6)  # Current week (7 days)
    
    weekly_data = []
    current_date = start_date
    
    while current_date <= end_date:
        day_data = get_daily_analytics_with_time_tracking(current_date, current_date)
        if day_data['daily_breakdown']:
            weekly_data.append(day_data['daily_breakdown'][0])
        current_date += timedelta(days=1)
    
    # Weekly patterns analysis
    weekday_patterns = defaultdict(list)
    for day in weekly_data:
        weekday_patterns[day['day_name']].append({
            'completion_rate': day['completion_rate'],
            'avg_duration': day['avg_journey_duration_minutes'],
            'total_tickets': day['total_tickets']
        })
    
    # Calculate averages for each weekday
    weekday_averages = {}
    for day_name, data_list in weekday_patterns.items():
        if data_list:
            weekday_averages[day_name] = {
                'avg_completion_rate': round(sum(d['completion_rate'] for d in data_list) / len(data_list), 2),
                'avg_duration': round(sum(d['avg_duration'] for d in data_list) / len(data_list), 2),
                'avg_tickets': round(sum(d['total_tickets'] for d in data_list) / len(data_list), 2)
            }
    
    return {
        'weekly_breakdown': weekly_data,
        'weekday_patterns': weekday_averages,
        'week_summary': {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_tickets': sum(day['total_tickets'] for day in weekly_data),
            'total_completed': sum(day['completed_journeys'] for day in weekly_data),
            'total_incomplete': sum(day['incomplete_journeys'] for day in weekly_data),
            'week_completion_rate': round(
                (sum(day['completed_journeys'] for day in weekly_data) / 
                 sum(day['total_tickets'] for day in weekly_data)) * 100, 2
            ) if sum(day['total_tickets'] for day in weekly_data) > 0 else 0
        }
    }


def get_route_time_analytics(route_id, start_date=None, end_date=None):
    """
    Get route-specific analytics using time tracking
    """
    try:
        route = Route.objects.get(route_id=route_id)
    except Route.DoesNotExist:
        return {'error': 'Route not found'}
    
    # Filter tickets by route and date range
    tickets_filter = Q(trip__route=route)
    if start_date:
        tickets_filter &= Q(trip__date__gte=start_date)
    if end_date:
        tickets_filter &= Q(trip__date__lte=end_date)
    
    tickets = Ticket.objects.filter(tickets_filter)
    
    # Time-based route analysis
    hourly_route_data = []
    for hour in range(24):
        hour_tickets = tickets.filter(in_ticket_time__hour=hour)
        completed_in_hour = hour_tickets.filter(is_completed=True)
        
        # Calculate average journey duration for this hour
        total_duration = 0
        duration_count = 0
        for ticket in completed_in_hour.filter(in_ticket_time__isnull=False, out_ticket_time__isnull=False):
            if ticket.in_ticket_time and ticket.out_ticket_time:
                in_datetime = datetime.combine(ticket.trip.date, ticket.in_ticket_time)
                out_datetime = datetime.combine(ticket.trip.date, ticket.out_ticket_time)
                
                if ticket.out_ticket_time < ticket.in_ticket_time:
                    out_datetime += timedelta(days=1)
                
                duration = (out_datetime - in_datetime).total_seconds() / 60
                total_duration += duration
                duration_count += 1
        
        avg_duration = total_duration / duration_count if duration_count > 0 else 0
        
        hourly_route_data.append({
            'hour': hour,
            'tickets': hour_tickets.count(),
            'completed': completed_in_hour.count(),
            'avg_duration_minutes': round(avg_duration, 2),
            'revenue': float(hour_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        })
    
    # Stopage-wise boarding/alighting patterns
    from app.models import RouteStopage
    route_stopages = RouteStopage.objects.filter(route=route).order_by('order')
    
    stopage_patterns = []
    for route_stopage in route_stopages:
        stopage = route_stopage.stopage
        
        # Boarding at this stopage
        boarding_tickets = tickets.filter(start_stopage=stopage)
        
        # Alighting at this stopage
        alighting_tickets = tickets.filter(end_stopage=stopage)
        
        # Time patterns for this stopage
        hourly_boarding = defaultdict(int)
        hourly_alighting = defaultdict(int)
        
        for ticket in boarding_tickets.filter(in_ticket_time__isnull=False):
            hourly_boarding[ticket.in_ticket_time.hour] += 1
        
        for ticket in alighting_tickets.filter(out_ticket_time__isnull=False):
            hourly_alighting[ticket.out_ticket_time.hour] += 1
        
        peak_boarding_hour = max(hourly_boarding.items(), key=lambda x: x[1])[0] if hourly_boarding else None
        peak_alighting_hour = max(hourly_alighting.items(), key=lambda x: x[1])[0] if hourly_alighting else None
        
        stopage_patterns.append({
            'stopage_name': stopage.name,
            'position': route_stopage.order,
            'boarding_count': boarding_tickets.count(),
            'alighting_count': alighting_tickets.count(),
            'peak_boarding_hour': peak_boarding_hour,
            'peak_alighting_hour': peak_alighting_hour,
            'revenue': float(boarding_tickets.aggregate(Sum('price'))['price__sum'] or 0)
        })
    
    return {
        'route_info': {
            'route_id': route.route_id,
            'name': f"{route.start_stopage.name} → {route.end_stopage.name}",
            'start': route.start_stopage.name,
            'end': route.end_stopage.name
        },
        'hourly_patterns': hourly_route_data,
        'stopage_patterns': stopage_patterns,
        'summary': {
            'total_tickets': tickets.count(),
            'completed_tickets': tickets.filter(is_completed=True).count(),
            'completion_rate': round(
                (tickets.filter(is_completed=True).count() / tickets.count()) * 100, 2
            ) if tickets.count() > 0 else 0,
            'total_revenue': float(tickets.aggregate(Sum('price'))['price__sum'] or 0)
        }
    }


def get_journey_duration_analytics(start_date=None, end_date=None):
    """
    Analyze journey durations using actual boarding and alighting times
    """
    # Filter for completed tickets with both times
    tickets_filter = Q(
        is_completed=True,
        in_ticket_time__isnull=False,
        out_ticket_time__isnull=False
    )
    
    if start_date:
        tickets_filter &= Q(trip__date__gte=start_date)
    if end_date:
        tickets_filter &= Q(trip__date__lte=end_date)
    
    tickets = Ticket.objects.filter(tickets_filter)
    
    # Calculate journey durations
    duration_data = []
    route_durations = defaultdict(list)
    hourly_durations = defaultdict(list)
    
    for ticket in tickets:
        if ticket.in_ticket_time and ticket.out_ticket_time:
            in_datetime = datetime.combine(ticket.trip.date, ticket.in_ticket_time)
            out_datetime = datetime.combine(ticket.trip.date, ticket.out_ticket_time)
            
            # Handle overnight journeys
            if ticket.out_ticket_time < ticket.in_ticket_time:
                out_datetime += timedelta(days=1)
            
            duration_minutes = (out_datetime - in_datetime).total_seconds() / 60
            
            duration_data.append({
                'ticket_id': ticket.id,
                'duration_minutes': duration_minutes,
                'route_id': ticket.trip.route.route_id,
                'start_stopage': ticket.start_stopage.name,
                'end_stopage': ticket.end_stopage.name,
                'boarding_hour': ticket.in_ticket_time.hour,
                'price': float(ticket.price)
            })
            
            # Group by route
            route_durations[ticket.trip.route.route_id].append(duration_minutes)
            
            # Group by boarding hour
            hourly_durations[ticket.in_ticket_time.hour].append(duration_minutes)
    
    # Calculate statistics
    if duration_data:
        all_durations = [d['duration_minutes'] for d in duration_data]
        avg_duration = sum(all_durations) / len(all_durations)
        min_duration = min(all_durations)
        max_duration = max(all_durations)
        
        # Duration distribution
        duration_ranges = {
            '0-15 min': len([d for d in all_durations if 0 <= d <= 15]),
            '16-30 min': len([d for d in all_durations if 16 <= d <= 30]),
            '31-45 min': len([d for d in all_durations if 31 <= d <= 45]),
            '46-60 min': len([d for d in all_durations if 46 <= d <= 60]),
            '60+ min': len([d for d in all_durations if d > 60])
        }
    else:
        avg_duration = min_duration = max_duration = 0
        duration_ranges = {}
    
    # Route-wise duration analysis
    route_analysis = []
    for route_id, durations in route_durations.items():
        if durations:
            route_analysis.append({
                'route_id': route_id,
                'avg_duration_minutes': round(sum(durations) / len(durations), 2),
                'min_duration': round(min(durations), 2),
                'max_duration': round(max(durations), 2),
                'journey_count': len(durations)
            })
    
    # Hourly duration analysis
    hourly_analysis = []
    for hour, durations in hourly_durations.items():
        if durations:
            hourly_analysis.append({
                'hour': hour,
                'hour_label': f'{hour:02d}:00',
                'avg_duration_minutes': round(sum(durations) / len(durations), 2),
                'journey_count': len(durations)
            })
    
    hourly_analysis.sort(key=lambda x: x['hour'])
    
    return {
        'summary': {
            'total_completed_journeys': len(duration_data),
            'avg_duration_minutes': round(avg_duration, 2),
            'min_duration_minutes': round(min_duration, 2),
            'max_duration_minutes': round(max_duration, 2)
        },
        'duration_distribution': duration_ranges,
        'route_analysis': route_analysis,
        'hourly_analysis': hourly_analysis,
        'detailed_journeys': duration_data[:100]  # Limit to first 100 for performance
    }