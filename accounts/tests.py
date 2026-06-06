from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import User, ClientProfile, DriverProfile


class ProfileAPITest(TestCase):
	def setUp(self):
		# Create a client user and a driver user
		self.client_user = User.objects.create_user(
			email='client@example.com', password='pass', is_client=True
		)
		self.driver_user = User.objects.create_user(
			email='driver@example.com', password='pass', is_driver=True
		)

		# Ensure signals created profiles
		assert ClientProfile.objects.filter(user=self.client_user).exists()
		assert DriverProfile.objects.filter(user=self.driver_user).exists()

		self.api = APIClient()

	def test_unauthenticated_cannot_access_profiles(self):
		resp = self.api.get(reverse('accounts:profile-client'))
		self.assertEqual(resp.status_code, 401)

	def test_client_can_read_and_update_own_profile(self):
		self.api.force_authenticate(user=self.client_user)

		# Read
		resp = self.api.get(reverse('accounts:profile-client'))
		self.assertEqual(resp.status_code, 200)
		self.assertIn('user', resp.data)

		# Update own profile
		resp = self.api.patch(
			reverse('accounts:profile-client'), {'first_name': 'Alice'}, format='json'
		)
		self.assertEqual(resp.status_code, 200)
		profile = ClientProfile.objects.get(user=self.client_user)
		self.assertEqual(profile.first_name, 'Alice')

	def test_cannot_edit_other_users_profile(self):
		# Client attempts to modify the driver's profile endpoint
		self.api.force_authenticate(user=self.client_user)

		# Set a value on the real driver to detect tampering
		driver_profile = DriverProfile.objects.get(user=self.driver_user)
		driver_profile.first_name = 'Original'
		driver_profile.save()

		# Client calls driver endpoint (this will create/modify client's own driver profile, not other's)
		resp = self.api.patch(
			reverse('accounts:profile-driver'), {'first_name': 'Hacked'}, format='json'
		)
		self.assertEqual(resp.status_code, 200)

		# Reload other driver's profile from DB and confirm unchanged
		driver_profile.refresh_from_db()
		self.assertEqual(driver_profile.first_name, 'Original')

	def test_driver_can_update_own_profile_and_cannot_change_user_field(self):
		self.api.force_authenticate(user=self.driver_user)

		# Driver updates own profile
		resp = self.api.patch(
			reverse('accounts:profile-driver'), {'first_name': 'Bob'}, format='json'
		)
		self.assertEqual(resp.status_code, 200)
		profile = DriverProfile.objects.get(user=self.driver_user)
		self.assertEqual(profile.first_name, 'Bob')

		# Attempt to change `user` field should be ignored (read_only)
		resp = self.api.patch(
			reverse('accounts:profile-driver'), {'user': str(self.client_user.pk)}, format='json'
		)
		self.assertEqual(resp.status_code, 200)
		profile.refresh_from_db()
		self.assertEqual(profile.user, self.driver_user)


	class RegistrationViewTest(TestCase):
		def test_register_creates_client_and_profile(self):
			url = reverse('accounts:register')

			# GET the registration page
			resp = self.client.get(url)
			self.assertEqual(resp.status_code, 200)

			data = {
				'email': 'newclient@example.com',
				'password1': 'secret1234',
				'password2': 'secret1234',
				'role': 'client',
			}

			resp = self.client.post(url, data)
			# should redirect to success
			self.assertEqual(resp.status_code, 302)
			self.assertTrue(User.objects.filter(email='newclient@example.com').exists())
			user = User.objects.get(email='newclient@example.com')
			self.assertTrue(user.check_password('secret1234'))
			# profile created by signals
			self.assertTrue(ClientProfile.objects.filter(user=user).exists())

		def test_register_creates_driver_and_profile(self):
			url = reverse('accounts:register')
			data = {
				'email': 'newdriver@example.com',
				'password1': 'driverpass',
				'password2': 'driverpass',
				'role': 'driver',
			}
			resp = self.client.post(url, data)
			self.assertEqual(resp.status_code, 302)
			user = User.objects.get(email='newdriver@example.com')
			self.assertTrue(user.check_password('driverpass'))
			self.assertTrue(DriverProfile.objects.filter(user=user).exists())

