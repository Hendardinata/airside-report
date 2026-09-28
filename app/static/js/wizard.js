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
    
    // Validasi HTML5 manual untuk mendukung hidden steps
    if (!this.checkValidity()) {
        const firstInvalid = this.querySelector(':invalid');
        if (firstInvalid) {
            const step = firstInvalid.closest('.wizard-step');
            if (step) {
                const stepNum = step.id.split('-')[1];
                nextStep(stepNum);
                setTimeout(() => firstInvalid.reportValidity(), 100);
            }
        }
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
            Swal.fire('Terkirim!', 'Data telah berhasil disimpan ke Spreadsheet.', 'success')
            .then(() => {
                window.location.href = '/staff/dashboard';
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
