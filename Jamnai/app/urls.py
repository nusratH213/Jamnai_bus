from django.urls import path
from . import views
from django.urls import path
from app.views import search_routes

urlpatterns = [
    # path('', views.hello_view, name='hello'),
    path('home', views.hello_view, name='home'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('', search_routes, name='search_routes'),
    path('owner_dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('manager_dashboard/', views.manager_dashboard, name='manager_dashboard'),
]
