from django.urls import path
from apps.metro import views

urlpatterns = [
    path('lines/', views.metro_lines, name='metro-lines'),
]
