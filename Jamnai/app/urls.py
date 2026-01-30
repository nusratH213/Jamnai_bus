from django.urls import path
from . import views
from django.urls import path
from app.views import search_routes, f, get_buses,setbus,getstop,updatestop
from app.analytics_views import (
    analytics_dashboard, analytics_api, get_filter_options, traffic_analytics, enhanced_analytics_dashboard
)

urlpatterns = [
    # path('', views.hello_view, name='hello'),
    # path('home', views.hello_view, name='home'),
    path('owner/', views.ownerview, name='owner'),
    path('bus/', views.bus_dashboard, name='bus'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('search/', search_routes, name='search'),
    path('', search_routes, name='search_h'),
    path('fo/', f, name='f'),
    path('g/', views.g, name='g'),
    path('setg/', views.setg_view ,name='g'),
    path('getbus/', get_buses, name='get_bus'),
    path('setbus/', setbus, name='setbus'),
    path('getstop/', getstop, name='getstop'),
    path('updatestop/', updatestop, name='updatestop'),
    path('gets/', views.gets, name='gets'),
    path('cap/', views.cap, name='cap'),
    
    path('analytics/', analytics_dashboard, name='analytics'),
    path('analytics/enhanced/', enhanced_analytics_dashboard, name='enhanced_analytics'),
    path('analytics/api/', analytics_api, name='analytics_api'),
    path('analytics/filters/', get_filter_options, name='analytics_filters'),
    path('analytics/traffic/', traffic_analytics, name='traffic_analytics'),
    
    # API Testing Dashboard
    path('api-tester/', views.api_tester, name='api_tester'),
    
    # path("api/get-buses/", get_buses),
    # path("api/setbus/", setbus),   

    path('send-location/', views.send_location_page, name='send_location_page'),
    path('location/', views.location_api, name='location_api'),
]