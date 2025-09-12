from django.contrib import admin
from .models import Restaurant, Store, MenuItem, Nutrients

admin.site.register(Restaurant)
admin.site.register(Store)
admin.site.register(Nutrients)
admin.site.register(MenuItem)
