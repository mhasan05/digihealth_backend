import shutil
import tempfile
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.patients.models import Patient
from core.utils import normalize_bd_phone
from .models import FieldPrescription

TEMP_MEDIA = tempfile.mkdtemp()


def _image(name='rx.jpg'):
    return SimpleUploadedFile(name, b'\xff\xd8\xff fake jpeg', content_type='image/jpeg')


class NormalizePhoneTests(APITestCase):
    def test_accepts_common_formats(self):
        for raw in ('01712345678', '+8801712345678', '8801712345678', '017-1234 5678'):
            self.assertEqual(normalize_bd_phone(raw), '01712345678')

    def test_rejects_invalid(self):
        for raw in ('', None, '0171234567', '01212345678', '12345678901'):
            self.assertIsNone(normalize_bd_phone(raw))


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class FieldPrescriptionFlowTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_user(
            phone='01700000001', password='pass1234', name='Admin', health_id='DH-A', roles=['admin'],
        )
        self.client.force_authenticate(self.admin)
        res = self.client.post('/api/admin/field-staff/', {
            'name': 'Karim Field', 'phone': '+880 1755-000001', 'password': 'pass1234', 'area': 'Mirpur',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.staff_id = res.data['id']
        self.staff_user = User.objects.get(phone='01755000001')

    def _upload(self, phone, **extra):
        self.client.force_authenticate(self.staff_user)
        data = {'phone': phone, 'consent_given': 'true', 'images': [_image('p1.jpg'), _image('p2.jpg')], **extra}
        return self.client.post('/api/field/prescriptions/', data, format='multipart')

    def _register(self, phone):
        self.client.force_authenticate(None)
        res = self.client.post('/api/auth/register/', {'phone': phone, 'password': 'pass1234', 'name': 'Rahim'}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        return User.objects.get(phone=normalize_bd_phone(phone))

    def _make_doctor(self):
        return User.objects.create_user(
            phone='01766000001', password='pass1234', name='Dr', health_id='DH-D', roles=['doctor'],
        )

    def test_unregistered_number_stays_hidden_until_signup(self):
        res = self._upload('01812345678', patient_name='Rahim', age='40', gender='Male')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['status'], 'unclaimed')
        self.assertEqual(len(res.data['images']), 2)

        # Signing up with a differently formatted copy of the same number links it.
        user = self._register('+8801812345678')
        rx = FieldPrescription.objects.get()
        self.assertEqual(rx.status, 'claimed')
        self.assertEqual(rx.patient.user, user)

        self.client.force_authenticate(user)
        res = self.client.get('/api/patient/field-prescriptions/')
        self.assertEqual(len(res.data), 1)

        doctor = self._make_doctor()
        self.client.force_authenticate(doctor)
        res = self.client.get(f'/api/doctor/patients/{rx.patient.id}/field-prescriptions/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

        # The signed image link works without auth.
        self.client.force_authenticate(None)
        url = res.data[0]['images'][0]['file_url']
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_existing_account_is_linked_on_upload(self):
        user = self._register('01812345678')
        res = self._upload('01812345678')
        self.assertEqual(res.data['status'], 'claimed')
        self.assertEqual(FieldPrescription.objects.get().patient.user, user)

    def test_doctor_cannot_see_private_patient(self):
        user = self._register('01812345678')
        self._upload('01812345678')
        Patient.objects.filter(user=user).update(is_private=True)
        self.client.force_authenticate(self._make_doctor())
        res = self.client.get(f'/api/doctor/patients/{user.patient_profile.id}/field-prescriptions/')
        self.assertEqual(res.status_code, 404)

    def test_retry_with_same_client_id_does_not_duplicate(self):
        cid = str(uuid.uuid4())
        self.assertEqual(self._upload('01812345678', client_id=cid).status_code, 201)
        self.assertEqual(self._upload('01812345678', client_id=cid).status_code, 200)
        self.assertEqual(FieldPrescription.objects.count(), 1)

    def test_upload_validation(self):
        self.assertEqual(self._upload('12345').status_code, 400)
        self.assertEqual(self._upload('01812345678', consent_given='false').status_code, 400)
        self.client.force_authenticate(self.staff_user)
        res = self.client.post('/api/field/prescriptions/', {
            'phone': '01812345678', 'consent_given': 'true',
            'images': [SimpleUploadedFile('x.exe', b'MZ', content_type='application/x-msdownload')],
        }, format='multipart')
        self.assertEqual(res.status_code, 400)

    def test_dispute_then_admin_corrects_phone(self):
        wrong = self._register('01812345678')
        right = User.objects.create_user(
            phone='01912345678', password='pass1234', name='Real', health_id='DH-R', roles=['patient'],
        )
        Patient.objects.create(user=right)
        self._upload('01812345678')
        rx = FieldPrescription.objects.get()

        self.client.force_authenticate(wrong)
        res = self.client.post(f'/api/patient/field-prescriptions/{rx.id}/dispute/', {'reason': 'Not mine'}, format='json')
        self.assertEqual(res.status_code, 204)
        rx.refresh_from_db()
        self.assertEqual((rx.status, rx.patient), ('disputed', None))

        self.client.force_authenticate(self.admin)
        res = self.client.patch(f'/api/admin/field-prescriptions/{rx.id}/', {'phone': '01912345678'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        rx.refresh_from_db()
        self.assertEqual((rx.status, rx.patient.user), ('claimed', right))

    def test_inactive_staff_cannot_upload_or_log_in(self):
        self.client.force_authenticate(self.admin)
        self.client.patch(f'/api/admin/field-staff/{self.staff_id}/', {'status': 'Inactive'}, format='json')
        self.staff_user.refresh_from_db()
        self.assertEqual(self._upload('01812345678').status_code, 403)
        self.client.force_authenticate(None)
        res = self.client.post('/api/auth/login/', {'identifier': '01755000001', 'password': 'pass1234'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_field_staff_and_patients_cannot_use_admin_endpoints(self):
        self.client.force_authenticate(self.staff_user)
        self.assertEqual(self.client.get('/api/admin/field-prescriptions/').status_code, 403)
        self.assertEqual(self.client.get('/api/patient/field-prescriptions/').status_code, 403)
