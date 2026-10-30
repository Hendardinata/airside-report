// wizard.js

function getCurrentStepNum() {
    const totalSteps = document.querySelectorAll('.wizard-step').length || 6;
    for (let i = 1; i <= totalSteps; i++) {
        const stepEl = document.getElementById(`step-${i}`);
        if (stepEl && (stepEl.style.display !== 'none' || stepEl.classList.contains('active'))) {
            return i;
        }
    }
    const activeNav = document.querySelector('.stepper-cell.step.active');
    if (activeNav && activeNav.id) {
        const num = parseInt(activeNav.id.replace('step-nav-', ''), 10);
        if (!isNaN(num)) return num;
    }
    return 1;
}

function validateStepFields(stepNum) {
    const stepEl = document.getElementById(`step-${stepNum}`);
    if (!stepEl) return true;

    // Validasi tanggal sebelum berpindah dari langkah 1 (cek tanggal kosong/duplikat/pending)
    if (stepNum === 1 && typeof validateStepDateBeforeNext === 'function') {
        if (!validateStepDateBeforeNext()) {
            return false;
        }
    }

    // Ambil seluruh input wajib (bertanda bintang merah / atribut required) pada langkah ini
    const requiredInputs = stepEl.querySelectorAll('input[required]:not([type="hidden"]), select[required], textarea[required]');
    let invalidList = [];

    requiredInputs.forEach(input => {
        let isFieldEmpty = false;
        if (input.tagName.toLowerCase() === 'select') {
            const val = input.value;
            if (!val || val === '' || input.selectedIndex <= 0 || val.startsWith('--')) {
                isFieldEmpty = true;
            }
        } else if (input.type === 'radio' || input.type === 'checkbox') {
            const name = input.name;
            const checked = stepEl.querySelectorAll(`input[name="${name}"]:checked`);
            if (checked.length === 0) {
                isFieldEmpty = true;
            }
        } else {
            const val = (input.value || '').trim();
            if (val === '') {
                isFieldEmpty = true;
            }
        }

        if (isFieldEmpty) {
            input.classList.add('field-has-error');
            if (input._flatpickr && input._flatpickr.altInput) {
                input._flatpickr.altInput.classList.add('field-has-error');
            }
            invalidList.push(input);
        } else {
            input.classList.remove('field-has-error');
            if (input._flatpickr && input._flatpickr.altInput) {
                input._flatpickr.altInput.classList.remove('field-has-error');
            }
        }
    });

    if (invalidList.length > 0) {
        const firstInvalid = invalidList[0];
        const targetFocus = (firstInvalid._flatpickr && firstInvalid._flatpickr.altInput) ? firstInvalid._flatpickr.altInput : firstInvalid;

        // Ambil nama label untuk pesan error yang informatif
        const row = firstInvalid.closest('.report-table-row');
        const labelEl = row ? row.querySelector('label') : null;
        let labelText = '';
        if (labelEl) {
            labelText = labelEl.innerText.replace(/\*/g, '').replace(/\(opsional\)/gi, '').trim();
        }
        if (!labelText) {
            labelText = firstInvalid.placeholder || firstInvalid.name || 'Kolom Wajib';
        }

        // Fokuskan kursor dan scroll ke field yang kosong
        targetFocus.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => {
            targetFocus.focus();
        }, 300);

        if (typeof Swal !== 'undefined') {
            Swal.fire({
                customClass: {
                    popup: 'swal-corp-popup',
                    confirmButton: 'swal-corp-btn-primary',
                    actions: 'swal-corp-actions-bar'
                },
                buttonsStyling: false,
                html: `
                    <div class="swal-corp-icon-tile icon-warning-corp">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                    </div>
                    <h3 class="swal-corp-title">Kolom Wajib Belum Diisi</h3>
                    <div class="swal-corp-sub">
                        <i class="fa-solid fa-circle-exclamation text-danger me-1"></i> Langkah ${stepNum} Memerlukan Kelengkapan Data
                    </div>
                    <p style="font-size:0.88rem; color:#475569; margin:0 0 1rem 0; line-height: 1.5;">
                        Harap lengkapi semua formulir yang bertanda bintang merah (<span style="color:#ef4444; font-weight:bold;">*</span>) sebelum melanjutkan ke langkah berikutnya.
                    </p>
                    <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:10px; padding:0.65rem 0.9rem; color:#991b1b; font-size:0.86rem; text-align:left; display:flex; align-items:center; gap:0.5rem;">
                        <i class="fa-solid fa-arrow-right text-danger"></i>
                        <span>Kolom kosong: <b>${labelText}</b></span>
                    </div>
                `,
                confirmButtonText: '<i class="fa-solid fa-pen-to-square me-1"></i> Lengkapi Sekarang'
            });
        }

        return false;
    }

    return true;
}

function goToStepDirect(step) {
    // Sembunyikan semua langkah
    document.querySelectorAll('.wizard-step').forEach(el => {
        el.style.display = 'none';
        el.classList.remove('active');
    });
    document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
    
    // Tampilkan langkah target
    const targetStep = document.getElementById(`step-${step}`);
    const targetNav = document.getElementById(`step-nav-${step}`);
    if (targetStep) {
        targetStep.style.display = 'block';
        targetStep.classList.add('active');
    }
    if (targetNav) {
        targetNav.classList.add('active');
        try {
            targetNav.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        } catch(e) {}
    }

    // Scroll halus ke atas kartu wizard
    const formCard = document.querySelector('.form-workspace-card') || document.querySelector('.form-main-card') || document.getElementById('reportWizard');
    if (formCard) {
        formCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    if (typeof updateLiveWaPreview === 'function') {
        updateLiveWaPreview();
    }
}

function nextStep(step) {
    const currentStep = getCurrentStepNum();

    // Jika mencoba maju ke langkah berikutnya (misal 1 -> 2 atau klik stepper langkah depan)
    if (step > currentStep) {
        // Validasi berurutan dari currentStep sampai step - 1
        for (let s = currentStep; s < step; s++) {
            if (!validateStepFields(s)) {
                if (s !== currentStep) {
                    goToStepDirect(s);
                }
                return false;
            }
        }
    }

    // Jika valid atau kembali ke langkah sebelumnya (prev), izinkan berpindah
    goToStepDirect(step);
    return true;
}

function prevStep(step) {
    goToStepDirect(step);
}

// Real-time listener: hilangkan highlight error saat user mulai mengetik / memilih opsi
document.addEventListener('DOMContentLoaded', function() {
    const wizardForm = document.getElementById('reportWizard');
    if (wizardForm) {
        const clearErr = function(target) {
            if (target && target.classList.contains('field-has-error')) {
                const val = (target.value || '').trim();
                const isSelect = target.tagName.toLowerCase() === 'select';
                const isEmptySelect = isSelect && (!val || val.startsWith('--'));
                if (val !== '' && !isEmptySelect) {
                    target.classList.remove('field-has-error');
                    if (target._flatpickr && target._flatpickr.altInput) {
                        target._flatpickr.altInput.classList.remove('field-has-error');
                    }
                }
            }
        };

        wizardForm.addEventListener('input', (e) => clearErr(e.target));
        wizardForm.addEventListener('change', (e) => {
            clearErr(e.target);
            if (e.target && e.target._flatpickr && e.target._flatpickr.altInput) {
                clearErr(e.target._flatpickr.altInput);
            }
        });
    }
});

const reportWizardForm = document.getElementById('reportWizard');
if (reportWizardForm) {
    reportWizardForm.addEventListener('submit', function(e) {
        e.preventDefault();

        // Validasi menyeluruh seluruh langkah formulir
        const totalSteps = document.querySelectorAll('.wizard-step').length || 6;
        for (let s = 1; s <= totalSteps; s++) {
            if (!validateStepFields(s)) {
                goToStepDirect(s);
                return;
            }
        }

        if (typeof showKawungLoading === 'function') {
            showKawungLoading('Mengirim Laporan...', 'Menyimpan data ke Database Staging...');
        } else {
            Swal.fire({
                title: 'Mengirim Laporan...',
                allowOutsideClick: false,
                didOpen: () => { Swal.showLoading(); }
            });
        }

        const formData = new FormData(this);
        if (typeof window.appendStaffPhotosToFormData === 'function') {
            window.appendStaffPhotosToFormData(formData);
        }
        
        fetch('/staff/submit', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (typeof hideKawungLoading === 'function') hideKawungLoading();
            Swal.close();

            if (data.status === 'success') {
                const serverPhotos = Array.isArray(data.photos) ? data.photos : [];
                window.currentStaffCollageBlob = null;
                if (serverPhotos.length > 0 && typeof window.buildStaffCollageBlob === 'function') {
                    window.buildStaffCollageBlob(serverPhotos, data.airport_code, data.tanggal).then(b => {
                        window.currentStaffCollageBlob = b;
                    }).catch(() => {});
                }

                const photoCtrlVHtml = serverPhotos.length > 0 ? `
                    <div style="background: #f0f9ff; border: 1.5px solid #7dd3fc; border-radius: 10px; padding: 0.75rem 0.9rem; margin-top: 0.85rem; text-align: left; font-size: 0.82rem; color: #0c4a6e;">
                        <div style="font-weight: 800; color: #002b49; margin-bottom: 0.25rem;">
                            <i class="fa-solid fa-file-pdf text-danger me-1"></i> ${serverPhotos.length} Foto Dokumentasi Siap Dijadikan PDF A4
                        </div>
                        <div>
                            Saat klik tombol di bawah, <b>Dokumen PDF Foto (${data.airport_code})</b> akan otomatis diunduh/dibagikan agar dapat dilampirkan dengan rapi di WhatsApp Department Head!
                        </div>
                    </div>
                ` : '';

                Swal.fire({
                    title: 'Laporan Diajukan ke DH!', 
                    html: `
                        <div style="font-size: 0.92rem; color: #334155; line-height: 1.5;">
                            Data telah berhasil disimpan di Database Staging sementara.<br><br>
                            Apakah Anda ingin mengirimkan notifikasi review ke WhatsApp Department Head?
                            ${photoCtrlVHtml}
                        </div>
                    `,
                    icon: 'success',
                    showCancelButton: true,
                    confirmButtonText: serverPhotos.length > 0
                        ? '<i class="fa-solid fa-file-pdf me-1"></i> Ya, Unduh PDF Foto & Beritahu DH'
                        : '<i class="fab fa-whatsapp"></i> Ya, Beritahu DH',
                    cancelButtonText: 'Kembali ke Dashboard',
                    confirmButtonColor: '#16a34a',
                    cancelButtonColor: '#64748b'
                }).then(async (result) => {
                    if (result.isConfirmed) {
                        const phone = data.dh_phone || data.gm_phone;
                        if (phone) {
                            let text = data.dh_message || data.gm_message || `Halo Department Head, Laporan Harian Airside baru saja diajukan dari cabang ${data.airport_code}. Mohon direview di portal.`;
                            let cleanDH = phone.replace(/\D/g, '');
                            if (cleanDH.startsWith('0')) cleanDH = '62' + cleanDH.substring(1);

                            const dhWaUrl = `https://wa.me/${cleanDH}?text=${encodeURIComponent(text)}`;
                            if (serverPhotos.length > 0 && window.AirsidePhotoPdf) {
                                const safeDate = (data.tanggal || 'Harian').replace(/[^0-9a-zA-Z_-]/g, '-');
                                const cachedDocRes = window.currentStaffCollageBlob ? {
                                    blob: window.currentStaffCollageBlob,
                                    filename: `Dokumentasi_Foto_Airside_${data.airport_code}_${safeDate}.png`
                                } : null;
                                await window.AirsidePhotoPdf.sendPdfAndTextViaWhatsApp({
                                    photos: serverPhotos,
                                    airportCode: data.airport_code,
                                    dateStr: data.tanggal,
                                    singleBranch: true,
                                    cachedDocRes: cachedDocRes,
                                    waUrl: dhWaUrl,
                                    waText: text,
                                    recipientLabel: 'Department Head',
                                    shareTitle: `Laporan & Dokumentasi Airside ${data.airport_code}`
                                });
                            } else {
                                window.open(dhWaUrl, '_blank');
                            }
                        } else {
                            Swal.fire('Info', 'Nomor WA Department Head belum dikonfigurasi.', 'info');
                        }
                    }

                    // Tampilkan loading spinner InJourney Kawung sebelum dan sesudah reload dashboard
                    try {
                        sessionStorage.setItem('staff_dashboard_reload_loading', 'true');
                    } catch(e) {}

                    if (typeof showKawungLoading === 'function') {
                        showKawungLoading('Memuat Dashboard...', 'Memperbarui data dan status laporan...');
                    }

                    setTimeout(() => {
                        window.location.href = '/staff/dashboard';
                    }, 400);
                });
            } else {
                Swal.fire('Gagal Menyimpan', data.message || 'Terjadi kesalahan sistem', 'error');
            }
        })
        .catch(error => {
            if (typeof hideKawungLoading === 'function') hideKawungLoading();
            Swal.close();
            Swal.fire('Error', 'Gagal terhubung ke server', 'error');
            console.error('Error:', error);
        });
    });
}
