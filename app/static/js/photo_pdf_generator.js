/**
 * Generator Dokumen PDF Resmi Lampiran Foto Lapangan Airside (Standar A4 Korporat)
 * PT Angkasa Pura Indonesia (InJourney Airports) — Regional II
 *
 * Fitur Utama:
 * - Kertas A4 Portrait (210mm x 297mm) berlatar putih bersih standar dokumen eksekutif.
 * - Setiap Kantor Cabang (1. DPS, 2. LOP, 3. KOE, 4. BWX) dipisahkan pada halaman tersendiri
 *   sehingga foto antarbandara tidak pernah tercampur.
 * - Tata letak Grid 2x2 (maksimal 4 foto per halaman A4) dengan proporsi foto terjaga tajam,
 *   dilengkapi badge Area (Runway/Taxiway/Apron) dan deskripsi lengkap di bawah foto.
 * - Kop dokumen resmi + nomor halaman ("Halaman X dari Y") otomatis di setiap lembar.
 * - Alur Dual-Send Mobile & Desktop: Menjamin File PDF Dokumentasi DAN Pesan Teks Laporan Lengkap
 *   sama-sama terkirim ke WhatsApp tanpa terpotong.
 */
(function (window) {
    'use strict';

    const AIRPORT_ORDER = ['DPS', 'LOP', 'KOE', 'BWX'];
    const AIRPORT_NAMES = {
        DPS: 'Bandara Internasional I Gusti Ngurah Rai — Bali',
        LOP: 'Bandara Internasional Zainuddin Abdul Madjid — Lombok',
        KOE: 'Bandara Internasional El Tari — Kupang',
        BWX: 'Bandara Internasional Banyuwangi'
    };
    const AIRPORT_NUMBERS = {
        DPS: '1',
        LOP: '2',
        KOE: '3',
        BWX: '4'
    };

    let cachedLogoDataUrl = null;

    function ensureJsPdfLoaded() {
        if (window.jspdf && window.jspdf.jsPDF) {
            return Promise.resolve(window.jspdf.jsPDF);
        }
        return new Promise((resolve, reject) => {
            const existing = document.querySelector('script[data-jspdf-cdn]');
            if (existing) {
                existing.addEventListener('load', () => resolve(window.jspdf.jsPDF));
                existing.addEventListener('error', reject);
                return;
            }
            const s = document.createElement('script');
            s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
            s.setAttribute('data-jspdf-cdn', '1');
            s.onload = () => {
                if (window.jspdf && window.jspdf.jsPDF) {
                    resolve(window.jspdf.jsPDF);
                } else {
                    reject(new Error('jsPDF tidak tersedia'));
                }
            };
            s.onerror = () => reject(new Error('Gagal memuat pustaka jsPDF'));
            document.head.appendChild(s);
        });
    }

    function loadImage(src) {
        return new Promise((resolve, reject) => {
            if (!src) return reject(new Error('URL gambar kosong'));
            const img = new Image();
            if (!src.startsWith('/') && !src.startsWith('data:') && !src.startsWith('blob:')) {
                img.crossOrigin = 'anonymous';
            }
            img.onload = () => resolve(img);
            img.onerror = (e) => reject(e);
            img.src = src;
        });
    }

    async function getLogoDataUrl() {
        if (cachedLogoDataUrl) return cachedLogoDataUrl;
        try {
            const img = await loadImage('/static/img/logo-kawung.png');
            const canvas = document.createElement('canvas');
            canvas.width = img.width || 120;
            canvas.height = img.height || 120;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            cachedLogoDataUrl = canvas.toDataURL('image/png');
            return cachedLogoDataUrl;
        } catch (e) {
            return null;
        }
    }

    /**
     * Render foto ke kanvas proporsional (1000 x 720 px) dengan center-crop rapi
     * agar tidak gepeng dan tajam ketika di-zoom di dalam PDF.
     */
    async function renderHighResPhotoBox(src) {
        const targetW = 1000;
        const targetH = 720;
        const canvas = document.createElement('canvas');
        canvas.width = targetW;
        canvas.height = targetH;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = '#f1f5f9';
        ctx.fillRect(0, 0, targetW, targetH);

        try {
            const img = await loadImage(src);
            const iw = img.width || targetW;
            const ih = img.height || targetH;
            const scale = Math.max(targetW / iw, targetH / ih);
            const sw = targetW / scale;
            const sh = targetH / scale;
            const sx = Math.max(0, (iw - sw) / 2);
            const sy = Math.max(0, (ih - sh) / 2);
            ctx.drawImage(img, sx, sy, sw, sh, 0, 0, targetW, targetH);
        } catch (err) {
            ctx.fillStyle = '#e2e8f0';
            ctx.fillRect(0, 0, targetW, targetH);
            ctx.fillStyle = '#64748b';
            ctx.font = 'bold 28px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Foto Dokumentasi Tidak Dapat Dimuat', targetW / 2, targetH / 2);
        }

        return canvas.toDataURL('image/jpeg', 0.90);
    }

    function formatIndonesianDateStr(dateStr) {
        if (!dateStr) return '-';
        const clean = String(dateStr).trim();
        const m = clean.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (!m) return clean;
        const months = [
            'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ];
        const day = parseInt(m[3], 10);
        const monthIdx = parseInt(m[2], 10) - 1;
        const year = m[1];
        return `${day} ${months[monthIdx] || m[2]} ${year}`;
    }

    /**
     * Normalisasi daftar foto menjadi dikelompokkan per bandara sesuai urutan resmi:
     * 1. DPS, 2. LOP, 3. KOE, 4. BWX
     */
    function groupPhotosByAirport(photosInput, defaultAirportCode) {
        const grouped = { DPS: [], LOP: [], KOE: [], BWX: [] };
        if (!photosInput) return grouped;

        if (Array.isArray(photosInput)) {
            photosInput.forEach(p => {
                if (!p) return;
                const code = String(p.airport_code || p.airport || defaultAirportCode || 'DPS').toUpperCase();
                const targetCode = grouped[code] ? code : (defaultAirportCode || 'DPS');
                if (!grouped[targetCode]) grouped[targetCode] = [];
                grouped[targetCode].push({
                    url: p.url || p.src || p.previewUrl || '',
                    area_tag: p.area_tag || p.area || 'Umum',
                    caption: p.caption || '',
                    airport_code: targetCode
                });
            });
        } else if (typeof photosInput === 'object') {
            Object.keys(photosInput).forEach(code => {
                const upper = code.toUpperCase();
                const arr = photosInput[code];
                if (Array.isArray(arr)) {
                    if (!grouped[upper]) grouped[upper] = [];
                    arr.forEach(p => {
                        grouped[upper].push({
                            url: p.url || p.src || p.previewUrl || '',
                            area_tag: p.area_tag || p.area || 'Umum',
                            caption: p.caption || '',
                            airport_code: upper
                        });
                    });
                }
            });
        }
        return grouped;
    }

    /**
     * Buat objek jsPDF dan kembalikan { doc, blob, filename, totalPhotos, totalPages }
     */
    async function buildPhotoDocumentPdf(options) {
        const opts = options || {};
        const dateStr = opts.dateStr || '';
        const formattedDate = opts.formattedDate || formatIndonesianDateStr(dateStr);
        const defaultBranch = opts.airportCode ? String(opts.airportCode).toUpperCase() : '';
        const isSingleBranch = Boolean(opts.singleBranch && defaultBranch);

        const grouped = groupPhotosByAirport(opts.photos, defaultBranch || 'DPS');
        const activeCodes = AIRPORT_ORDER.filter(c => grouped[c] && grouped[c].length > 0);
        Object.keys(grouped).forEach(c => {
            if (!AIRPORT_ORDER.includes(c) && grouped[c] && grouped[c].length > 0) {
                activeCodes.push(c);
            }
        });

        const totalPhotos = activeCodes.reduce((acc, c) => acc + grouped[c].length, 0);
        if (totalPhotos === 0) {
            return null;
        }

        const JsPDF = await ensureJsPdfLoaded();
        const doc = new JsPDF({
            orientation: 'portrait',
            unit: 'mm',
            format: 'a4',
            compress: true
        });

        const logoData = await getLogoDataUrl();
        const pageW = 210;
        const pageH = 297;
        const marginX = 14;
        const contentW = pageW - marginX * 2; // 182 mm

        let totalPages = 0;
        activeCodes.forEach(code => {
            const count = grouped[code].length;
            totalPages += Math.max(1, Math.ceil(count / 4));
        });

        let currentPage = 0;

        function drawPageHeaderAndFooter(code, branchPhotoCount, branchPageIdx, branchTotalPages) {
            doc.setFillColor(0, 43, 73); // #002b49
            doc.rect(0, 0, pageW, 4, 'F');
            doc.setFillColor(0, 183, 205); // #00B7CD
            doc.rect(0, 4, pageW, 1.5, 'F');

            let textStartX = marginX;
            if (logoData) {
                try {
                    doc.addImage(logoData, 'PNG', marginX, 10, 13, 13);
                    textStartX = marginX + 16;
                } catch (e) {}
            }

            doc.setFont('helvetica', 'bold');
            doc.setFontSize(8.5);
            doc.setTextColor(0, 140, 165);
            doc.text('INJOURNEY AIRPORTS — PT ANGKASA PURA INDONESIA', textStartX, 13.5);

            doc.setFont('helvetica', 'bold');
            doc.setFontSize(13.5);
            doc.setTextColor(0, 43, 73);
            doc.text('LAMPIRAN DOKUMENTASI FOTO FASILITAS SISI UDARA', textStartX, 19.5);

            doc.setFont('helvetica', 'normal');
            doc.setFontSize(8.5);
            doc.setTextColor(100, 116, 139);
            doc.text(
                isSingleBranch
                    ? `Laporan Harian Kondisi Fasilitas Airside — Kantor Cabang ${code}`
                    : 'Laporan Harian Kondisi Fasilitas Airside — Kantor Regional II',
                textStartX,
                24.2
            );

            const metaW = 54;
            const metaX = pageW - marginX - metaW;
            doc.setFillColor(248, 250, 252);
            doc.setDrawColor(203, 213, 225);
            doc.setLineWidth(0.3);
            doc.roundedRect(metaX, 9.5, metaW, 16, 2, 2, 'FD');

            doc.setFont('helvetica', 'bold');
            doc.setFontSize(7);
            doc.setTextColor(100, 116, 139);
            doc.text('TANGGAL LAPORAN', metaX + 3.5, 14);

            doc.setFont('helvetica', 'bold');
            doc.setFontSize(9);
            doc.setTextColor(15, 23, 42);
            doc.text(String(formattedDate), metaX + 3.5, 18.8);

            doc.setFont('helvetica', 'normal');
            doc.setFontSize(7.2);
            doc.setTextColor(3, 105, 161);
            doc.text(`Total Dokumentasi: ${totalPhotos} Foto`, metaX + 3.5, 23.2);

            doc.setDrawColor(226, 232, 240);
            doc.setLineWidth(0.4);
            doc.line(marginX, 28.5, pageW - marginX, 28.5);

            const numLabel = AIRPORT_NUMBERS[code] ? `${AIRPORT_NUMBERS[code]}. ` : '';
            const fullAirportName = AIRPORT_NAMES[code] || `Kantor Cabang ${code}`;
            doc.setFillColor(0, 43, 73);
            doc.roundedRect(marginX, 31.5, contentW, 11, 2, 2, 'F');

            doc.setFillColor(0, 183, 205);
            doc.roundedRect(marginX + 2.5, 33.5, 18, 7, 1.5, 1.5, 'F');
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(8.5);
            doc.setTextColor(255, 255, 255);
            doc.text(`${numLabel}${code}`, marginX + 11.5, 38.2, { align: 'center' });

            doc.setFont('helvetica', 'bold');
            doc.setFontSize(9.5);
            doc.setTextColor(255, 255, 255);
            doc.text(fullAirportName.toUpperCase(), marginX + 23.5, 38.2);

            const pageSuffix = branchTotalPages > 1 ? ` (Lembar ${branchPageIdx}/${branchTotalPages})` : '';
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(8);
            doc.setTextColor(186, 230, 253);
            doc.text(`${branchPhotoCount} Foto Terlampir${pageSuffix}`, pageW - marginX - 3.5, 38.2, { align: 'right' });

            doc.setDrawColor(203, 213, 225);
            doc.setLineWidth(0.3);
            doc.line(marginX, pageH - 14, pageW - marginX, pageH - 14);

            doc.setFont('helvetica', 'bold');
            doc.setFontSize(7.5);
            doc.setTextColor(71, 85, 105);
            doc.text('PT Angkasa Pura Indonesia (InJourney Airports) — Regional II', marginX, pageH - 9.2);

            doc.setFont('helvetica', 'normal');
            doc.setFontSize(7.5);
            doc.setTextColor(100, 116, 139);
            doc.text(
                `Dokumen Resmi Lampiran Foto Airside • Halaman ${currentPage} dari ${totalPages}`,
                pageW - marginX,
                pageH - 9.2,
                { align: 'right' }
            );
        }

        for (let bIdx = 0; bIdx < activeCodes.length; bIdx++) {
            const code = activeCodes[bIdx];
            const branchPhotos = grouped[code];
            const branchTotalPages = Math.max(1, Math.ceil(branchPhotos.length / 4));

            for (let pIdx = 0; pIdx < branchPhotos.length; pIdx++) {
                const slotInPage = pIdx % 4;
                if (slotInPage === 0) {
                    if (currentPage > 0) {
                        doc.addPage();
                    }
                    currentPage++;
                    const branchPageIdx = Math.floor(pIdx / 4) + 1;
                    drawPageHeaderAndFooter(code, branchPhotos.length, branchPageIdx, branchTotalPages);
                }

                const photo = branchPhotos[pIdx];
                const col = slotInPage % 2;
                const row = Math.floor(slotInPage / 2);

                const gapX = 6;
                const gapY = 6;
                const cardW = (contentW - gapX) / 2; // 88 mm
                const cardH = 112;
                const imgH = 82;

                const cardX = marginX + col * (cardW + gapX);
                const cardY = 46 + row * (cardH + gapY);

                doc.setFillColor(255, 255, 255);
                doc.setDrawColor(203, 213, 225);
                doc.setLineWidth(0.35);
                doc.roundedRect(cardX, cardY, cardW, cardH, 2.5, 2.5, 'FD');

                const dataUrl = await renderHighResPhotoBox(photo.url);
                doc.addImage(dataUrl, 'JPEG', cardX + 1.5, cardY + 1.5, cardW - 3, imgH);

                const metaTopY = cardY + imgH + 3;
                doc.setFillColor(248, 250, 252);
                doc.rect(cardX + 0.5, cardY + imgH + 1.5, cardW - 1, cardH - imgH - 2, 'F');

                const areaText = `AREA: ${(photo.area_tag || 'UMUM').toUpperCase()}`;
                doc.setFillColor(0, 43, 73);
                doc.roundedRect(cardX + 3, metaTopY + 1, 36, 5.5, 1.2, 1.2, 'F');
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(7);
                doc.setTextColor(56, 189, 248);
                doc.text(areaText.substring(0, 22), cardX + 5, metaTopY + 4.8);

                doc.setFont('helvetica', 'bold');
                doc.setFontSize(7);
                doc.setTextColor(100, 116, 139);
                doc.text(`Foto #${pIdx + 1} (${code})`, cardX + cardW - 3, metaTopY + 4.8, { align: 'right' });

                const rawCaption = (photo.caption && String(photo.caption).trim())
                    ? String(photo.caption).trim()
                    : `Dokumentasi pemeriksaan rutin kondisi fasilitas ${photo.area_tag || 'sisi udara'} cabang ${code}.`;
                doc.setFont('helvetica', 'normal');
                doc.setFontSize(8);
                doc.setTextColor(30, 41, 59);
                const lines = doc.splitTextToSize(rawCaption, cardW - 6).slice(0, 3);
                doc.text(lines, cardX + 3, metaTopY + 10.5);
            }
        }

        const safeDate = (dateStr || 'Harian').replace(/[^0-9a-zA-Z_-]/g, '-');
        const filename = isSingleBranch
            ? `Dokumentasi_Foto_Airside_${defaultBranch}_${safeDate}.pdf`
            : `Dokumentasi_Foto_Airside_Regional_II_${safeDate}.pdf`;

        const blob = doc.output('blob');
        return {
            doc,
            blob,
            filename,
            totalPhotos,
            totalPages
        };
    }

    async function downloadPhotoPdf(options) {
        try {
            if (typeof window.showKawungLoading === 'function') {
                window.showKawungLoading('Menyusun Dokumen PDF Resmi...', 'Merapikan tata letak foto dokumentasi A4 per cabang...');
            }
            const res = await buildPhotoDocumentPdf(options);
            if (typeof window.hideKawungLoading === 'function') {
                window.hideKawungLoading();
            }
            if (!res) {
                if (window.Swal) {
                    Swal.fire('Info', 'Belum ada foto dokumentasi untuk dibuatkan PDF.', 'info');
                }
                return null;
            }
            res.doc.save(res.filename);
            return res;
        } catch (err) {
            if (typeof window.hideKawungLoading === 'function') {
                window.hideKawungLoading();
            }
            console.error('Gagal membuat PDF dokumentasi foto:', err);
            if (window.Swal) {
                Swal.fire('Gagal Membuat PDF', err.message || 'Terjadi kesalahan saat menyusun dokumen PDF.', 'error');
            }
            return null;
        }
    }

    async function copyTextSafe(txt) {
        if (!txt) return false;
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(txt);
                return true;
            }
        } catch (e) {}
        try {
            const ta = document.createElement('textarea');
            ta.value = txt;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            return true;
        } catch (e2) {
            return false;
        }
    }

    /**
     * Alur Pengiriman WhatsApp Lengkap (Teks Laporan + File PDF Dokumentasi Foto)
     *
     * Mengatasi limitasi teknis aplikasi WhatsApp di HP (Android/iOS):
     * Saat mengirim file dokumen (.pdf) melalui sistem Share HP (Intent.ACTION_SEND),
     * aplikasi WhatsApp secara bawaan mengabaikan teks panjang atau memotongnya.
     *
     * Solusi Dual-Send:
     * 1. Di HP (Mobile):
     *    - Otomatis menyalin Teks Laporan Lengkap ke Clipboard HP.
     *    - Membagikan File PDF Dokumentasi via menu Share WhatsApp.
     *    - Begitu selesai mengirim PDF, langsung menampilkan tombol 1-Ketuk
     *      "Kirim Teks Laporan ke WhatsApp" (membuka wa.me dengan teks penuh utuh),
     *      atau pengguna bisa langsung Tempel (Paste) teks di ruang chat WhatsApp!
     * 2. Di Laptop / PC (Desktop):
     *    - Mengunduh File PDF Resmi A4 dan langsung membuka tab WhatsApp dengan teks laporan lengkap.
     */
    async function sendPdfAndTextViaWhatsApp(options) {
        const opts = options || {};
        const waUrl = opts.waUrl || '';
        const waText = opts.waText || '';
        const recipientLabel = opts.recipientLabel || 'Penerima';
        const isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent || '');

        // 1. Salin teks laporan lengkap ke Clipboard terlebih dahulu selagi user-gesture masih aktif
        await copyTextSafe(waText);

        // 2. Bangun dokumen PDF A4
        if (typeof window.showKawungLoading === 'function') {
            window.showKawungLoading('Menyiapkan PDF & Teks Laporan...', 'Menyusun halaman dokumentasi foto A4...');
        }
        let pdfRes = null;
        try {
            pdfRes = await buildPhotoDocumentPdf(opts);
        } catch (err) {
            console.error('Gagal membuat PDF:', err);
        }
        if (typeof window.hideKawungLoading === 'function') {
            window.hideKawungLoading();
        }

        if (!pdfRes || !pdfRes.blob) {
            if (waUrl) window.open(waUrl, '_blank');
            return { completed: true };
        }

        // 3. Alur Khusus Mobile (Android / iOS)
        if (isMobile && navigator.canShare) {
            const pdfFile = new File([pdfRes.blob], pdfRes.filename, { type: 'application/pdf' });
            if (navigator.canShare({ files: [pdfFile] })) {
                const promptStep2SendText = async () => {
                    if (!window.Swal || !waUrl) {
                        if (waUrl) window.open(waUrl, '_blank');
                        return;
                    }
                    const step2 = await Swal.fire({
                        icon: 'success',
                        title: 'Langkah 2: Kirim Teks Laporan',
                        html: `
                            <div style="text-align: left; font-size: 0.88rem; color: #334155; line-height: 1.55;">
                                <div style="background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 12px; padding: 0.8rem 0.95rem; margin-bottom: 0.8rem;">
                                    <div style="font-weight: 800; color: #15803d; margin-bottom: 0.25rem;">
                                        <i class="fa-solid fa-circle-check me-1"></i> File PDF Dokumentasi Siap / Terkirim!
                                    </div>
                                    <div style="font-size: 0.81rem; color: #1e293b;">
                                        Karena WhatsApp di HP memisahkan pengiriman <b>File Dokumen PDF</b> dan <b>Pesan Teks Panjang</b>, silakan ketuk tombol hijau di bawah untuk mengirim <b>Teks Laporan Lengkap</b> ke <b>${recipientLabel}</b>:
                                    </div>
                                </div>
                                <div style="background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 9px; padding: 0.6rem 0.8rem; font-size: 0.78rem; color: #475569;">
                                    <i class="fa-regular fa-clipboard me-1 text-primary"></i>
                                    <b>Tips Cepat:</b> Teks laporan lengkap juga <b>sudah disalin otomatis ke Clipboard HP Anda</b>. Anda dapat langsung menekan <b>Tempel (Paste)</b> di ruang chat WhatsApp!
                                </div>
                            </div>
                        `,
                        showCancelButton: true,
                        confirmButtonText: `<i class="fa-brands fa-whatsapp me-1"></i> Kirim Teks Laporan ke ${recipientLabel}`,
                        cancelButtonText: 'Sudah Saya Tempel / Selesai',
                        confirmButtonColor: '#16a34a',
                        cancelButtonColor: '#64748b',
                        allowOutsideClick: false
                    });

                    if (step2.isConfirmed && waUrl) {
                        await copyTextSafe(waText);
                        window.open(waUrl, '_blank');
                    }
                };

                try {
                    await navigator.share({
                        title: opts.shareTitle || 'Dokumentasi Foto Laporan Harian Airside',
                        text: waText,
                        files: [pdfFile]
                    });
                    // Setelah pengguna kembali dari memilih kontak & mengirim PDF di WhatsApp,
                    // tampilkan tombol Langkah 2 untuk mengirim Teks Laporan Lengkap!
                    await promptStep2SendText();
                    return { shared: true, completed: true };
                } catch (shareErr) {
                    if (shareErr && shareErr.name === 'AbortError') {
                        return { aborted: true, completed: false };
                    }
                    // Jika browser HP menolak navigator.share otomatis karena jeda pembuatan PDF (NotAllowedError),
                    // tampilkan modal 2-Langkah interaktif agar pengguna mendapat user-gesture baru (0ms).
                    if (window.Swal) {
                        const manualShareModal = await Swal.fire({
                            title: 'Kirim PDF Foto & Teks Laporan',
                            html: `
                                <div style="text-align: left; font-size: 0.86rem; color: #334155; line-height: 1.5;">
                                    <div style="background: #f0f9ff; border: 1.5px solid #7dd3fc; border-radius: 11px; padding: 0.8rem 0.95rem; margin-bottom: 0.75rem;">
                                        <div style="font-weight: 800; color: #002b49; margin-bottom: 0.3rem;">
                                            <i class="fa-solid fa-file-pdf text-danger me-1"></i> ${pdfRes.filename} (${pdfRes.totalPhotos} Foto)
                                        </div>
                                        <div style="font-size: 0.8rem; color: #0c4a6e;">
                                            <b>Teks laporan sudah disalin ke Clipboard Anda.</b><br>
                                            Ketuk <b>Bagikan File PDF</b> di bawah untuk mengirim PDF ke WhatsApp, lalu lanjutkan dengan mengirim Teks Laporan.
                                        </div>
                                    </div>
                                </div>
                            `,
                            showCancelButton: true,
                            showDenyButton: true,
                            confirmButtonText: '<i class="fa-solid fa-file-pdf me-1"></i> 1. Bagikan File PDF ke WA',
                            denyButtonText: '<i class="fa-brands fa-whatsapp me-1"></i> Langsung Kirim Teks Saja',
                            cancelButtonText: 'Batal',
                            confirmButtonColor: '#002b49',
                            denyButtonColor: '#16a34a',
                            cancelButtonColor: '#64748b'
                        });

                        if (manualShareModal.isConfirmed) {
                            try {
                                await navigator.share({
                                    title: opts.shareTitle || 'Dokumentasi Foto Laporan Harian Airside',
                                    text: waText,
                                    files: [pdfFile]
                                });
                            } catch (e2) {
                                pdfRes.doc.save(pdfRes.filename);
                            }
                            await promptStep2SendText();
                            return { shared: true, completed: true };
                        } else if (manualShareModal.isDenied) {
                            pdfRes.doc.save(pdfRes.filename);
                            if (waUrl) window.open(waUrl, '_blank');
                            return { downloaded: true, completed: true };
                        }
                        return { aborted: true, completed: false };
                    }
                }
            }
        }

        // 4. Alur Desktop / Laptop (atau fallback jika Web Share file tidak didukung)
        if (!opts.alreadyConfirmedOnDesktop && window.Swal) {
            const stepRes = await Swal.fire({
                title: 'Kirim Laporan & PDF Dokumentasi Foto',
                html: `
                    <div style="text-align: left; font-size: 0.88rem; color: #334155; line-height: 1.55;">
                        <div style="background: #f0f9ff; border: 1.5px solid #7dd3fc; border-radius: 12px; padding: 0.9rem 1rem; margin-bottom: 0.85rem;">
                            <div style="font-weight: 800; color: #002b49; font-size: 0.93rem; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.45rem;">
                                <i class="fa-solid fa-file-pdf text-danger" style="font-size: 1.15rem;"></i>
                                <span>${pdfRes.totalPhotos} Foto Disusun ke PDF A4 (${pdfRes.totalPages} Halaman)</span>
                            </div>
                            <div style="font-size: 0.82rem; color: #1e293b;">
                                Saat klik tombol di bawah:
                                <ol style="margin: 0.45rem 0 0.25rem 1.2rem; padding: 0;">
                                    <li style="margin-bottom: 0.3rem;">File <b>${pdfRes.filename}</b> otomatis terunduh (rapi per cabang di kertas A4).</li>
                                    <li>Setelah WhatsApp terbuka, kirim teks laporan lalu <b>tarik (Drag & Drop)</b> file PDF dari bilah unduhan browser ke ruang chat WhatsApp!</li>
                                </ol>
                            </div>
                        </div>
                    </div>
                `,
                showCancelButton: true,
                confirmButtonText: '<i class="fa-solid fa-file-pdf me-1"></i> Unduh PDF Foto & Buka WhatsApp',
                cancelButtonText: 'Batal',
                confirmButtonColor: '#16a34a',
                cancelButtonColor: '#64748b',
                width: 520
            });
            if (!stepRes.isConfirmed) {
                return { aborted: true, completed: false };
            }
        }

        pdfRes.doc.save(pdfRes.filename);
        if (waUrl) {
            window.open(waUrl, '_blank');
        }
        return { downloaded: true, completed: true };
    }

    async function shareOrDownloadPhotoPdf(options) {
        return sendPdfAndTextViaWhatsApp(options);
    }

    window.AirsidePhotoPdf = {
        buildPhotoDocumentPdf,
        downloadPhotoPdf,
        shareOrDownloadPhotoPdf,
        sendPdfAndTextViaWhatsApp,
        formatIndonesianDateStr
    };
})(window);
