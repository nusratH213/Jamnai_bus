from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, id, password=None, role=None):
        if not id:
            raise ValueError("Users must have an ID")
        user = self.model(id=id, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, id, password=None, role='admin'):
        user = self.create_user(id=id, password=password, role=role)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user
    
class User(AbstractBaseUser, PermissionsMixin):
    id = models.CharField(max_length=50, primary_key=True, unique=True)
    role = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    USERNAME_FIELD = 'id'
    REQUIRED_FIELDS = ['role']
    objects = CustomUserManager()

    def __str__(self):
        return self.id

class Stopage(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

class Route(models.Model):
    route_id = models.CharField(max_length=10, unique=True)
    start_stopage = models.ForeignKey(Stopage, related_name='route_start', on_delete=models.CASCADE)
    end_stopage = models.ForeignKey(Stopage, related_name='route_end', on_delete=models.CASCADE)

    def __str__(self):
        return f"Route {self.route_id}: {self.start_stopage} to {self.end_stopage}"
    
class RouteStopage(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    stopage = models.ForeignKey(Stopage, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()  # to keep stopage order in route
    distance_from_last_stopage = models.FloatField(help_text="Distance (in km) from the previous stopage")

    class Meta:
        unique_together = ('route', 'order')
        ordering = ['order']

    def __str__(self):
        return f"{self.route.route_id} - {self.stopage.name} (Order: {self.order}, Distance from last: {self.distance_from_last_stopage} km)"


from django.conf import settings
from app.models import Route, Stopage  # Adjust import path if needed

class Trip(models.Model):
    trip_id = models.CharField(max_length=100, unique=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    bus = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'role': 'bus'})
    date = models.DateField()
    is_ended = models.BooleanField(default=False)  # marks if trip has ended

    def __str__(self):
        status = 'Ended' if self.is_ended else 'Ongoing'
        return f"Trip {self.trip_id} - Bus {self.bus} on Route {self.route} - {status}"


class Schedule(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='schedules')
    stopage = models.ForeignKey(Stopage, on_delete=models.CASCADE)
    arrival_time = models.TimeField()
    departure_time = models.TimeField()

    class Meta:
        ordering = ['arrival_time']

    def __str__(self):
        return f"{self.trip.trip_id} - {self.stopage.name} (Arrive: {self.arrival_time}, Depart: {self.departure_time})"

class Card(models.Model):
    card_id = models.CharField(max_length=100, unique=True)
    availability = models.BooleanField(default=True)  # True = Active/Usable, False = Inactive/Lost
    
    def __str__(self):
        return f"Card {self.card_id} - {'Available' if self.availability else 'Unavailable'}"
    
class Ticket(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    start_stopage = models.ForeignKey(Stopage, on_delete=models.CASCADE, related_name='ticket_start')
    end_stopage = models.ForeignKey(Stopage, on_delete=models.CASCADE, related_name='ticket_end', null=True, blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Ticket for Card {self.card.card_id} on Trip {self.trip.trip_id}: {self.start_stopage} ➝ {self.end_stopage}"