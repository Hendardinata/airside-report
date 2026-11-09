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

class TestAirsideFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        cls.test_csrf = 'test_csrf_token_1234567890abcdef'

    def setUp(self):
        invalidate_calendar_cache('LOP')
        try:
            gm_request_revision('LOP', 'REP-LOP-20261001', 'Perbaiki data apron kembali.', 'Department Head LOP', 'dh_lop')
        except Exception:
            pass

    def test_01_notification_atomicity_and_protection(self):
        with self.app.app_context():
            # 1. Create a revision notification for active revision report
            notif_obj = create_notification(
                airport_code='LOP',
                recipient_role='staff',
                notif_type='revisi',
                title='Perlu Revisi Laporan Unit Test',
                message='Pemeriksaan marka apron memerlukan klarifikasi detail.',
                report_id='REP-LOP-20261001',
                tanggal='2026-10-01',
                recipient_username='lop_hendar',
                sender_name='Department Head Unit Test',
                sender_username='dh_lop'
            )
            self.assertIsNotNone(notif_obj)
            notif_id = notif_obj['id'] if isinstance(notif_obj, dict) else notif_obj

            # 2. Mark read once
            set_notification_read_status(notif_id, True)
            notifs = get_notifications('LOP', role='staff', username='lop_hendar')
            target = next((x for x in notifs if x['id'] == notif_id), None)
            self.assertIsNotNone(target)
            self.assertEqual(target['is_read'], 1)

            # 3. Mark read a second time (simulate repeated clicks)
            set_notification_read_status(notif_id, True)
            notifs = get_notifications('LOP', role='staff', username='lop_hendar')
            target = next((x for x in notifs if x['id'] == notif_id), None)
            self.assertIsNotNone(target)
            self.assertEqual(target['is_read'], 1, "Status read reverted to 0 upon repeated click!")

            # 4. Create ordinary notification
            norm_obj = create_notification(
                airport_code='LOP',
                recipient_role='staff',
                notif_type='info',
                title='Pemberitahuan Sistem',
                message='Sistem berjalan normal.',
                recipient_username='lop_hendar'
            )
            norm_id = norm_obj['id'] if isinstance(norm_obj, dict) else norm_obj

            # 5. Clear notifications: ordinary deleted, active revisi PROTECTED
            clear_notifications('lop_hendar')
            notifs = get_notifications('LOP', role='staff', username='lop_hendar')
            self.assertTrue(any(x['id'] == notif_id for x in notifs), "Active revisi notif was deleted by clear_notifications!")
            self.assertFalse(any(x['id'] == norm_id for x in notifs), "Ordinary notif was not cleared!")

            # 6. Single delete on active revisi notif must fail
            del_res = delete_single_notification(notif_id)
            self.assertFalse(del_res, "delete_single_notification permitted deleting active revisi notif!")
            notifs = get_notifications('LOP', role='staff', username='lop_hendar')
            self.assertTrue(any(x['id'] == notif_id for x in notifs), "Active revisi notif was deleted by single delete!")

    def test_02_dh_self_correction_date_locked(self):
        with self.app.app_context():
            orig_rep = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
            self.assertIsNotNone(orig_rep)
            orig_date = orig_rep['tanggal']

            # DH attempts to alter date via self-correction
            res = update_staging_report_by_dh(
                airport_code='LOP',
                report_id='REP-LOP-20261001',
                updated_form_data={'TANGGAL': '2026-11-25', 'RUNWAY_PCI': '99,5%'},
                dh_name='Department Head LOP',
                dh_username='dh_lop'
            )
            self.assertTrue(res['success'])

            # Verify report date remains strictly orig_date
            updated_rep = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
            self.assertEqual(updated_rep['tanggal'], orig_date)
            self.assertEqual(updated_rep['data']['TANGGAL'], orig_date)

            # Restore status to REVISI for subsequent tests
            gm_request_revision('LOP', 'REP-LOP-20261001', 'Perbaiki data apron kembali.', 'Department Head LOP', 'dh_lop')
            invalidate_calendar_cache('LOP')

    def test_03_calendar_data_includes_revision_reports_mapping(self):
        with self.app.app_context():
            cal_data = get_airport_sheet_calendar_data('LOP')
            self.assertTrue(cal_data['success'])
            self.assertIn('staging_revision_dates', cal_data)
            self.assertIn('staging_revision_reports', cal_data)
            self.assertIn('2026-10-01', cal_data['staging_revision_dates'])
            self.assertIn('2026-10-01', cal_data['staging_revision_reports'])
            rev_info = cal_data['staging_revision_reports']['2026-10-01']
            self.assertEqual(rev_info['report_id'], 'REP-LOP-20261001')
            self.assertEqual(rev_info['status'], 'REVISI')

    def test_04_get_staging_report_by_date_endpoint(self):
        with self.client:
            # Login as staff lop_hendar
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'lop_hendar'
                sess['role'] = 'staff'
                sess['airport'] = 'LOP'
                sess['_csrf_token'] = self.test_csrf

            res = self.client.get('/staff/api/staging-report-by-date/2026-10-01')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data['success'])
            rep = data['report']
            self.assertEqual(rep['report_id'], 'REP-LOP-20261001')
            self.assertEqual(rep['tanggal'], '2026-10-01')
            self.assertIn('dh_name', rep)
            self.assertIn('catatan_dh', rep)

    def test_05_staff_submit_revised_report_preserves_id_and_updates_status(self):
        with self.client:
            # Login as staff lop_hendar
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'lop_hendar'
                sess['role'] = 'staff'
                sess['airport'] = 'LOP'
                sess['_csrf_token'] = self.test_csrf

            # Resubmit revised report
            submit_data = {
                'csrf_token': self.test_csrf,
                'report_id': 'REP-LOP-20261001',
                'TANGGAL': '2026-10-01',
                'KANTOR_CABANG': '1. Kantor Cabang LOP',
                'RUNWAY_PCI': '95,0%',
                'RUNWAY_KONDISI': 'Clear & Serviceable (Revised)',
                'APN_KONDISI': 'Clear & Serviceable'
            }
            res = self.client.post('/staff/submit', data=submit_data, headers={'X-CSRFToken': self.test_csrf})
            self.assertEqual(res.status_code, 200)
            json_res = res.get_json()
            self.assertTrue(json_res.get('success') or json_res.get('status') == 'success')
            self.assertEqual(json_res['report_id'], 'REP-LOP-20261001')

            # Verify report in staging is now PENDING_DH with NO DUPLICATE
            rep = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
            self.assertEqual(rep['status'], 'PENDING_DH')
            self.assertEqual(rep['data']['RUNWAY_KONDISI'], 'Clear & Serviceable (Revised)')

            # Re-request revision by DH to keep test state consistent
            rev_res = gm_request_revision('LOP', 'REP-LOP-20261001', 'Perbaiki data apron kembali.', 'Department Head LOP', 'dh_lop')
            self.assertTrue(rev_res['success'])
            rep_after = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
            self.assertEqual(rep_after['status'], 'REVISI')

    def test_06_profile_update_backend(self):
        with self.client:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'lop_hendar'
                sess['role'] = 'staff'
                sess['airport'] = 'LOP'
                sess['_csrf_token'] = self.test_csrf

            # Test updating profile via /api/user/profile
            res = self.client.post('/api/user/profile', data={'csrf_token': self.test_csrf, 'name': 'Hendardinata, S.Kom'}, headers={'X-CSRFToken': self.test_csrf})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['user']['name'], 'Hendardinata, S.Kom')

    def test_07_dh_koreksi_mandiri_document_layout_and_fields(self):
        # 1. Inspect gm_dashboard.html template contents
        template_path = os.path.join(os.path.dirname(__file__), 'app', 'templates', 'gm_dashboard.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            tmpl_src = f.read()

        # Check 3-column grid structure
        self.assertIn('grid-template-columns: 260px 20px 1fr;', tmpl_src)
        self.assertIn('.doc-pair-row', tmpl_src)
        self.assertIn('.doc-pair-key', tmpl_src)
        self.assertIn('.doc-pair-sep', tmpl_src)
        self.assertIn('.doc-pair-val', tmpl_src)

        # Check left alignment for values and inputs
        self.assertIn('text-align: left !important;', tmpl_src)

        # Check locked report date badge in DH Self-Edit Mode
        self.assertIn('name="TANGGAL"', tmpl_src)
        self.assertIn('readonly', tmpl_src)
        self.assertIn('Terkunci (Sesuai Laporan Asli)', tmpl_src)

        # Check responsive mobile override
        self.assertIn('flex-direction: column !important;', tmpl_src)

        # 2. Test DH self-edit submission maintains report date integrity
        with self.client:
            with self.client.session_transaction() as sess:
                sess['user_id'] = 'dh_lop'
                sess['role'] = 'gm'
                sess['airport'] = 'LOP'
                sess['_csrf_token'] = self.test_csrf

            # Test DH updating report with self-edit
            edit_data = {
                'csrf_token': self.test_csrf,
                'report_id': 'REP-LOP-20261001',
                'auto_approve': False,
                'form_data': {
                    'SAPAAN': 'Selamat Malam',
                    'TANGGAL': '2026-10-01',
                    'PENERIMA_1': 'Pak DT API',
                    'PENERIMA_2': 'Pak GH API',
                    'PENERIMA_3': 'Deputy Regional Airport Facility, Equipment, & Technology Readiness Region II',
                    'PENERIMA_4': 'Pak DH Regional II',
                    'KANTOR_CABANG': '1. Kantor Cabang LOP',
                    'RUNWAY_KONDISI': 'Clear & Serviceable'
                }
            }
            res = self.client.post('/gm/api/edit-report', json=edit_data, headers={'X-CSRFToken': self.test_csrf})
            self.assertEqual(res.status_code, 200)
            res_data = res.get_json()
            self.assertTrue(res_data.get('success'))

            # Verify saved report
            rep = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
            self.assertEqual(rep['tanggal'], '2026-10-01')
            self.assertEqual(rep['data']['SAPAAN'], 'Selamat Malam')
            self.assertEqual(rep['data']['PENERIMA_3'], 'Deputy Regional Airport Facility, Equipment, & Technology Readiness Region II')

            # Restore REVISI status for REP-LOP-20261001 to keep test suite idempotent
            gm_request_revision('LOP', 'REP-LOP-20261001', 'Perbaiki data apron kembali.', 'Department Head LOP', 'dh_lop')

    def test_06_revisi_notification_badge_and_button_behavior(self):
        """
        Menguji pemisahan status dibaca dengan status penyelesaian revisi:
        1. Tombol 'Sudah Dibaca' ditiadakan pada notifikasi PERLU REVISI.
        2. Badge angka lonceng tetap menampilkan jumlah revisi aktif meskipun notifikasi dibuka/dibaca.
        3. Badge baru berkurang saat laporan diperbaiki/disubmit ulang (status tidak lagi REVISI).
        4. Notifikasi biasa tetap memiliki toggle status dibaca dan mark_all_as_read.
        """
        with self.app.app_context():
            # Pastikan REP-LOP-20261001 berstatus REVISI
            gm_request_revision('LOP', 'REP-LOP-20261001', 'Perbaiki data apron kembali.', 'Department Head LOP', 'dh_lop')

            # 1. Login sebagai petugas staff LOP
            with self.client:
                with self.client.session_transaction() as sess:
                    sess['user_id'] = 'lop_hendar'
                    sess['role'] = 'staff'
                    sess['airport'] = 'LOP'
                    sess['_csrf_token'] = self.test_csrf

                # 2. Ambil notifikasi via API
                res = self.client.get('/staff/api/notifications')
                self.assertEqual(res.status_code, 200)
                data = res.get_json()
                self.assertTrue(data.get('success'))
                self.assertGreaterEqual(data.get('active_revisi_count', 0), 1)
                self.assertGreaterEqual(data.get('unread_count', 0), 1)
                self.assertGreaterEqual(data.get('badge_count', 0), 1)

                # Cari notifikasi revisi untuk REP-LOP-20261001
                revisi_notif = next((n for n in data.get('notifications', []) if n.get('report_id') == 'REP-LOP-20261001' and n.get('notif_type') == 'revisi'), None)
                self.assertIsNotNone(revisi_notif, "Notifikasi revisi harus ditemukan")
                self.assertEqual(revisi_notif['notif_type'], 'revisi')

                # 3. Uji bahwa 'Baca Semua' TIDAK menghapus atau menurunkan badge revisi
                res_mark = self.client.post('/staff/api/notifications/mark-read', json={'mark_all': True}, headers={'X-CSRFToken': self.test_csrf})
                self.assertEqual(res_mark.status_code, 200)

                res_after_mark = self.client.get('/staff/api/notifications')
                data_after = res_after_mark.get_json()
                # active_revisi_count dan badge_count harus tetap >= 1!
                self.assertGreaterEqual(data_after.get('active_revisi_count', 0), 1, "Badge revisi tidak boleh hilang hanya karena Baca Semua")
                self.assertGreaterEqual(data_after.get('badge_count', 0), 1)

                # 4. Verifikasi template staff_dashboard.html
                tmpl_path = os.path.join(BASE_DIR, 'app', 'templates', 'staff_dashboard.html')
                with open(tmpl_path, 'r', encoding='utf-8') as f:
                    tmpl_html = f.read()

                # Cek bahwa pada nType === 'revisi', readStatusBtn tidak di-render
                self.assertIn("if (nType !== 'revisi')", tmpl_html)
                self.assertIn("readStatusBtn = isUnread", tmpl_html)
                self.assertIn("Perbaiki Laporan Sekarang", tmpl_html)
                self.assertIn("revisi-active", tmpl_html)

                # 5. Simulasi penyelesaian revisi: submit ulang laporan
                # Simpan report baru / hasil perbaikan dengan status PENDING_DH
                staging_res = save_report_to_staging(
                    airport_code='LOP',
                    form_data={
                        'SAPAAN': 'Selamat Malam',
                        'TANGGAL': '2026-10-01',
                        'PENERIMA_1': 'Pak DT API',
                        'PENERIMA_2': 'Pak GH API',
                        'KANTOR_CABANG': '1. Kantor Cabang LOP',
                        'RUNWAY_KONDISI': 'Serviceable'
                    },
                    user_name='Hendar Petugas',
                    user_username='lop_hendar',
                    report_id='REP-LOP-20261001'
                )
                self.assertEqual(staging_res.get('status'), 'PENDING_DH')

                # Cek bahwa notifikasi API sekarang tidak lagi menghitung REP-LOP-20261001 sebagai active_revisi
                res_after_submit = self.client.get('/staff/api/notifications')
                data_submit = res_after_submit.get_json()
                active_rids = [n.get('report_id') for n in data_submit.get('notifications', []) if n.get('notif_type') == 'revisi']
                self.assertNotIn('REP-LOP-20261001', active_rids)

                # Kembalikan status REVISI untuk idempotensi test suite
                gm_request_revision('LOP', 'REP-LOP-20261001', 'Perbaiki data apron kembali.', 'Department Head LOP', 'dh_lop')

    def test_07_global_document_layout_across_various_report_types(self):
        """
        Pengujian komprehensif struktur dan spacing seluruh dokumen Koreksi Mandiri DH:
        1. Dokumen dengan sedikit informasi (minimal).
        2. Dokumen dengan banyak penerima (Penerima 1 - 4).
        3. Dokumen dengan teks panjang (multiline kerusakan / catatan).
        4. Dokumen dengan banyak bagian (A s/d E).
        5. Dokumen dengan field opsional yang kosong.
        6. Dokumen dengan field terkunci/read-only (Tanggal Laporan).
        """
        with self.app.app_context():
            tmpl_path = os.path.join(BASE_DIR, 'app', 'templates', 'gm_dashboard.html')
            with open(tmpl_path, 'r', encoding='utf-8') as f:
                tmpl_html = f.read()

            # Verifikasi aturan CSS global level komponen
            self.assertIn('.doc-pair-row', tmpl_html)
            self.assertIn('grid-template-columns: 260px 20px 1fr;', tmpl_html)
            self.assertIn('padding: 11px 0;', tmpl_html)
            self.assertIn('text-align: left !important;', tmpl_html)
            self.assertIn('#dhSelfEditForm', tmpl_html)
            self.assertIn('.doc-lock-field-wrap', tmpl_html)
            self.assertIn('.doc-inline-input', tmpl_html)
            self.assertIn('textarea.doc-inline-input', tmpl_html)

            # Verifikasi API /gm/api/report/<report_id> mengembalikan data lengkap untuk koreksi mandiri
            with self.client:
                with self.client.session_transaction() as sess:
                    sess['user_id'] = 'dh_lop'
                    sess['role'] = 'gm'
                    sess['airport'] = 'LOP'
                    sess['_csrf_token'] = self.test_csrf

                res = self.client.get('/gm/api/report/REP-LOP-20261001')
                self.assertEqual(res.status_code, 200)
                rep_data = res.get_json()
                self.assertTrue(rep_data.get('success'))
                rep = rep_data.get('report')
                self.assertIsNotNone(rep)

                # 1. Dokumen Sedikit Informasi: Verifikasi field dasar ada
                self.assertIn('tanggal', rep)
                self.assertEqual(rep['tanggal'], '2026-10-01')

                # 2. Dokumen Banyak Penerima: Verifikasi field Penerima 1-4 didukung
                d = rep.get('data', {})
                self.assertIn('PENERIMA_1', d)
                self.assertIn('PENERIMA_2', d)

                # 3. Dokumen Teks Panjang: Update dengan teks panjang di catatan
                long_text = "Lendutan pada apron bay 01 sepanjang 15 meter dengan kedalaman 3 cm.\nPerlu koordinasi dengan tim teknis fasilitas sisi udara."
                save_res = self.client.post('/gm/api/edit-report', json={
                    'csrf_token': self.test_csrf,
                    'report_id': 'REP-LOP-20261001',
                    'auto_approve': False,
                    'form_data': {
                        'SAPAAN': 'Selamat Malam',
                        'TANGGAL': '2026-10-01',
                        'PENERIMA_1': 'Pak DT API',
                        'PENERIMA_2': 'Pak GH API',
                        'PENERIMA_3': 'Deputy Regional Airport Facility, Equipment, & Technology Readiness Region II',
                        'PENERIMA_4': 'Pak DH Regional II',
                        'KANTOR_CABANG': '1. Kantor Cabang LOP',
                        'RUNWAY_KONDISI': 'Clear & Serviceable',
                        'CATATAN_1': long_text
                    }
                }, headers={'X-CSRFToken': self.test_csrf})
                self.assertEqual(save_res.status_code, 200)
                self.assertTrue(save_res.get_json().get('success'))

                # 4. Verifikasi data tersimpan
                updated_rep = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
                self.assertEqual(updated_rep['data']['CATATAN_1'], long_text)
                self.assertEqual(updated_rep['data']['PENERIMA_4'], 'Pak DH Regional II')

                # 5. Dokumen Field Opsional Kosong: Kosongkan field opsional (PENERIMA_4, dll)
                empty_opt_res = self.client.post('/gm/api/edit-report', json={
                    'csrf_token': self.test_csrf,
                    'report_id': 'REP-LOP-20261001',
                    'auto_approve': False,
                    'form_data': {
                        'SAPAAN': 'Selamat Malam',
                        'TANGGAL': '2026-10-01',
                        'PENERIMA_1': 'Pak DT API',
                        'PENERIMA_2': 'Pak GH API',
                        'PENERIMA_3': '',
                        'PENERIMA_4': '',
                        'KANTOR_CABANG': '1. Kantor Cabang LOP',
                        'RUNWAY_KONDISI': 'Clear & Serviceable'
                    }
                }, headers={'X-CSRFToken': self.test_csrf})
                self.assertEqual(empty_opt_res.status_code, 200)
                self.assertTrue(empty_opt_res.get_json().get('success'))

                # 6. Dokumen Field Terkunci: Tanggal harus tetap 2026-10-01
                rep_locked = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
                self.assertEqual(rep_locked['tanggal'], '2026-10-01')

                # Restore status revisi untuk idempotensi
                gm_request_revision('LOP', 'REP-LOP-20261001', 'Perbaiki data apron kembali.', 'Department Head LOP', 'dh_lop')

if __name__ == '__main__':
    unittest.main()
