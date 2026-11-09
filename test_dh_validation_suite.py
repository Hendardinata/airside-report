import os
import sys
import unittest
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app import create_app
from app.models.db import get_db
from app.models.config_store import load_schema, save_schema
from app.services.validator_service import validate_form_data, validate_numeric_value, get_schema_field_definitions
from app.services.staging_service import save_report_to_staging, get_staging_report_by_id

class TestDhValidationIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
        cls.test_csrf = 'test_csrf_token_dh_validation_123456789'

        # Backup schema asli agar idempotent
        cls.original_schema = load_schema()

    @classmethod
    def tearDownClass(cls):
        # Restore schema asli setelah seluruh pengujian selesai
        if cls.original_schema:
            save_schema(cls.original_schema)

    def setUp(self):
        # Siapkan user session sebagai Department Head
        with self.client.session_transaction() as sess:
            sess['user_id'] = 'dh_lop'
            sess['role'] = 'gm'
            sess['airport'] = 'LOP'
            sess['_csrf_token'] = self.test_csrf

        # Pastikan ada laporan uji di staging
        save_report_to_staging(
            airport_code='LOP',
            form_data={
                'SAPAAN': 'Selamat Malam',
                'TANGGAL': '2026-10-01',
                'PENERIMA_1': 'Pak DT API',
                'PENERIMA_2': 'Pak GH API',
                'KANTOR_CABANG': '1. Kantor Cabang LOP',
                'RUNWAY_KONDISI': 'Serviceable',
                'RUNWAY_PCI': '95%',
                'RUNWAY_TITIK_RUSAK': '0',
                'RUNWAY_TITIK_DIPERBAIKI': '0',
                'RUNWAY_TITIK_BELUM': '0',
                'RUNWAY_TITIK_BERULANG': '0',
                'RUNWAY_JENIS_DIPERBAIKI': 'Pothole di bay 01'
            },
            user_name='Hendar Petugas',
            user_username='lop_hendar',
            report_id='REP-LOP-20261001'
        )

    # =========================================================================
    # SKENARIO A — FIELD NUMBER
    # =========================================================================
    def test_scenario_a_field_number_validation(self):
        """
        Field bertipe Number (misal: RUNWAY_TITIK_RUSAK):
        - Angka valid: diterima
        - Karakter alfabet (misal: 'CSCS'): ditolak dengan pesan error
        - Simbol atau teks nonangka: ditolak
        """
        schema = load_schema()
        field_defs = get_schema_field_definitions(schema)
        titik_rusak_def = field_defs.get('RUNWAY_TITIK_RUSAK')

        self.assertIsNotNone(titik_rusak_def)
        self.assertEqual(titik_rusak_def['type'], 'number')

        # 1. Input angka valid
        ok, res = validate_numeric_value('0', titik_rusak_def)
        self.assertTrue(ok)
        self.assertEqual(res, '0')

        ok, res = validate_numeric_value('15', titik_rusak_def)
        self.assertTrue(ok)
        self.assertEqual(res, '15')

        # 2. Input karakter alfabet 'CSCS' harus ditolak
        ok, err = validate_numeric_value('CSCS', titik_rusak_def)
        self.assertFalse(ok)
        self.assertIn("hanya boleh berisi angka bulat numerik", err)

        # 3. Input paste atau campuran teks nonangka harus ditolak
        ok, err = validate_numeric_value('12 titik', titik_rusak_def)
        self.assertFalse(ok)
        self.assertIn("hanya boleh berisi angka bulat numerik", err)

    # =========================================================================
    # SKENARIO B — FIELD TEXT
    # =========================================================================
    def test_scenario_b_field_text_validation(self):
        """
        Field bertipe Text (misal: RUNWAY_JENIS_DIPERBAIKI, PENERIMA_1):
        - Menerima teks, huruf, angka, dan kombinasi deskripsi bebas
        - Tidak dibatasi menjadi angka saja
        """
        schema = load_schema()
        field_defs = get_schema_field_definitions(schema)
        jenis_def = field_defs.get('RUNWAY_JENIS_DIPERBAIKI')

        self.assertIsNotNone(jenis_def)
        self.assertEqual(jenis_def['type'], 'text')

        # Form data dengan teks bebas harus lolos validasi
        form_payload = {
            'RUNWAY_JENIS_DIPERBAIKI': '1 titik deflection pada Runway 08, 27 titik spalling',
            'PENERIMA_1': 'Pak DT API (Direktur Teknik)'
        }
        is_valid, err, cleaned = validate_form_data(form_payload, schema)
        self.assertTrue(is_valid)
        self.assertEqual(cleaned['RUNWAY_JENIS_DIPERBAIKI'], '1 titik deflection pada Runway 08, 27 titik spalling')

    # =========================================================================
    # SKENARIO C — FIELD DECIMAL
    # =========================================================================
    def test_scenario_c_field_decimal_validation(self):
        """
        Field yang mendukung desimal (allow_decimal: True atau type: 'decimal'):
        - Menerima angka desimal dengan format titik (12.5) maupun koma (12,5)
        - Menolak huruf atau karakter alfabet
        """
        test_decimal_def = {
            'name': 'TEST_DECIMAL_FIELD',
            'label': 'Test Persentase Desimal',
            'type': 'decimal',
            'allow_decimal': True,
            'required': True
        }

        # 1. Angka desimal titik (12.5) -> Valid
        ok, res = validate_numeric_value('12.5', test_decimal_def)
        self.assertTrue(ok)
        self.assertEqual(res, '12.5')

        # 2. Angka desimal koma (12,5) -> Valid
        ok, res = validate_numeric_value('12,5', test_decimal_def)
        self.assertTrue(ok)

        # 3. Huruf alfabet ('CSCS') -> Ditolak
        ok, err = validate_numeric_value('CSCS', test_decimal_def)
        self.assertFalse(ok)
        self.assertIn("harus berupa angka valid", err)

    # =========================================================================
    # SKENARIO D — PERUBAHAN KONFIGURASI ADMIN
    # =========================================================================
    def test_scenario_d_dynamic_admin_configuration_change(self):
        """
        Admin mengubah tipe field:
        - API /gm/api/schema harus langsung mengembalikan konfigurasi terbaru
        - Backend validation harus mengikuti aturan konfigurasi terbaru
        """
        # 1. Tes API /gm/api/schema dapat diakses oleh DH
        res = self.client.get('/gm/api/schema')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('steps', data.get('data', {}))

        # 2. Simulasikan Admin mengubah field RUNWAY_PCI dari text menjadi number dengan allow_decimal=True
        modified_schema = json.loads(json.dumps(self.original_schema))
        found = False
        for step in modified_schema.get('steps', []):
            for sec in step.get('sections', []):
                for f in sec.get('fields', []):
                    if f.get('name') == 'RUNWAY_PCI':
                        f['type'] = 'number'
                        f['allow_decimal'] = True
                        found = True
                        break
        self.assertTrue(found)
        save_schema(modified_schema)

        # 3. Verifikasi API /gm/api/schema langsung mengembalikan tipe number
        res_after = self.client.get('/gm/api/schema')
        self.assertEqual(res_after.status_code, 200)
        schema_after = res_after.get_json().get('data', {})
        pci_def = get_schema_field_definitions(schema_after).get('RUNWAY_PCI')
        self.assertEqual(pci_def['type'], 'number')
        self.assertTrue(pci_def['allow_decimal'])

        # 4. Verifikasi backend menolak nilai nonangka pada field yang baru diubah menjadi number
        invalid_pci_res = self.client.post('/gm/api/edit-report', json={
            'csrf_token': self.test_csrf,
            'report_id': 'REP-LOP-20261001',
            'auto_approve': False,
            'form_data': {
                'RUNWAY_PCI': 'SANGAT_BAIK_ALFABET'
            }
        }, headers={'X-CSRFToken': self.test_csrf})
        self.assertEqual(invalid_pci_res.status_code, 400)
        err_json = invalid_pci_res.get_json()
        self.assertFalse(err_json.get('success'))
        self.assertIn("Validasi Gagal", err_json.get('error'))

        # 5. Restore schema
        save_schema(self.original_schema)

    # =========================================================================
    # SKENARIO E — VALIDASI BACKEND API (/gm/api/edit-report)
    # =========================================================================
    def test_scenario_e_backend_api_direct_rejection(self):
        """
        Pengiriman request API langsung dengan nilai tidak sesuai aturan Admin:
        - Harus ditolak dengan status code HTTP 400
        - Pesan kesalahan harus informatif dan menyebutkan kolom yang bermasalah
        - Request dengan nilai valid harus berhasil diproses (HTTP 200)
        """
        # 1. Request dengan nilai 'CSCS' pada field RUNWAY_TITIK_RUSAK
        res_invalid = self.client.post('/gm/api/edit-report', json={
            'csrf_token': self.test_csrf,
            'report_id': 'REP-LOP-20261001',
            'auto_approve': False,
            'form_data': {
                'RUNWAY_TITIK_RUSAK': 'CSCS',
                'RUNWAY_KONDISI': 'Serviceable'
            }
        }, headers={'X-CSRFToken': self.test_csrf})

        self.assertEqual(res_invalid.status_code, 400)
        res_data = res_invalid.get_json()
        self.assertFalse(res_data.get('success'))
        self.assertIn("Validasi Gagal", res_data.get('error'))
        self.assertIn("Jml Titik Rusak", res_data.get('error'))
        self.assertIn("angka bulat numerik", res_data.get('error'))

        # 2. Request dengan nilai angka valid ('5') pada field RUNWAY_TITIK_RUSAK
        res_valid = self.client.post('/gm/api/edit-report', json={
            'csrf_token': self.test_csrf,
            'report_id': 'REP-LOP-20261001',
            'auto_approve': False,
            'form_data': {
                'RUNWAY_TITIK_RUSAK': '5',
                'RUNWAY_KONDISI': 'Serviceable'
            }
        }, headers={'X-CSRFToken': self.test_csrf})

        self.assertEqual(res_valid.status_code, 200)
        valid_json = res_valid.get_json()
        self.assertTrue(valid_json.get('success'))

        # 3. Verifikasi data tersimpan di staging dengan benar
        rep_updated = get_staging_report_by_id('LOP', 'REP-LOP-20261001')
        self.assertEqual(rep_updated['data']['RUNWAY_TITIK_RUSAK'], '5')

    # =========================================================================
    # VERIFIKASI INTEGRASI TEMPLATE & SCRIPT FRONTEND
    # =========================================================================
    def test_frontend_template_and_script_integration(self):
        """
        Memastikan komponen frontend terhubung:
        - gm_dashboard.html memuat window.ACTIVE_FIELD_DEFS, applySchemaAttributesToForm,
          validateDhFormInputs, dan showDhValidationErrorModal
        - input-validator.js mendeteksi field dinamis dan menggunakan pesan alert standar
        """
        tmpl_path = os.path.join(BASE_DIR, 'app', 'templates', 'gm_dashboard.html')
        with open(tmpl_path, 'r', encoding='utf-8') as f:
            gm_html = f.read()

        self.assertIn('window.ACTIVE_SCHEMA', gm_html)
        self.assertIn('window.getSchemaFieldMap', gm_html)
        self.assertIn('window.ACTIVE_FIELD_DEFS', gm_html)
        self.assertIn('applySchemaAttributesToForm', gm_html)
        self.assertIn('validateDhFormInputs', gm_html)
        self.assertIn('showDhValidationErrorModal', gm_html)
        self.assertIn('swal-corp-popup', gm_html)
        self.assertIn('icon-warning-corp', gm_html)
        self.assertIn('/gm/api/schema', gm_html)

        val_script_path = os.path.join(BASE_DIR, 'app', 'static', 'js', 'input-validator.js')
        with open(val_script_path, 'r', encoding='utf-8') as f:
            val_js = f.read()

        self.assertIn('window.ACTIVE_FIELD_DEFS', val_js)
        self.assertIn('Input tidak valid. Field ini hanya menerima angka.', val_js)
        self.assertIn('position: fixed', val_js)

if __name__ == '__main__':
    unittest.main()

