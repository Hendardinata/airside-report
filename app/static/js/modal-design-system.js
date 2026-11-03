/**
 * ==============================================================================
 * INJOURNEY AIRPORTS - STANDARDIZED MODAL & UI DIALOG DESIGN SYSTEM JS
 * ==============================================================================
 * Shared Reusable Modal Component & SweetAlert2 Configuration Engine.
 * 
 * Provides:
 *   - InJourneyModal.confirm({ title, message, ... })
 *   - InJourneyModal.alert({ title, message, icon, ... })
 *   - InJourneyModal.success(title, message)
 *   - InJourneyModal.warning(title, message)
 *   - InJourneyModal.error(title, message)
 *   - InJourneyModal.actionSheet({ title, message, actions: [...] })
 *   - InJourneyModal.loading(title, message)
 *   - Universal Escape key & backdrop click handler for .clean-modal-overlay
 * ==============================================================================
 */

(function (window) {
    'use strict';

    // Global Modal Namespace
    const InJourneyModal = {};

    /**
     * Standard Confirmation Dialog (2 Buttons: Primary Confirm + Secondary Cancel)
     * @param {Object} opts - Options
     * @param {string} opts.title - Modal title
     * @param {string} opts.html - Body HTML or text
     * @param {string} [opts.icon='question'] - 'warning', 'success', 'error', 'info', 'question'
     * @param {string} [opts.confirmText='Konfirmasi'] - Confirm button text
     * @param {string} [opts.cancelText='Batal'] - Cancel button text
     * @param {boolean} [opts.isDanger=false] - If true, confirm button becomes red/danger
     * @returns {Promise<SweetAlertResult>}
     */
    InJourneyModal.confirm = function (opts) {
        opts = opts || {};
        if (typeof Swal === 'undefined') {
            const ok = window.confirm(opts.title ? `${opts.title}\n\n${opts.html || ''}` : (opts.html || ''));
            return Promise.resolve({ isConfirmed: ok, isDismissed: !ok });
        }

        return Swal.fire({
            title: opts.title || 'Konfirmasi Tindakan',
            html: opts.html || opts.message || '',
            icon: opts.icon || 'question',
            showCancelButton: true,
            showCloseButton: true,
            confirmButtonText: opts.confirmText || 'Ya, Lanjutkan',
            cancelButtonText: opts.cancelText || 'Batal',
            reverseButtons: false,
            focusCancel: false,
            customClass: {
                popup: opts.isDanger ? 'swal-danger-confirm' : 'swal-standard-confirm'
            }
        });
    };

    /**
     * Standard Alert Dialog (1 Button: Symmetrical Confirm Button)
     * @param {Object} opts - Options
     * @param {string} opts.title - Modal title
     * @param {string} opts.html - Body HTML or text
     * @param {string} [opts.icon='info'] - 'warning', 'success', 'error', 'info'
     * @param {string} [opts.confirmText='Mengerti'] - Confirm button text
     * @returns {Promise<SweetAlertResult>}
     */
    InJourneyModal.alert = function (opts) {
        opts = opts || {};
        if (typeof Swal === 'undefined') {
            window.alert(opts.title ? `${opts.title}\n\n${opts.html || ''}` : (opts.html || ''));
            return Promise.resolve({ isConfirmed: true });
        }

        return Swal.fire({
            title: opts.title || 'Informasi',
            html: opts.html || opts.message || '',
            icon: opts.icon || 'info',
            showCancelButton: false,
            showCloseButton: true,
            confirmButtonText: opts.confirmText || 'Mengerti',
            customClass: {
                popup: 'swal-standard-alert'
            }
        });
    };

    // Quick Alert Shorthands
    InJourneyModal.success = function (title, html, confirmText) {
        return InJourneyModal.alert({ title: title || 'Berhasil', html: html, icon: 'success', confirmText: confirmText || 'Selesai' });
    };

    InJourneyModal.warning = function (title, html, confirmText) {
        return InJourneyModal.alert({ title: title || 'Perhatian', html: html, icon: 'warning', confirmText: confirmText || 'Mengerti' });
    };

    InJourneyModal.error = function (title, html, confirmText) {
        return InJourneyModal.alert({ title: title || 'Terjadi Kesalahan', html: html, icon: 'error', confirmText: confirmText || 'Tutup' });
    };

    InJourneyModal.info = function (title, html, confirmText) {
        return InJourneyModal.alert({ title: title || 'Informasi', html: html, icon: 'info', confirmText: confirmText || 'Mengerti' });
    };

    /**
     * Standard Action Sheet (Multi-action operational sheet, exactly as in Design Reference)
     * @param {Object} opts - Options
     * @param {string} opts.title - Sheet title
     * @param {string} opts.subtitle - Helper prompt
     * @param {string} opts.html - Body message
     * @param {string} [opts.icon='warning'] - Badge icon
     * @param {string} opts.primaryText - Primary button text (InJourney Cyan)
     * @param {string} [opts.secondaryText] - Secondary button text (Blush Pink / Deny)
     * @param {string} [opts.neutralText] - Neutral button text (White Slate Outline / Cancel)
     * @returns {Promise<SweetAlertResult>}
     */
    InJourneyModal.actionSheet = function (opts) {
        opts = opts || {};
        if (typeof Swal === 'undefined') return Promise.reject(new Error('Swal is not defined'));

        let bodyContent = opts.html || '';
        if (opts.subtitle) {
            bodyContent += `<div style="font-size: 0.84rem; color: #94a3b8; margin-top: 0.35rem; margin-bottom: 0.65rem;">${opts.subtitle}</div>`;
        }

        return Swal.fire({
            title: opts.title || 'Pilih Tindakan',
            html: bodyContent,
            icon: opts.icon || 'warning',
            showCloseButton: true,
            showConfirmButton: !!opts.primaryText,
            showDenyButton: !!opts.secondaryText,
            showCancelButton: !!opts.neutralText,
            confirmButtonText: opts.primaryText || 'Lanjutkan',
            denyButtonText: opts.secondaryText || '',
            cancelButtonText: opts.neutralText || 'Batal',
            customClass: {
                popup: 'swal-branch-action-sheet',
                actions: 'swal-branch-actions'
            }
        });
    };

    /**
     * Standard Loading Spinner with InJourney Branding
     * @param {string} [title='Memproses Data...']
     * @param {string} [message='Mohon tunggu beberapa saat.']
     */
    InJourneyModal.loading = function (title, message) {
        if (typeof Swal === 'undefined') return;
        Swal.fire({
            title: title || 'Memproses Data...',
            html: `<div style="font-size: 0.9rem; color: #64748b; margin-top: 0.5rem;">${message || 'Mohon tunggu beberapa saat.'}</div>`,
            allowOutsideClick: false,
            allowEscapeKey: false,
            showConfirmButton: false,
            showCloseButton: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });
    };

    InJourneyModal.close = function () {
        if (typeof Swal !== 'undefined' && Swal.isVisible()) {
            Swal.close();
        }
    };

    // ==============================================================================
    // Universal Keyboard & Backdrop Listeners for Custom Overlay Modals
    // ==============================================================================
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            // Find any open custom modal overlay
            const openOverlays = document.querySelectorAll('.clean-modal-overlay, .custom-modal-backdrop, .modal-overlay');
            openOverlays.forEach(function (overlay) {
                if (overlay.style.display !== 'none' && getComputedStyle(overlay).display !== 'none') {
                    // Check if there is a close button or handler
                    const closeBtn = overlay.querySelector('.modal-close-btn, .btn-outline-action, .btn-rev-cancel');
                    if (closeBtn) {
                        closeBtn.click();
                    } else {
                        overlay.style.display = 'none';
                    }
                }
            });
        }
    });

    // Auto backdrop click closer for clean modals
    document.addEventListener('DOMContentLoaded', function () {
        const overlays = document.querySelectorAll('.clean-modal-overlay');
        overlays.forEach(function (overlay) {
            overlay.addEventListener('click', function (e) {
                if (e.target === overlay) {
                    const closeBtn = overlay.querySelector('.modal-close-btn');
                    if (closeBtn) {
                        closeBtn.click();
                    } else {
                        overlay.style.display = 'none';
                    }
                }
            });
        });
    });

    // Export to global window
    window.InJourneyModal = InJourneyModal;

})(window);
