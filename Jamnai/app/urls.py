from django.urls import path
from . import views
from django.urls import path
from app.views import search_routes, f, get_buses,setbus,getstop,updatestop

urlpatterns = [
    path('', views.hello_view, name='hello'),
    path('home', views.hello_view, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('search/', search_routes, name='search_routes'),
    path('fo/', f, name='f'),
    path('g/', views.g, name='g'),
    path('setg/', views.setg_view ,name='g'),
    path('getbus/', get_buses, name='get_bus'),
    path('setbus/', setbus, name='setbus'),
    path('getstop/', getstop, name='getstop'),
    path('updatestop/', updatestop, name='updatestop'),
]