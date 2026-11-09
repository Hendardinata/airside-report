import os
import unittest
import json
from app import create_app
from app.services.notification_service import create_notification, get_notifications, clear_notifications

class TestDhNotificationUiSuite(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret'
        self.client = self.app.test_client()

    def test_css_and_template_standards_in_gm_dashboard(self):
        """Memverifikasi bahwa gm_dashboard.html memiliki seluruh styling standar UI/UX notifikasi sesuai dashboard_staff"""
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'templates', 'gm_dashboard.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. Card container & width standar
        self.assertIn('.notif-dropdown-card', content)
        self.assertIn('width: 440px;', content)
        self.assertIn('max-width: min(440px, 94vw);', content)

        # 2. Header alignment, responsive wrapping, no truncation bug
        self.assertIn('.notif-dropdown-header', content)
        self.assertIn('flex-wrap: wrap;', content)
        self.assertIn('min-width: 170px;', content)
        self.assertIn('@media (max-width: 440px)', content)
        self.assertIn('.notif-hdr-actions', content)

        # Pastikan tidak ada white-space: nowrap pada notif-hdr-title yang memotong judul
        self.assertIn('.notif-hdr-title {', content)
        idx_title = content.find('.notif-hdr-title {')
        title_block = content[idx_title:idx_title+250]
        self.assertNotIn('white-space: nowrap;', title_block)
        self.assertNotIn('overflow: hidden;', title_block)

        # 3. Padding content agar timestamp tidak bertabrakan dengan tombol hapus (del btn)
        self.assertIn('padding-right: 1.6rem;', content)
        self.assertIn('.notif-item-del-btn', content)

        # 4. Standardisasi 5 status notifikasi
        expected_classes = [
            'icon-box-revisi', 'icon-box-approved', 'icon-box-pending', 'icon-box-rejected', 'icon-box-info',
            'pill-notif-revisi', 'pill-notif-approved', 'pill-notif-pending', 'pill-notif-rejected', 'pill-notif-info'
        ]
        for cls in expected_classes:
            self.assertIn(cls, content, f"Class {cls} harus terdefinisi di stylesheet gm_dashboard")

        # 5. Footer styling proporsional & status indicator dot
        self.assertIn('.notif-dropdown-footer', content)
        self.assertIn('.notif-ftr-status', content)
        self.assertIn('.status-indicator-dot', content)

        # 6. JavaScript status mapping mencakup 5 status
        self.assertIn("typeLower === 'revisi'", content)
        self.assertIn("typeLower === 'approved'", content)
        self.assertIn("typeLower === 'rejected'", content)
        self.assertIn("typeLower === 'pending'", content)
        self.assertIn("Perlu Review", content)
        self.assertIn("Telah Disetujui", content)
        self.assertIn("Ditolak", content)
        self.assertIn("Sedang Direvisi", content)
        self.assertIn("Informasi", content)

    def test_css_standards_in_staff_dashboard(self):
        """Memverifikasi bahwa dashboard_staff tetap memiliki kelas status lengkap tanpa regresi"""
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'templates', 'staff_dashboard.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('.notif-dropdown-card', content)
        self.assertIn('width: 440px;', content)
        self.assertIn('icon-box-rejected', content)
        self.assertIn('pill-notif-rejected', content)
        self.assertIn('.notif-ftr-status', content)

    def test_dh_notification_api_flow(self):
        """Memverifikasi fungsi API notifikasi DH (fetch, mark-read, mark-all, clear)"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'dh_lop'
            sess['role'] = 'dh'
            sess['airport'] = 'LOP'
            sess['_csrf_token'] = 'test-csrf-token'

        headers = {'X-CSRFToken': 'test-csrf-token'}

        from app.models.config_store import get_active_month
        from app.services.staging_service import save_report_to_staging
        active_m = get_active_month('LOP') or '2026-10'

        # Buat dummy report di staging agar pending notif valid
        save_report_to_staging(
            airport_code='LOP',
            form_data={'TANGGAL': f'{active_m}-15', 'STATUS': 'SUBMITTED'},
            user_name='Petugas Staff',
            report_id=f'TEST-{active_m}-001',
            user_username='staff_lop'
        )

        # Buat dummy notifikasi untuk role dh sesuai active_month
        create_notification(
            airport_code='LOP',
            recipient_role='dh',
            notif_type='pending',
            title='Laporan Airside Baru',
            message='Petugas telah mengirimkan Laporan Harian untuk direview.',
            report_id=f'TEST-{active_m}-001',
            tanggal=f'{active_m}-15'
        )

        create_notification(
            airport_code='LOP',
            recipient_role='dh',
            notif_type='rejected',
            title='Laporan Ditolak',
            message='Laporan dibatalkan.',
            report_id=f'TEST-{active_m}-002',
            tanggal=f'{active_m}-16'
        )

        # 1. Fetch notifications
        res = self.client.get('/gm/api/notifications')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        notifs = data.get('notifications', [])
        self.assertTrue(any(n.get('report_id') == f'TEST-{active_m}-001' for n in notifs))

        test_notif = next(n for n in notifs if n.get('report_id') == f'TEST-{active_m}-001')
        notif_id = test_notif['id']

        # 2. Mark single as read
        res_read = self.client.post('/gm/api/notifications/mark-read', json={'notif_id': notif_id, 'is_read': True}, headers=headers)
        self.assertEqual(res_read.status_code, 200)

        # 3. Mark all as read
        res_all = self.client.post('/gm/api/notifications/mark-read', json={'mark_all': True}, headers=headers)
        self.assertEqual(res_all.status_code, 200)

        # 4. Clear single notif
        res_del = self.client.post('/gm/api/notifications/clear', json={'notif_id': notif_id}, headers=headers)
        self.assertEqual(res_del.status_code, 200)

if __name__ == '__main__':
    unittest.main()
