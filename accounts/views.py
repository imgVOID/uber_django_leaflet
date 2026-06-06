from rest_framework import generics, permissions
from .models import ClientProfile, DriverProfile, StaffProfile
from .serializers import (
	ClientProfileSerializer,
	DriverProfileSerializer,
	StaffProfileSerializer,
)
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView
from .forms import *
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin


class BaseProfileView(generics.RetrieveUpdateAPIView):
	permission_classes = [permissions.IsAuthenticated]

	def get_object(self):
		user = self.request.user
		obj, _ = self.queryset.get_or_create(user=user)
		return obj


class ClientProfileView(BaseProfileView):
	queryset = ClientProfile.objects
	serializer_class = ClientProfileSerializer


class DriverProfileView(BaseProfileView):
	queryset = DriverProfile.objects
	serializer_class = DriverProfileSerializer


class StaffProfileView(BaseProfileView):
	queryset = StaffProfile.objects
	serializer_class = StaffProfileSerializer


class RegisterView(FormView):
	template_name = 'register.html'
	form_class = RegistrationForm
	success_url = reverse_lazy('accounts:register-success')

	def form_valid(self, form):
		user = form.save()
		return super().form_valid(form)


class RegisterSuccessView(TemplateView):
	template_name = 'register_success.html'


class CustomLoginView(LoginView):
    form_class = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
