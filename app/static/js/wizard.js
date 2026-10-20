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
                title: 'Laporan Diajukan ke GM!', 
                text: 'Data telah berhasil disimpan di Spreadsheet Staging sementara.\n\nApakah Anda ingin mengirimkan notifikasi telaah ke WhatsApp General Manager?', 
                icon: 'success',
                showCancelButton: true,
                confirmButtonText: '<i class="fab fa-whatsapp"></i> Ya, Beritahu GM',
                cancelButtonText: 'Kembali ke Dashboard',
                confirmButtonColor: '#16a34a',
                cancelButtonColor: '#64748b'
            }).then((result) => {
                if (result.isConfirmed) {
                    if (data.gm_phone) {
                        let text = data.gm_message || `Halo General Manager, Laporan Harian Airside baru saja diajukan dari cabang ${data.airport_code}. Mohon ditelaah di portal.`;
                        let cleanGM = data.gm_phone.replace(/\D/g, '');
                        if (cleanGM.startsWith('0')) cleanGM = '62' + cleanGM.substring(1);
                        window.open(`https://wa.me/${cleanGM}?text=${encodeURIComponent(text)}`, '_blank');
                    } else {
                        Swal.fire('Info', 'Nomor WA General Manager belum dikonfigurasi.', 'info');
                    }
                }
                setTimeout(() => {
                    window.location.href = '/staff/dashboard';
                }, 500);
            });
        } else {
            Swal.fire('Gagal Menyimpan', data.message || 'Terjadi kesalahan sistem', 'error');
        }
    })
    .catch(error => {
        Swal.fire('Error', 'Gagal terhubung ke server', 'error');
        console.error('Error:', error);
    });
});
