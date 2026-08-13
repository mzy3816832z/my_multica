"""
房源模块路由
"""
from django.urls import path
from apps.apartments import views

urlpatterns = [
    # 公共房源接口（公开访问）
    path('', views.apartment_list, name='apartment-list'),
    path('hot-districts/', views.hot_districts, name='hot-districts'),
    path('geocode/', views.apartment_geocode, name='apartment-geocode'),
    path('map-config/', views.apartment_map_config, name='apartment-map-config'),
    path('<int:id>/', views.apartment_detail, name='apartment-detail'),
    path('<int:id>/room-types/', views.apartment_room_types, name='apartment-room-types'),
    path('<int:id>/nearby/', views.apartment_nearby, name='apartment-nearby'),
    path('room-types/<int:id>/', views.room_type_detail, name='room-type-detail'),
]
