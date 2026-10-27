// wizard.js

function getCurrentStepNum() {
    for (let i = 1; i <= 5; i++) {
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

document.getElementById('reportWizard').addEventListener('submit', function(e) {
    e.preventDefault();

    // Validasi menyeluruh seluruh langkah 1 sampai 5
    for (let s = 1; s <= 5; s++) {
        if (!validateStepFields(s)) {
            goToStepDirect(s);
            return;
        }
    }

    if (typeof showKawungLoading === 'function') {
        showKawungLoading('Mengirim Laporan...', 'Menyimpan data ke Spreadsheet Staging...');
    } else {
        Swal.fire({
            title: 'Mengirim Laporan...',
            allowOutsideClick: false,
            didOpen: () => { Swal.showLoading(); }
        });
    }

    const formData = new FormData(this);
    
    fetch('/staff/submit', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (typeof hideKawungLoading === 'function') hideKawungLoading();
        Swal.close();

        if (data.status === 'success') {
            Swal.fire({
                title: 'Laporan Diajukan ke GM!', 
                text: 'Data telah berhasil disimpan di Spreadsheet Staging sementara.\n\nApakah Anda ingin mengirimkan notifikasi review ke WhatsApp General Manager?', 
                icon: 'success',
                showCancelButton: true,
                confirmButtonText: '<i class="fab fa-whatsapp"></i> Ya, Beritahu GM',
                cancelButtonText: 'Kembali ke Dashboard',
                confirmButtonColor: '#16a34a',
                cancelButtonColor: '#64748b'
            }).then((result) => {
                if (result.isConfirmed) {
                    if (data.gm_phone) {
                        let text = data.gm_message || `Halo General Manager, Laporan Harian Airside baru saja diajukan dari cabang ${data.airport_code}. Mohon direview di portal.`;
                        let cleanGM = data.gm_phone.replace(/\D/g, '');
                        if (cleanGM.startsWith('0')) cleanGM = '62' + cleanGM.substring(1);
                        window.open(`https://wa.me/${cleanGM}?text=${encodeURIComponent(text)}`, '_blank');
                    } else {
                        Swal.fire('Info', 'Nomor WA General Manager belum dikonfigurasi.', 'info');
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
