/**
 * input-validator.js
 * Sistem validasi input dinamis komprehensif berdasarkan tipe data pertanyaan Form Schema.
 * Menegakkan aturan ketat untuk tipe Number/Angka:
 * - Hanya mengizinkan karakter numerik (0–9)
 * - Mencegah huruf, teks, simbol, 'e', '+', '-', '.' (kecuali diizinkan konfigurasi desimal/negatif)
 * - Melindungi input via keyboard, copy-paste, drag-and-drop, dan virtual keyboard mobile
 * - Menyediakan umpan balik visual non-intrusif (micro-hint & subtle pulse)
 */

(function () {
    'use strict';

    // Tooltip singleton untuk visual feedback saat karakter nonangka diblokir
    let hintElement = null;
    let hintTimeout = null;

    function getOrCreateHintElement() {
        if (!hintElement) {
            hintElement = document.createElement('div');
            hintElement.className = 'number-input-micro-hint';
            hintElement.setAttribute('role', 'alert');
            hintElement.setAttribute('aria-live', 'polite');
            document.body.appendChild(hintElement);
        }
        return hintElement;
    }

    function showInvalidFeedback(input, message) {
        if (!input) return;

        // 1. Subtle shake / pulse effect pada input
        input.classList.remove('input-invalid-pulse');
        // Force reflow
        void input.offsetWidth;
        input.classList.add('input-invalid-pulse');

        setTimeout(() => {
            if (input) input.classList.remove('input-invalid-pulse');
        }, 350);

        // 2. Floating micro-tooltip di dekat input (menggunakan position: fixed agar presisi di dalam modal/viewport)
        try {
            const hint = getOrCreateHintElement();
            hint.textContent = message || 'Input tidak valid. Field ini hanya menerima angka.';
            
            const rect = input.getBoundingClientRect();
            let topPos = rect.bottom + 6;
            if (topPos + 32 > window.innerHeight && rect.top > 40) {
                topPos = Math.max(10, rect.top - 34);
            }
            const leftPos = Math.max(12, Math.min(rect.left, window.innerWidth - 260));

            hint.style.position = 'fixed';
            hint.style.top = `${topPos}px`;
            hint.style.left = `${leftPos}px`;
            hint.style.zIndex = '999999';
            hint.classList.add('show');

            if (hintTimeout) clearTimeout(hintTimeout);
            hintTimeout = setTimeout(() => {
                hint.classList.remove('show');
            }, 1800);
        } catch (e) {
            // Abaikan jika DOM tidak mendukung
        }
    }

    /**
     * Memeriksa apakah suatu elemen merupakan input bertipe Number
     */
    function isNumberInput(el) {
        if (!el || el.tagName !== 'INPUT') return false;
        
        // Pengecualian field non-data
        if (el.type === 'hidden' || el.type === 'file' || el.type === 'radio' || el.type === 'checkbox') {
            return false;
        }

        // Jika secara eksplisit dideklarasikan sebagai tipe non-number
        const dataType = el.getAttribute('data-type');
        if (dataType === 'text' || dataType === 'date') return false;
        if (dataType === 'number' || dataType === 'decimal' || dataType === 'integer') return true;

        const name = el.name;
        // 1. Cek pemetaan dari metadata Admin schema global (Single Source of Truth)
        if (name && window.ACTIVE_FIELD_DEFS && window.ACTIVE_FIELD_DEFS[name]) {
            const t = window.ACTIVE_FIELD_DEFS[name].type;
            if (t === 'number' || t === 'decimal' || t === 'integer') return true;
            if (t === 'text' || t === 'textarea' || t === 'select' || t === 'date') return false;
        }

        if (name && window.schemaFieldTypes && window.schemaFieldTypes[name]) {
            const t = window.schemaFieldTypes[name];
            if (t === 'number' || t === 'decimal' || t === 'integer') return true;
            if (t === 'text' || t === 'textarea' || t === 'select' || t === 'date') return false;
        }

        if (el.classList.contains('field-number-input')) return true;
        if (el.classList.contains('num-input')) return true;
        if (el.type === 'number') return true;

        if (name && window.ACTIVE_SCHEMA && window.ACTIVE_SCHEMA.steps) {
            // Lookup lazy di schema
            for (let step of window.ACTIVE_SCHEMA.steps) {
                for (let sec of (step.sections || [])) {
                    for (let f of (sec.fields || [])) {
                        if (f.name === name) {
                            return f.type === 'number' || f.type === 'decimal' || f.type === 'integer';
                        }
                    }
                }
            }
        }

        return false;
    }

    /**
     * Mengambil konfigurasi validasi angka untuk input tertentu
     */
    function getNumberConfig(input) {
        let allowDecimal = input.getAttribute('data-allow-decimal') === 'true';
        let allowNegative = input.getAttribute('data-allow-negative') === 'true';
        let minAttr = input.getAttribute('min');
        let maxAttr = input.getAttribute('max');

        // Sinkronisasi dengan schema Admin global jika atribut belum terpasang
        const name = input ? input.name : null;
        if (name) {
            let fDef = null;
            if (window.ACTIVE_FIELD_DEFS && window.ACTIVE_FIELD_DEFS[name]) {
                fDef = window.ACTIVE_FIELD_DEFS[name];
            } else if (window.ACTIVE_SCHEMA && window.ACTIVE_SCHEMA.steps) {
                for (let step of window.ACTIVE_SCHEMA.steps) {
                    for (let sec of (step.sections || [])) {
                        for (let f of (sec.fields || [])) {
                            if (f.name === name) {
                                fDef = f;
                                break;
                            }
                        }
                        if (fDef) break;
                    }
                    if (fDef) break;
                }
            }

            if (fDef) {
                if (fDef.allow_decimal || fDef.type === 'decimal') {
                    allowDecimal = true;
                }
                if (fDef.allow_negative) {
                    allowNegative = true;
                }
                if ((minAttr === null || minAttr === '') && fDef.min !== null && fDef.min !== undefined && fDef.min !== '') {
                    minAttr = fDef.min;
                }
                if ((maxAttr === null || maxAttr === '') && fDef.max !== null && fDef.max !== undefined && fDef.max !== '') {
                    maxAttr = fDef.max;
                }
            }
        }

        const min = (minAttr !== null && minAttr !== '') ? parseFloat(minAttr) : null;
        const max = (maxAttr !== null && maxAttr !== '') ? parseFloat(maxAttr) : null;

        return {
            allowDecimal,
            allowNegative,
            min,
            max
        };
    }

    /**
     * Sanitasi string teks menjadi representasi angka yang sah
     */
    function sanitizeNumericString(text, allowDecimal, allowNegative) {
        if (text === null || text === undefined) return '';
        let s = String(text).trim();

        // Bersihkan tanda kutip formula Google Sheets
        if (s.startsWith("'")) s = s.slice(1).trim();

        if (!allowDecimal && !allowNegative) {
            // Murni angka bulat 0-9
            return s.replace(/[^0-9]/g, '');
        }

        let isNegative = false;
        if (allowNegative && s.startsWith('-')) {
            isNegative = true;
            s = s.slice(1);
        }

        // Hapus karakter negatif di posisi lain
        s = s.replace(/-/g, '');

        if (allowDecimal) {
            // Ganti koma dengan titik untuk normalisasi, simpan pemisah pertama saja
            let hasDot = false;
            let result = '';
            for (let i = 0; i < s.length; i++) {
                const ch = s[i];
                if (ch >= '0' && ch <= '9') {
                    result += ch;
                } else if ((ch === '.' || ch === ',') && !hasDot) {
                    result += '.';
                    hasDot = true;
                }
            }
            return (isNegative && result) ? `-${result}` : result;
        } else {
            const digits = s.replace(/[^0-9]/g, '');
            return (isNegative && digits) ? `-${digits}` : digits;
        }
    }

    /**
     * Menyisipkan teks pada posisi kursor pengguna saat ini
     */
    function insertTextAtCursor(input, text) {
        if (!input) return;
        const start = input.selectionStart !== null ? input.selectionStart : input.value.length;
        const end = input.selectionEnd !== null ? input.selectionEnd : input.value.length;
        const val = input.value || '';
        const newVal = val.slice(0, start) + text + val.slice(end);
        
        input.value = newVal;
        const newCursor = start + text.length;
        try {
            if (input.setSelectionRange) {
                input.setSelectionRange(newCursor, newCursor);
            }
        } catch (e) {}

        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // =========================================================================
    // EVENT HANDLERS
    // =========================================================================

    /**
     * 1. KEYDOWN: Mencegah pengetikan huruf, simbol, 'e', '+', '-', '.' sejak awal
     */
    function onKeyDown(e) {
        const input = e.target;
        if (!isNumberInput(input)) return;

        // Izinkan tombol kontrol, navigasi, dan kombinasi shortcut keyboard
        if (
            e.key === 'Backspace' ||
            e.key === 'Delete' ||
            e.key === 'Tab' ||
            e.key === 'Escape' ||
            e.key === 'Enter' ||
            e.key === 'ArrowLeft' ||
            e.key === 'ArrowRight' ||
            e.key === 'ArrowUp' ||
            e.key === 'ArrowDown' ||
            e.key === 'Home' ||
            e.key === 'End' ||
            e.key === 'PageUp' ||
            e.key === 'PageDown' ||
            e.ctrlKey ||
            e.metaKey ||
            e.altKey
        ) {
            return;
        }

        const config = getNumberConfig(input);

        // Angka 0-9: Selalu diizinkan
        if (/^[0-9]$/.test(e.key)) {
            return;
        }

        // Tanda Desimal (. atau ,): Hanya jika diizinkan konfigurasi & belum ada tanda desimal
        if (config.allowDecimal && (e.key === '.' || e.key === ',')) {
            const currentVal = input.value || '';
            if (!currentVal.includes('.') && !currentVal.includes(',')) {
                return;
            } else {
                e.preventDefault();
                showInvalidFeedback(input, 'Hanya boleh ada 1 tanda desimal');
                return;
            }
        }

        // Tanda Negatif (-): Hanya jika diizinkan, kursor di indeks 0, dan belum ada minus
        if (config.allowNegative && e.key === '-') {
            const selStart = input.selectionStart || 0;
            const currentVal = input.value || '';
            if (selStart === 0 && !currentVal.includes('-')) {
                return;
            } else {
                e.preventDefault();
                showInvalidFeedback(input, 'Tanda minus hanya boleh di awal angka');
                return;
            }
        }

        // SEMUA KARAKTER LAIN DIBLOKIR TOTAL (Huruf, spasi, simbol, e, E, +, *)
        e.preventDefault();
        
        let hintMsg = 'Input tidak valid. Field ini hanya menerima angka.';
        if (config.allowDecimal && config.allowNegative) {
            hintMsg = 'Input tidak valid. Hanya angka, titik desimal, atau minus (-) yang diperbolehkan.';
        } else if (config.allowDecimal) {
            hintMsg = 'Input tidak valid. Field ini hanya menerima angka desimal (. atau ,).';
        } else if (config.allowNegative) {
            hintMsg = 'Input tidak valid. Field ini hanya menerima angka dan tanda minus (-).';
        }
        showInvalidFeedback(input, hintMsg);
    }

    /**
     * 2. BEFOREINPUT: Intersepsi level peramban modern & mobile IME
     */
    function onBeforeInput(e) {
        const input = e.target;
        if (!isNumberInput(input)) return;
        if (!e.data) return;

        const config = getNumberConfig(input);

        if (!config.allowDecimal && !config.allowNegative) {
            if (/[^0-9]/.test(e.data)) {
                e.preventDefault();
                showInvalidFeedback(input, 'Input tidak valid. Field ini hanya menerima angka.');
            }
        } else {
            // Cek apakah data yang akan disisipkan mengandung karakter ilegal
            const allowedRegex = (config.allowDecimal && config.allowNegative) ? /^[0-9.,-]+$/ :
                                 (config.allowDecimal ? /^[0-9.,]+$/ :
                                 (config.allowNegative ? /^[0-9-]+$/ : /^[0-9]+$/));
            if (!allowedRegex.test(e.data)) {
                e.preventDefault();
                showInvalidFeedback(input, 'Input tidak valid. Karakter tidak sesuai dengan format angka ini.');
            }
        }
    }

    /**
     * 3. PASTE: Mencegah dan membersihkan penempelan teks nonangka
     */
    function onPaste(e) {
        const input = e.target;
        if (!isNumberInput(input)) return;

        e.preventDefault();
        const clipboard = e.clipboardData || window.clipboardData;
        const pastedText = clipboard ? clipboard.getData('text') : '';

        if (!pastedText) return;

        const config = getNumberConfig(input);
        const cleaned = sanitizeNumericString(pastedText, config.allowDecimal, config.allowNegative);

        if (!cleaned) {
            showInvalidFeedback(input, 'Input tidak valid. Field ini hanya menerima angka.');
            return;
        }

        if (pastedText.trim() !== cleaned.trim()) {
            showInvalidFeedback(input, 'Input tidak valid. Karakter nonangka otomatis dibersihkan.');
        }

        insertTextAtCursor(input, cleaned);
    }

    /**
     * 4. DROP: Mencegah dan membersihkan teks drag-and-drop nonangka
     */
    function onDrop(e) {
        const input = e.target;
        if (!isNumberInput(input)) return;

        e.preventDefault();
        const transfer = e.dataTransfer;
        const droppedText = transfer ? transfer.getData('text') : '';

        if (!droppedText) return;

        const config = getNumberConfig(input);
        const cleaned = sanitizeNumericString(droppedText, config.allowDecimal, config.allowNegative);

        if (!cleaned) {
            showInvalidFeedback(input, 'Input tidak valid. Field ini hanya menerima angka.');
            return;
        }

        insertTextAtCursor(input, cleaned);
    }

    /**
     * 5. INPUT: Safety net real-time untuk virtual keyboard mobile & autofill
     */
    function onInput(e) {
        const input = e.target;
        if (!isNumberInput(input)) return;

        const config = getNumberConfig(input);
        const raw = input.value || '';
        const cleaned = sanitizeNumericString(raw, config.allowDecimal, config.allowNegative);

        if (raw !== cleaned) {
            const sel = input.selectionStart;
            input.value = cleaned;
            try {
                if (sel !== null) {
                    const newPos = Math.min(sel, cleaned.length);
                    input.setSelectionRange(newPos, newPos);
                }
            } catch (err) {}
            showInvalidFeedback(input, 'Input tidak valid. Karakter nonangka otomatis dibersihkan.');
        }
    }

    /**
     * 6. BLUR: Pembersihan akhir (misal tanda minus tunggal atau titik desimal di ujung)
     */
    function onBlur(e) {
        const input = e.target;
        if (!isNumberInput(input)) return;

        let val = (input.value || '').trim();
        if (val === '-' || val === '.' || val === ',') {
            input.value = '';
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        } else if (val.endsWith('.')) {
            input.value = val.slice(0, -1);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    // =========================================================================
    // INJEKSI CSS RESILIENT
    // =========================================================================
    function injectValidationStyles() {
        if (document.getElementById('injourney-input-validator-styles')) return;

        const style = document.createElement('style');
        style.id = 'injourney-input-validator-styles';
        style.textContent = `
            /* Sembunyikan default spinner browser pada input type number tanpa merusak layout */
            input[type="number"].report-clean-input::-webkit-outer-spin-button,
            input[type="number"].report-clean-input::-webkit-inner-spin-button,
            input[type="number"].doc-inline-input::-webkit-outer-spin-button,
            input[type="number"].doc-inline-input::-webkit-inner-spin-button {
                -webkit-appearance: none;
                margin: 0;
            }
            input[type="number"].report-clean-input,
            input[type="number"].doc-inline-input {
                -moz-appearance: textfield;
            }

            /* Efek getar halus saat input ilegal dicegah */
            @keyframes invalidInputPulse {
                0%, 100% { transform: translateX(0); }
                20%, 60% { transform: translateX(-3px); }
                40%, 80% { transform: translateX(3px); }
            }
            .input-invalid-pulse {
                animation: invalidInputPulse 0.3s ease-in-out !important;
                border-color: #ef4444 !important;
                box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.22) !important;
            }

            /* Floating micro-hint notification */
            .number-input-micro-hint {
                position: fixed !important;
                background: #0f172a;
                color: #f8fafc;
                font-family: inherit;
                font-size: 0.73rem;
                font-weight: 600;
                padding: 0.35rem 0.75rem;
                border-radius: 7px;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28);
                pointer-events: none;
                z-index: 999999 !important;
                opacity: 0;
                transform: translateY(4px);
                transition: opacity 0.16s ease, transform 0.16s ease;
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            .number-input-micro-hint.show {
                opacity: 1;
                transform: translateY(0);
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Memindai elemen di DOM dan menerapkan atribut HTML & konfigurasi dinamis
     */
    function attachNumberAttributes(root) {
        const container = root || document;
        const inputs = container.querySelectorAll('input');

        inputs.forEach(input => {
            if (!isNumberInput(input)) return;

            // Set atribut bawaan HTML yang sesuai
            input.setAttribute('data-type', 'number');
            input.classList.add('field-number-input');

            const allowDecimal = input.getAttribute('data-allow-decimal') === 'true';
            const allowNegative = input.getAttribute('data-allow-negative') === 'true';

            input.setAttribute('inputmode', allowDecimal ? 'decimal' : 'numeric');
            
            if (allowDecimal && allowNegative) {
                input.setAttribute('pattern', '^-?\\d*([.,]\\d+)?$');
                input.setAttribute('step', 'any');
            } else if (allowDecimal) {
                input.setAttribute('pattern', '^\\d*([.,]\\d+)?$');
                input.setAttribute('step', 'any');
                if (!input.hasAttribute('min')) input.setAttribute('min', '0');
            } else if (allowNegative) {
                input.setAttribute('pattern', '^-?\\d+$');
                input.setAttribute('step', '1');
            } else {
                input.setAttribute('pattern', '[0-9]*');
                input.setAttribute('step', '1');
                if (!input.hasAttribute('min')) input.setAttribute('min', '0');
            }

            // Pastikan autocomplete tidak sembarangan mengisi teks nonangka
            if (!input.hasAttribute('autocomplete')) {
                input.setAttribute('autocomplete', 'off');
            }
        });
    }

    // Pasang Global Event Delegation (Capture Phase)
    document.addEventListener('keydown', onKeyDown, true);
    document.addEventListener('beforeinput', onBeforeInput, true);
    document.addEventListener('paste', onPaste, true);
    document.addEventListener('drop', onDrop, true);
    document.addEventListener('input', onInput, true);
    document.addEventListener('blur', onBlur, true);

    // Inisialisasi saat DOM siap
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            injectValidationStyles();
            attachNumberAttributes(document);
        });
    } else {
        injectValidationStyles();
        attachNumberAttributes(document);
    }

    // API Publik InputValidator
    window.InputValidator = {
        isNumberInput,
        getNumberConfig,
        sanitizeNumericString,
        attachNumberAttributes,
        showInvalidFeedback,
        validateValue: function (val, config) {
            config = config || {};
            const strVal = String(val === undefined || val === null ? '' : val).trim();
            if (strVal === '') {
                return { valid: true, value: '' };
            }
            const allowDecimal = !!config.allowDecimal;
            const allowNegative = !!config.allowNegative;

            if (!allowDecimal && !allowNegative) {
                const valid = /^\d+$/.test(strVal);
                return {
                    valid,
                    value: strVal,
                    error: valid ? null : 'Hanya boleh berisi angka bulat (0–9)'
                };
            }

            const norm = strVal.replace(',', '.');
            let pattern = (allowDecimal && allowNegative) ? /^-?\d+(\.\d+)?$/ :
                          (allowDecimal ? /^\d+(\.\d+)?$/ :
                          (allowNegative ? /^-?\d+$/ : /^\d+$/));
            const valid = pattern.test(norm);
            return {
                valid,
                value: strVal,
                error: valid ? null : 'Bukan format angka yang valid'
            };
        }
    };

})();

