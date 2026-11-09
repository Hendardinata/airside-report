import sys
import os
import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import create_app
from app.models.db import get_db
from app.services.notification_service import (
    create_notification, get_notifications, set_notification_read_status,
    clear_notifications, delete_single_notification
)
from app.services.staging_service import (
    save_report_to_staging, gm_request_revision, get_staging_report_by_id,
    get_staging_report_by_date, update_staging_report_by_dh, get_staging_reports
)
from app.services.gsheets_service import get_airport_sheet_calendar_data, invalidate_calendar_cache
from app.services.photo_service import save_uploaded_photos, get_photos_by_date

class ComprehensiveAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        cls.csrf = 'test_csrf_token_acceptance_tests_987654321'

    def setUp(self):
        invalidate_calendar_cache('LOP')

    # =========================================================================
    # REQUIREMENT 1: NOTIFICATION LOGIC & PERSISTENCE
    # =========================================================================
    def test_scenario_01_notification_read_status_db_persistence(self):
        """Notifikasi yang ditandai dibaca harus tersimpan permanen di database."""
        with self.app.app_context():
            n = create_notification(
                airport_code='LOP', recipient_role='staff', notif_type='info',
                title='Test 01', message='Pesan persistensi DB', recipient_username='lop_hendar'
            )
            nid = n['id']
            # Direct atomic update in SQLite
            set_notification_read_status(nid, True)
            
            # Query directly from raw SQLite to ensure persistence
            with get_db() as conn:
                row = conn.cursor().execute("SELECT is_read FROM notifications WHERE id = ?;", (nid,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row['is_read'], 1)

    def test_scenario_02_notification_read_status_idempotence(self):
        """Klik berulang pada 'Tandai Dibaca' tidak boleh mengembalikan status menjadi belum dibaca."""
        with self.app.app_context():
            n = create_notification(
                airport_code='LOP', recipient_role='staff', notif_type='info',
                title='Test 02', message='Pesan idempoten', recipient_username='lop_hendar'
            )
            nid = n['id']
            set_notification_read_status(nid, True)
            set_notification_read_status(nid, True) # click 2
            set_notification_read_status(nid, True) # click 3
            
            with get_db() as conn:
                row = conn.cursor().execute("SELECT is_read FROM notifications WHERE id = ?;", (nid,)).fetchone()
            self.assertEqual(row['is_read'], 1, "Status toggled back to unread on repeated clicks!")

    def test_scenario_03_notification_mark_read_via_staff_endpoint(self):
        """Endpoint /staff/api/notifications/mark-read harus idempoten dan mengembalikan status 200."""
        with self.client:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'lop_hendar'
                sess['role'] = 'staff'
                sess['airport'] = 'LOP'
                sess['_csrf_token'] = self.csrf

            n = create_notification(
                airport_code='LOP', recipient_role='staff', notif_type='info',
                title='Test 03 Endpoint', message='Pesan endpoint test', recipient_username='lop_hendar'
            )
            nid = n['id']

            # Post mark read with is_read = false (attempting to toggle off)
            # Backend should maintain is_read = True (idempotent mark read)
            res = self.client.post('/staff/api/notifications/mark-read', 
                json={'id': nid, 'is_read': False, 'csrf_token': self.csrf},
                headers={'X-CSRFToken': self.csrf}
            )
            self.assertEqual(res.status_code, 200)
            with get_db() as conn:
                row = conn.cursor().execute("SELECT is_read FROM notifications WHERE id = ?;", (nid,)).fetchone()
            self.assertEqual(row['is_read'], 1)

    # =========================================================================
    # REQUIREMENT 2: EDIT PROFILE POPUP & SAVING
    # =========================================================================
    def test_scenario_04_edit_profile_success_response(self):
        """Edit profil staff harus berhasil menyimpan nama dan merespons 200 JSON."""
        with self.client:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'lop_hendar'
                sess['role'] = 'staff'
                sess['airport'] = 'LOP'
                sess['_csrf_token'] = self.csrf

            res = self.client.post('/api/user/profile', 
                data={'csrf_token': self.csrf, 'name': 'Hendardinata, S.Kom'},
                headers={'X-CSRFToken': self.csrf}
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['user']['name'], 'Hendardinata, S.Kom')

    def test_scenario_05_edit_profile_invalid_password_returns_error(self):
        """Edit profil dengan password salah harus ditolak dan tidak menampilkan sukses."""
        with self.client:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'lop_hendar'
                sess['role'] = 'staff'
                sess['airport'] = 'LOP'
                sess['_csrf_token'] = self.csrf

            res = self.client.post('/api/user/profile', 
                data={
                    'csrf_token': self.csrf,
                    'current_password': 'wrong_password_xyz',
                    'new_password': 'newpassword123'
                },
                headers={'X-CSRFToken': self.csrf}
            )
            self.assertEqual(res.status_code, 400)
            data = res.get_json()
            self.assertFalse(data['success'])

    # =========================================================================
    # REQUIREMENT 3: DH KOREKSI MANDIRI DATE LOCK & VALIDATION
    # =========================================================================
    def test_scenario_06_dh_self_correction_locks_date_backend(self):
        """Backend harus menolak/mengabaikan upaya manipulasi tanggal pada koreksi mandiri DH."""
        with self.app.app_context():
            orig_rep = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
            orig_date = orig_rep['tanggal']

            # Attacker/DH tries to change TANGGAL to another date
            res = update_staging_report_by_dh(
                airport_code='LOP',
                report_id='REP-LOP-20261001',
                updated_form_data={'TANGGAL': '2026-11-20', 'RUNWAY_PCI': '92%'},
                dh_name='Department Head LOP',
                dh_username='dh_lop'
            )
            self.assertTrue(res['success'])

            # Date must remain strictly orig_date
            check_rep = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
            self.assertEqual(check_rep['tanggal'], orig_date)
            self.assertEqual(check_rep['data']['TANGGAL'], orig_date)

            # Restore status to REVISI
            gm_request_revision('LOP', 'REP-LOP-20261001', 'Perbaiki apron test.', 'Department Head LOP', 'dh_lop')

    def test_scenario_07_gm_api_edit_report_enforces_original_date(self):
        """Route /gm/api/edit-report harus mengunci field TANGGAL sesuai laporan asli."""
        with self.client:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'dh_lop'
                sess['role'] = 'dh'
                sess['airport'] = 'LOP'
                sess['_csrf_token'] = self.csrf

            res = self.client.post('/gm/api/edit-report',
                json={
                    'csrf_token': self.csrf,
                    'report_id': 'REP-LOP-20261001',
                    'form_data': {
                        'TANGGAL': '2026-12-31', # Manipulated date
                        'RUNWAY_PCI': '96%'
                    }
                },
                headers={'X-CSRFToken': self.csrf}
            )
            self.assertEqual(res.status_code, 200)
            check_rep = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
            self.assertEqual(check_rep['tanggal'], '2026-10-01', "Backend allowed date tampering via /gm/api/edit-report!")

            # Restore status to REVISI
            gm_request_revision('LOP', 'REP-LOP-20261001', 'Perbaiki apron test.', 'Department Head LOP', 'dh_lop')

    # =========================================================================
    # REQUIREMENT 4: REVISION NOTIFICATIONS IMMUNITY & DATA LOADING
    # =========================================================================
    def test_scenario_08_active_revision_notif_immune_from_clear(self):
        """Fitur 'Bersihkan' tidak boleh menghapus notifikasi revisi yang masih aktif."""
        with self.app.app_context():
            rev_notif = create_notification(
                airport_code='LOP', recipient_role='staff', notif_type='revisi',
                title='Revisi Aktif Wajib', message='Jangan hapus saya!',
                report_id='REP-LOP-20261001', tanggal='2026-10-01', recipient_username='lop_hendar'
            )
            norm_notif = create_notification(
                airport_code='LOP', recipient_role='staff', notif_type='info',
                title='Info Biasa', message='Boleh dibersihkan', recipient_username='lop_hendar'
            )

            # Staff clears notifications
            clear_notifications('lop_hendar')
            notifs = get_notifications('LOP', role='staff', username='lop_hendar')
            
            self.assertTrue(any(x['id'] == rev_notif['id'] for x in notifs), "Active revision notif was deleted by clear_notifications!")
            self.assertFalse(any(x['id'] == norm_notif['id'] for x in notifs), "Normal notif was not cleared!")

    def test_scenario_09_active_revision_notif_immune_from_single_delete(self):
        """Tombol hapus individual tidak boleh menghapus notifikasi revisi aktif."""
        with self.app.app_context():
            rev_notif = create_notification(
                airport_code='LOP', recipient_role='staff', notif_type='revisi',
                title='Revisi Tidak Boleh Dihapus', message='Tes hapus tunggal',
                report_id='REP-LOP-20261001', tanggal='2026-10-01', recipient_username='lop_hendar'
            )
            res = delete_single_notification(rev_notif['id'])
            self.assertFalse(res, "delete_single_notification allowed deleting active revision notif!")

    def test_scenario_10_calendar_data_highlights_revision_dates(self):
        """Kalender harus memuat tanggal berstatus revisi dalam staging_revision_dates."""
        with self.app.app_context():
            cal = get_airport_sheet_calendar_data('LOP')
            self.assertIn('2026-10-01', cal['staging_revision_dates'])
            self.assertIn('2026-10-01', cal['staging_revision_reports'])
            self.assertEqual(cal['staging_revision_reports']['2026-10-01']['status'], 'REVISI')

    def test_scenario_11_fetch_staging_report_by_date_contains_dh_metadata(self):
        """Endpoint fetch by date harus menyertakan nama DH, catatan DH, dan seluruh field formulir."""
        with self.client:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'lop_hendar'
                sess['role'] = 'staff'
                sess['airport'] = 'LOP'
                sess['_csrf_token'] = self.csrf

            res = self.client.get('/staff/api/staging-report-by-date/2026-10-01')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data['success'])
            rep = data['report']
            self.assertEqual(rep['report_id'], 'REP-LOP-20261001')
            self.assertEqual(rep['tanggal'], '2026-10-01')
            self.assertIsNotNone(rep.get('dh_name'))
            self.assertIsNotNone(rep.get('catatan_dh'))
            self.assertIsInstance(rep.get('data'), dict)
            self.assertIsInstance(rep.get('photos'), list)

    def test_scenario_12_submit_revised_report_preserves_id_no_duplicate(self):
        """Pengiriman laporan revisi harus memperbarui record yang sama tanpa membuat baris baru / duplikasi."""
        with self.client:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'lop_hendar'
                sess['role'] = 'staff'
                sess['airport'] = 'LOP'
                sess['_csrf_token'] = self.csrf

            initial_count = len(get_staging_reports('LOP'))

            submit_data = {
                'csrf_token': self.csrf,
                'report_id': 'REP-LOP-20261001',
                'TANGGAL': '2026-10-01',
                'KANTOR_CABANG': '1. Kantor Cabang LOP',
                'RUNWAY_PCI': '94,5%',
                'RUNWAY_KONDISI': 'Clear & Serviceable (Final Revision)',
                'APN_KONDISI': 'Clear & Serviceable'
            }
            res = self.client.post('/staff/submit', data=submit_data, headers={'X-CSRFToken': self.csrf})
            self.assertEqual(res.status_code, 200)

            # Record count in staging must be UNCHANGED (no duplicate record)
            after_count = len(get_staging_reports('LOP'))
            self.assertEqual(initial_count, after_count, "Duplicate report created on revision submission!")

            # Status must be PENDING_DH
            rep = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
            self.assertEqual(rep['status'], 'PENDING_DH')
            self.assertEqual(rep['data']['RUNWAY_KONDISI'], 'Clear & Serviceable (Final Revision)')

            # Re-request revision to preserve initial fixture
            gm_request_revision('LOP', 'REP-LOP-20261001', 'Perbaiki data apron kembali.', 'Department Head LOP', 'dh_lop')

if __name__ == '__main__':
    unittest.main()
