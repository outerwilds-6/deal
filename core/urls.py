from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/run/', views.run_script, name='run_script'),
    path('api/stop/', views.stop_script, name='stop_script'), # 新增
    path('api/logs/', views.get_logs, name='get_logs'),       # 新增
]