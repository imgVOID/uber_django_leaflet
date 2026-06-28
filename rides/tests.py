import json
from django.test import TestCase
from django.contrib.auth import get_user_model


class TaxiViewsTestCase(TestCase):
	def setUp(self):
		User = get_user_model()
		# create client user
		self.client_user = User.objects.create_user(email='client@example.com', password='pass')

		# create driver user
		self.driver_user = User.objects.create_user(email='driver@example.com', password='pass', role='driver')

		# create driver profile (signals may or may not have created it)
		from accounts.models import DriverProfile
		driver_profile, _ = DriverProfile.objects.get_or_create(user=self.driver_user)
		driver_profile.is_verified = True
		driver_profile.is_active_driver = True
		driver_profile.first_name = 'John'
		driver_profile.last_name = 'Doe'
		driver_profile.save()

		# create a vehicle for driver
		from vehicles.models import Vehicle
		vehicle = Vehicle.objects.create(
			driver=driver_profile,
			brand='Toyota',
			model='Prius',
			color='blue',
			license_plate='XYZ123',
			year=2020,
			is_available=True,
		)

		# create a DriverLocation near some coords
		from django.contrib.gis.geos import Point
		from .models import DriverLocation
		# Point expects (lng, lat)
		loc = DriverLocation.objects.create(
			driver=driver_profile,
			vehicle=vehicle,
			position=Point(37.618423, 55.751244, srid=4326),
		)

	def test_taxi_request_requires_login_and_renders(self):
		# unauthenticated -> redirect to login
		r = self.client.get('/')
		self.assertEqual(r.status_code, 302)

		# authenticated -> 200 and template
		self.client.force_login(self.client_user)
		r = self.client.get('/')
		self.assertEqual(r.status_code, 200)
		self.assertTemplateUsed(r, 'taxi_request.html')

	def test_set_location_and_session_storage(self):
		self.client.force_login(self.client_user)
		payload = {'lat': 55.751244, 'lng': 37.618423}
		r = self.client.post('/set_location/', data=json.dumps(payload), content_type='application/json')
		self.assertEqual(r.status_code, 200)
		sess = self.client.session
		self.assertIn('user_location', sess)
		self.assertAlmostEqual(float(sess['user_location']['lat']), 55.751244, places=5)

	def test_set_location_invalid_payload(self):
		self.client.force_login(self.client_user)
		r = self.client.post('/set_location/', data='notjson', content_type='application/json')
		self.assertEqual(r.status_code, 400)

	def test_nearby_drivers_returns_driver(self):
		self.client.force_login(self.client_user)
		r = self.client.get('/nearby_drivers/?lat=55.751244&lng=37.618423')
		self.assertEqual(r.status_code, 200)
		data = r.json()
		self.assertIn('drivers', data)
		self.assertGreaterEqual(len(data['drivers']), 1)
		d = data['drivers'][0]
		self.assertIn('driver_name', d)

	def test_taxi_map_requires_login_and_renders(self):
		r = self.client.get('/map/')
		self.assertEqual(r.status_code, 302)
		self.client.force_login(self.client_user)
		r = self.client.get('/map/')
		self.assertEqual(r.status_code, 200)
		self.assertTemplateUsed(r, 'taxi_map.html')

