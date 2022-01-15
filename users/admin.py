from django.contrib import admin
from .models import Profile # must include b4 registering

admin.site.register(Profile) # After making a table to make it visible in the admin page i need to register it here