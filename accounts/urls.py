from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
	path('api/profile/client/', views.ClientProfileView.as_view(), name='profile-client'),
	path('api/profile/driver/', views.DriverProfileView.as_view(), name='profile-driver'),
	path('api/profile/staff/', views.StaffProfileView.as_view(), name='profile-staff'),
	path('register/', views.RegisterView.as_view(), name='register'),
	path('register/success/', views.RegisterSuccessView.as_view(), name='register-success'),
	path('login/', views.CustomLoginView.as_view(template_name='login.html'), name='login'),
]
