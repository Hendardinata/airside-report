// wizard.js
function nextStep(step) {
    // Hide all steps
    document.querySelectorAll('.wizard-step').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
    
    // Show current step
    const targetStep = document.getElementById(`step-${step}`);
    const targetNav = document.getElementById(`step-nav-${step}`);
    if (targetStep) targetStep.style.display = 'block';
    if (targetNav) targetNav.classList.add('active');

    // Smooth scroll to top of wizard card
    const formCard = document.querySelector('.form-main-card') || document.getElementById('reportWizard');
    if (formCard) {
        formCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function prevStep(step) {
    nextStep(step);
}

document.getElementById('reportWizard').addEventListener('submit', function(e) {
    e.preventDefault();
    
    // Validasi input kosong
    let isEmpty = false;
    let firstEmpty = null;
    const inputs = this.querySelectorAll('input:not([type="hidden"]), select, textarea');
    inputs.forEach(input => {
        if (!input.value || input.value.trim() === '') {
            if (input.hasAttribute('required')) {
                isEmpty = true;
                if (!firstEmpty) firstEmpty = input;
            }
        }
    });

    if (isEmpty || !this.checkValidity()) {
        const invalidElement = firstEmpty || this.querySelector(':invalid');
        
        Swal.fire({
            icon: 'warning',
            title: 'Form Belum Lengkap!',
            text: 'Masih ada form inputan yang kosong. Mohon lengkapi terlebih dahulu baru kirim.',
            confirmButtonText: 'Mengerti',
            confirmButtonColor: '#003366'
        }).then(() => {
            if (invalidElement) {
                const step = invalidElement.closest('.wizard-step');
                if (step) {
                    const stepNum = step.id.split('-')[1];
                    nextStep(stepNum);
                    setTimeout(() => invalidElement.focus(), 300);
                }
            }
        });
        return;
    }

    Swal.fire({
        title: 'Mengirim Laporan...',
        text: 'Sedang menyuntikkan data ke Google Spreadsheet.',
        allowOutsideClick: false,
        didOpen: () => { Swal.showLoading() }
    });

    const formData = new FormData(this);
    
    fetch('/staff/submit', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            Swal.fire({
                title: 'Laporan Terkirim!', 
                text: 'Data telah berhasil disimpan ke Spreadsheet.\n\nApakah Anda ingin mengirim notifikasi laporan ke WhatsApp Admin?', 
                icon: 'success',
                showCancelButton: true,
                confirmButtonText: '<i class="fab fa-whatsapp"></i> Ya, Kirim ke Admin',
                cancelButtonText: 'Tidak, Kembali ke Dashboard',
                confirmButtonColor: '#16a34a',
                cancelButtonColor: '#64748b'
            }).then((result) => {
                if (result.isConfirmed) {
                    if (data.admin_phone) {
                        let text = data.admin_message || `Halo Admin, Laporan Harian Airside baru saja dikirimkan dari cabang ${data.airport_code}. Mohon dicek di sistem.`;
                        let cleanAdmin = data.admin_phone.replace(/\D/g, '');
                        if (cleanAdmin.startsWith('0')) cleanAdmin = '62' + cleanAdmin.substring(1);
                        window.open(`https://wa.me/${cleanAdmin}?text=${encodeURIComponent(text)}`, '_blank');
                    } else {
                        Swal.fire('Info', 'Nomor WA Admin belum diatur di Konfigurasi Pusat.', 'info');
                    }
                }
                // Reload dashboard after interacting with the prompt
                setTimeout(() => {
                    window.location.href = '/staff/dashboard';
                }, 500);
            });
        } else {
            Swal.fire('Error', data.message || 'Terjadi kesalahan sistem', 'error');
        }
    })
    .catch(error => {
        Swal.fire('Error', 'Gagal terhubung ke server', 'error');
        console.error('Error:', error);
    });
});
