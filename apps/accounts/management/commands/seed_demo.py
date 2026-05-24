"""
Idempotent seed command for DigiHealth demo data.
Can be run multiple times safely.
"""
import random
from datetime import date, timedelta, datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


BENGALI_MONTHS = ['জানু', 'ফেব্রু', 'মার্চ', 'এপ্রিল', 'মে', 'জুন',
                  'জুলাই', 'আগস্ট', 'সেপ্টে', 'অক্টো', 'নভে', 'ডিসে']


def make_health_id(suffix):
    """Create a deterministic health ID for demo data."""
    return f'DH-{str(suffix).zfill(12)}'


def get_or_create_user(phone, password, name, health_id, roles, email=None):
    from apps.accounts.models import User
    user, created = User.objects.get_or_create(phone=phone, defaults={
        'name': name,
        'health_id': health_id,
        'roles': roles,
        'email': email,
    })
    if created:
        user.set_password(password)
        user.save()
    return user, created


class Command(BaseCommand):
    help = 'Seed demo data for DigiHealth (idempotent)'

    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data...')
        with transaction.atomic():
            self._seed()
        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully!'))

    def _seed(self):
        from apps.accounts.models import User, ActivityEvent
        from apps.hospitals.models import Hospital, Owner
        from apps.staff.models import Manager, Pathologist, Doctor, HospitalDoctor, Nurse
        from apps.patients.models import Patient, HealthMetric, MedicalReport, ReportAccessLog
        from apps.clinical.models import Bed, LabTest, Appointment, Admission, LabOrder, LabResult
        from apps.finance.models import MonthlyFinancial

        # ── Hospitals ──────────────────────────────────────────────────────────
        h1, _ = Hospital.objects.get_or_create(
            name_en='Dhaka Medical College Hospital',
            defaults={
                'name_bn': 'ঢাকা মেডিকেল কলেজ হাসপাতাল',
                'type': 'General',
                'status': 'Active',
                'address': 'Zahir Raihan Road, Dhaka-1000',
                'phone': '02-55165088',
                'email': 'info@dmch.gov.bd',
                'beds': 2600,
                'established': date(1946, 1, 1),
            }
        )
        h2, _ = Hospital.objects.get_or_create(
            name_en='Chittagong General Hospital',
            defaults={
                'name_bn': 'চট্টগ্রাম জেনারেল হাসপাতাল',
                'type': 'General',
                'status': 'Active',
                'address': 'Chittagong Medical College Road, Chittagong',
                'phone': '031-619999',
                'email': 'info@cgh.gov.bd',
                'beds': 1000,
                'established': date(1957, 1, 1),
            }
        )
        hospitals = [h1, h2]
        self.stdout.write(f'  Hospitals: {h1.name_en}, {h2.name_en}')

        # ── Admin user ─────────────────────────────────────────────────────────
        admin_user, created = get_or_create_user(
            phone='01700000001',
            password='demo1234',
            name='System Admin',
            health_id='DH-000000000001',
            roles=['admin'],
            email='admin@digihealth.bd',
        )
        self.stdout.write(f'  Admin: {admin_user.phone} ({"created" if created else "exists"})')

        # ── Owner users ────────────────────────────────────────────────────────
        owner_phones = ['01711111111', '01711111112']
        owner_names = ['Dr. Aminul Islam', 'Dr. Rezaul Karim']
        owners = []
        for i, (hospital, phone, name) in enumerate(zip(hospitals, owner_phones, owner_names)):
            user, created = get_or_create_user(
                phone=phone,
                password='demo1234',
                name=name,
                health_id=make_health_id(100 + i),
                roles=['owner'],
                email=f'owner{i+1}@digihealth.bd',
            )
            owner_profile, _ = Owner.objects.get_or_create(
                user=user,
                hospital=hospital,
                defaults={'is_primary': True, 'status': 'Active'},
            )
            owners.append(owner_profile)
        self.stdout.write(f'  Owners: {len(owners)} created/found')

        # ── Managers ───────────────────────────────────────────────────────────
        manager_data = [
            # (hospital, phone, name, email)
            (h1, '01722000001', 'Kamal Hossain', 'kamal@dmch.bd'),
            (h1, '01722000002', 'Rina Begum', 'rina@dmch.bd'),
            (h2, '01722000003', 'Shahidul Islam', 'shahidul@cgh.bd'),
            (h2, '01722000004', 'Farida Khanam', 'farida@cgh.bd'),
        ]
        managers = []
        for idx, (hospital, phone, name, email) in enumerate(manager_data):
            user, created = get_or_create_user(
                phone=phone,
                password='demo1234',
                name=name,
                health_id=make_health_id(200 + idx),
                roles=['manager'],
                email=email,
            )
            mgr, _ = Manager.objects.get_or_create(
                user=user,
                hospital=hospital,
                defaults={'status': 'Active'},
            )
            managers.append(mgr)
        self.stdout.write(f'  Managers: {len(managers)} created/found')

        # ── Pathologists ───────────────────────────────────────────────────────
        path_data = [
            (h1, '01733000001', 'Dr. Nasrin Akter', 'nasrin@dmch.bd', 'Clinical Pathology'),
            (h1, '01733000002', 'Dr. Imran Khan', 'imran@dmch.bd', 'Hematology'),
            (h2, '01733000003', 'Dr. Sabina Yasmin', 'sabina@cgh.bd', 'Biochemistry'),
            (h2, '01733000004', 'Dr. Monir Hossain', 'monir@cgh.bd', 'Microbiology'),
        ]
        pathologists = []
        for idx, (hospital, phone, name, email, spec) in enumerate(path_data):
            user, created = get_or_create_user(
                phone=phone,
                password='demo1234',
                name=name,
                health_id=make_health_id(300 + idx),
                roles=['pathologist'],
                email=email,
            )
            path, _ = Pathologist.objects.get_or_create(
                user=user,
                hospital=hospital,
                defaults={'specialization': spec, 'status': 'Active'},
            )
            pathologists.append(path)
        self.stdout.write(f'  Pathologists: {len(pathologists)} created/found')

        # ── Doctors (registry) + per-hospital attachments ─────────────────────
        doctor_data = [
            (h1, 'Dr. Rafiqul Islam', 'Cardiology', '01744000001', 'Sat-Thu 9am-1pm', 'BMDC-A-1001'),
            (h1, 'Dr. Salma Khatun', 'Gynecology', '01744000002', 'Sat-Thu 2pm-6pm', 'BMDC-A-1002'),
            (h1, 'Dr. Zahir Ahmed', 'Orthopedics', '01744000003', 'Sun-Wed 10am-2pm', 'BMDC-A-1003'),
            (h2, 'Dr. Nargis Parvin', 'Pediatrics', '01744000004', 'Sat-Thu 9am-1pm', 'BMDC-A-1004'),
            (h2, 'Dr. Hasibul Haque', 'Neurology', '01744000005', 'Sat-Thu 3pm-7pm', 'BMDC-A-1005'),
            (h2, 'Dr. Tahmina Begum', 'Dermatology', '01744000006', 'Sun-Wed 11am-3pm', 'BMDC-A-1006'),
        ]
        h1_doctors, h2_doctors = [], []
        for hospital, name, spec, phone, schedule, bmdc in doctor_data:
            doc, _ = Doctor.objects.get_or_create(
                phone=phone,
                defaults={'name': name, 'bmdc_registration_no': bmdc, 'specialization': spec},
            )
            HospitalDoctor.objects.get_or_create(
                hospital=hospital,
                doctor=doc,
                defaults={'schedule': schedule, 'status': 'Active'},
            )
            (h1_doctors if hospital == h1 else h2_doctors).append(doc)
        total = len(h1_doctors) + len(h2_doctors)
        self.stdout.write(f'  Doctors: {total} attached across {2} hospitals')

        # ── Nurses ─────────────────────────────────────────────────────────────
        nurse_data = [
            (h1, 'Fatema Begum', '01755000001', 'General Ward'),
            (h1, 'Roksana Akter', '01755000002', 'ICU'),
            (h1, 'Mitu Khanam', '01755000003', 'Pediatrics Ward'),
            (h2, 'Sultana Razia', '01755000004', 'General Ward'),
            (h2, 'Minara Begum', '01755000005', 'Emergency'),
            (h2, 'Lipi Akter', '01755000006', 'Surgery Ward'),
        ]
        nurses = []
        for hospital, name, phone, ward in nurse_data:
            nurse, _ = Nurse.objects.get_or_create(
                hospital=hospital,
                phone=phone,
                defaults={'name': name, 'ward': ward, 'status': 'Active'},
            )
            nurses.append(nurse)
        h1_nurses = [n for n in nurses if n.hospital == h1]
        h2_nurses = [n for n in nurses if n.hospital == h2]
        self.stdout.write(f'  Nurses: {len(nurses)} created/found')

        # ── Beds ───────────────────────────────────────────────────────────────
        bed_data = [
            (h1, 'B-101', 'General Ward', 'General', 500),
            (h1, 'B-102', 'General Ward', 'General', 500),
            (h1, 'ICU-01', 'ICU', 'ICU', 5000),
            (h1, 'P-201', 'Private Wing', 'Private', 3000),
            (h1, 'C-301', 'Cabin Block', 'Cabin', 2000),
            (h2, 'B-101', 'General Ward', 'General', 400),
            (h2, 'B-102', 'General Ward', 'General', 400),
            (h2, 'ICU-01', 'ICU', 'ICU', 4500),
            (h2, 'P-201', 'Private Wing', 'Private', 2500),
            (h2, 'C-301', 'Cabin Block', 'Cabin', 1800),
        ]
        beds = []
        for hospital, number, ward, btype, price in bed_data:
            bed, _ = Bed.objects.get_or_create(
                hospital=hospital,
                number=number,
                defaults={
                    'ward': ward,
                    'type': btype,
                    'price_per_day': price,
                    'status': 'Available',
                }
            )
            beds.append(bed)
        h1_beds = [b for b in beds if b.hospital == h1]
        h2_beds = [b for b in beds if b.hospital == h2]
        self.stdout.write(f'  Beds: {len(beds)} created/found')

        # ── Lab Tests ──────────────────────────────────────────────────────────
        test_data = [
            (h1, 'Complete Blood Count (CBC)', 500, '24 hours'),
            (h1, 'Blood Glucose (Fasting)', 200, '4 hours'),
            (h1, 'HbA1c', 800, '48 hours'),
            (h2, 'Urine Routine Examination', 300, '6 hours'),
            (h2, 'Lipid Profile', 1200, '24 hours'),
            (h2, 'Liver Function Test', 1500, '24 hours'),
        ]
        lab_tests = []
        for hospital, name, price, duration in test_data:
            test, _ = LabTest.objects.get_or_create(
                hospital=hospital,
                name=name,
                defaults={'price': price, 'duration': duration, 'available': True},
            )
            lab_tests.append(test)
        h1_tests = [t for t in lab_tests if t.hospital == h1]
        h2_tests = [t for t in lab_tests if t.hospital == h2]
        self.stdout.write(f'  Lab Tests: {len(lab_tests)} created/found')

        # ── Patients ───────────────────────────────────────────────────────────
        patient_data = [
            ('01799000001', 'Md. Arif Hossain', 35, 'Male', 'B+', 'Mirpur, Dhaka'),
            ('01799000002', 'Sabrina Rahman', 28, 'Female', 'A+', 'Banani, Dhaka'),
            ('01799000003', 'Jakir Hossain', 45, 'Male', 'O+', 'Chittagong'),
        ]
        patients = []
        for idx, (phone, name, age, gender, blood, address) in enumerate(patient_data):
            user, created = get_or_create_user(
                phone=phone,
                password='demo1234',
                name=name,
                health_id=make_health_id(400 + idx),
                roles=['patient'],
                email=f'patient{idx+1}@example.com',
            )
            patient, _ = Patient.objects.get_or_create(
                user=user,
                defaults={
                    'age': age,
                    'gender': gender,
                    'blood_group': blood,
                    'address': address,
                    'subscription_tier': 'Free',
                }
            )
            patients.append(patient)
        self.stdout.write(f'  Patients: {len(patients)} created/found')

        # ── Multi-role user ────────────────────────────────────────────────────
        multi_user, created = get_or_create_user(
            phone='01788000001',
            password='demo1234',
            name='Rifat Multi-Role',
            health_id=make_health_id(500),
            roles=['manager', 'pathologist', 'patient'],
            email='multi@digihealth.bd',
        )
        # Ensure manager profile
        multi_mgr, _ = Manager.objects.get_or_create(
            user=multi_user,
            hospital=h1,
            defaults={'status': 'Active'},
        )
        # Ensure pathologist profile
        multi_path, _ = Pathologist.objects.get_or_create(
            user=multi_user,
            hospital=h1,
            defaults={'specialization': 'General', 'status': 'Active'},
        )
        # Ensure patient profile
        multi_patient, _ = Patient.objects.get_or_create(
            user=multi_user,
            defaults={
                'age': 32,
                'gender': 'Male',
                'blood_group': 'AB+',
                'address': 'Gulshan, Dhaka',
                'subscription_tier': 'Premium',
            }
        )
        self.stdout.write(f'  Multi-role user: {multi_user.phone} ({"created" if created else "exists"})')

        # Multi-role user also gets demo metrics/reports so patient dashboard is populated
        patients.append(multi_patient)

        # ── Health Metrics ─────────────────────────────────────────────────────
        metric_types = ['hba1c', 'blood_pressure', 'weight']
        metric_values = {
            'hba1c': ['5.8', '6.1', '6.4', '6.0', '5.9', '6.2'],
            'blood_pressure': ['120/80', '130/85', '125/82', '118/78', '122/80', '128/84'],
            'weight': ['72', '73', '74', '72.5', '71.8', '73.2'],
        }
        for patient in patients:
            for i in range(6):
                mtype = metric_types[i % 3]
                metric_date = date.today() - timedelta(days=30 * i)
                HealthMetric.objects.get_or_create(
                    patient=patient,
                    metric_type=mtype,
                    date=metric_date,
                    defaults={'value': metric_values[mtype][i]},
                )
        self.stdout.write('  Health Metrics: seeded')

        # ── Medical Reports ────────────────────────────────────────────────────
        for patient in patients:
            for i in range(2):
                MedicalReport.objects.get_or_create(
                    patient=patient,
                    name=f'Blood Test Report {i+1}',
                    defaults={
                        'file_url': f'https://example.com/reports/{patient.id}/report{i+1}.pdf',
                        'size': random.randint(50000, 500000),
                    }
                )
        self.stdout.write('  Medical Reports: seeded')

        # ── Appointments ───────────────────────────────────────────────────────
        apt_statuses = ['Pending', 'Confirmed', 'Completed', 'Pending', 'Cancelled']
        today = date.today()
        for hospital, hdoctors in [(h1, h1_doctors), (h2, h2_doctors)]:
            for i, p in enumerate(patients):
                doctor = hdoctors[i % len(hdoctors)]
                apt_date = today + timedelta(days=i - 2)
                Appointment.objects.get_or_create(
                    hospital=hospital,
                    patient=p,
                    doctor=doctor,
                    date=apt_date,
                    defaults={
                        'time': f'{9 + i}:00',
                        'reason': 'Regular checkup',
                        'status': apt_statuses[i % len(apt_statuses)],
                        'admitted': False,
                    }
                )
        self.stdout.write('  Appointments: seeded')

        # ── Admissions ─────────────────────────────────────────────────────────
        # Find a confirmed appointment to admit
        apt_to_admit = Appointment.objects.filter(
            hospital=h1, admitted=False, status='Confirmed'
        ).first()
        if apt_to_admit and not hasattr(apt_to_admit, 'admission'):
            avail_bed = Bed.objects.filter(hospital=h1, status='Available').first()
            avail_nurse = h1_nurses[0] if h1_nurses else None
            if avail_bed and avail_nurse:
                try:
                    Admission.objects.get_or_create(
                        appointment=apt_to_admit,
                        defaults={
                            'bed': avail_bed,
                            'nurse': avail_nurse,
                            'bed_price_snapshot': avail_bed.price_per_day,
                        }
                    )
                    avail_bed.status = 'Occupied'
                    avail_bed.save()
                    apt_to_admit.admitted = True
                    apt_to_admit.save()
                except Exception:
                    pass
        self.stdout.write('  Admissions: seeded')

        # ── Lab Orders ─────────────────────────────────────────────────────────
        order_statuses = ['Pending', 'Assigned', 'Completed', 'Pending']
        for hospital, htests, hpathologists in [
            (h1, h1_tests, [p for p in pathologists if p.hospital == h1]),
            (h2, h2_tests, [p for p in pathologists if p.hospital == h2]),
        ]:
            for i, patient in enumerate(patients):
                test = htests[i % len(htests)]
                doctor = h1_doctors[0] if hospital == h1 else h2_doctors[0]
                ostatus = order_statuses[i % len(order_statuses)]
                assigned_path = hpathologists[0] if hpathologists and ostatus in ('Assigned', 'Completed') else None

                order, created = LabOrder.objects.get_or_create(
                    hospital=hospital,
                    patient=patient,
                    test=test,
                    defaults={
                        'ordered_by_doctor': doctor,
                        'assigned_pathologist': assigned_path,
                        'status': ostatus,
                    }
                )

                # Create a lab result for completed orders
                if created and ostatus == 'Completed' and assigned_path:
                    try:
                        LabResult.objects.get_or_create(
                            lab_order=order,
                            defaults={
                                'findings': 'All values within normal range.',
                                'remarks': 'Normal',
                                'submitted_by': assigned_path.user,
                            }
                        )
                    except Exception:
                        pass

        self.stdout.write('  Lab Orders: seeded')

        # ── Privacy/Access Logs ────────────────────────────────────────────────
        if patients:
            patient = patients[0]
            reports = list(patient.medical_reports.all()[:2])
            accessor = admin_user
            for i, report in enumerate(reports):
                ReportAccessLog.objects.get_or_create(
                    patient=patient,
                    report=report,
                    accessor=accessor,
                    action='viewed',
                    defaults={'accessor_role': 'admin'},
                )
            if managers:
                mgr_user = managers[0].user
                if reports:
                    ReportAccessLog.objects.get_or_create(
                        patient=patient,
                        report=reports[0],
                        accessor=mgr_user,
                        action='downloaded',
                        defaults={'accessor_role': 'manager'},
                    )
        self.stdout.write('  Privacy Logs: seeded')

        # ── Financial Data ─────────────────────────────────────────────────────
        for hospital in hospitals:
            base_rev = 1200000 if hospital == h1 else 800000
            base_exp = 700000 if hospital == h1 else 500000
            for month_num in range(1, 13):
                month_str = f'2025-{str(month_num).zfill(2)}'
                revenue = base_rev + random.randint(-100000, 200000)
                expenses = base_exp + random.randint(-50000, 100000)
                MonthlyFinancial.objects.get_or_create(
                    hospital=hospital,
                    month=month_str,
                    defaults={
                        'revenue': revenue,
                        'expenses': expenses,
                    }
                )
        self.stdout.write('  Financial Data: seeded')

        # ── Activity Events ────────────────────────────────────────────────────
        events_to_create = [
            ('hospital_created', f'Hospital created: {h1.name_en}'),
            ('hospital_created', f'Hospital created: {h2.name_en}'),
            ('manager_created', f'Manager added: Kamal Hossain at {h1.name_en}'),
            ('patient_registered', 'New patient registered: Md. Arif Hossain'),
            ('lab_order_created', 'Lab order placed for Sabrina Rahman'),
        ]
        if not ActivityEvent.objects.exists():
            for event_type, desc in events_to_create:
                ActivityEvent.objects.create(type=event_type, description=desc)
        self.stdout.write('  Activity Events: seeded')

        self.stdout.write('')
        self.stdout.write('Demo login credentials:')
        self.stdout.write('  admin:       01700000001 / demo1234')
        self.stdout.write('  owner:       01711111111 / demo1234')
        self.stdout.write('  manager:     01722000001 / demo1234')
        self.stdout.write('  pathologist: 01733000001 / demo1234')
        self.stdout.write('  patient:     01799000001 / demo1234')
        self.stdout.write('  multiRole:   01788000001 / demo1234')
