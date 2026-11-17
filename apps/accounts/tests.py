from rest_framework.test import APITestCase

from apps.accounts.models import User, ConsentRecord
from core.consent import CURRENT_CONSENT_VERSION


class ConsentTests(APITestCase):
    def _register(self, **extra):
        data = {'phone': '01812345678', 'password': 'pass1234', 'name': 'Rahim', **extra}
        return self.client.post('/api/auth/register/', data, format='json')

    def test_register_requires_consent(self):
        self.assertEqual(self._register().status_code, 400)
        self.assertEqual(self._register(consent_accepted='true', consent_version=CURRENT_CONSENT_VERSION).status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_register_rejects_outdated_notice(self):
        res = self._register(consent_accepted=True, consent_version='old')
        self.assertEqual(res.status_code, 409)
        self.assertEqual(res.data['current_version'], CURRENT_CONSENT_VERSION)

    def test_register_records_consent(self):
        res = self._register(consent_accepted=True, consent_version=CURRENT_CONSENT_VERSION, language='bn')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertFalse(res.data['user']['consent_required'])
        record = ConsentRecord.objects.get()
        self.assertEqual((record.version, record.channel, record.language), (CURRENT_CONSENT_VERSION, 'register', 'bn'))

    def test_existing_patient_must_accept_on_login(self):
        User.objects.create_user(phone='01812345678', password='pass1234', name='Old', health_id='DH-1', roles=['patient'])
        res = self.client.post('/api/auth/login/', {'identifier': '01812345678', 'password': 'pass1234'}, format='json')
        self.assertTrue(res.data['user']['consent_required'])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['token']}")
        self.assertEqual(self.client.post('/api/auth/consent/', {'version': 'old'}, format='json').status_code, 409)
        res = self.client.post('/api/auth/consent/', {'version': CURRENT_CONSENT_VERSION, 'language': 'en'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data['user']['consent_required'])
        self.assertEqual(ConsentRecord.objects.get().channel, 'login')

    def test_staff_only_accounts_are_not_asked(self):
        User.objects.create_user(phone='01812345678', password='pass1234', name='Admin', health_id='DH-1', roles=['admin'])
        res = self.client.post('/api/auth/login/', {'identifier': '01812345678', 'password': 'pass1234'}, format='json')
        self.assertFalse(res.data['user']['consent_required'])

    def test_consent_requires_login(self):
        self.assertEqual(self.client.post('/api/auth/consent/', {'version': CURRENT_CONSENT_VERSION}, format='json').status_code, 401)
