from django.contrib import admin
from .models import Client, Master, Registration, FeedBack, Hairdressing
# Register your models here.

admin.site.register(Client)
admin.site.register(Master)
admin.site.register(Registration)
admin.site.register(FeedBack)
admin.site.register(Hairdressing)
