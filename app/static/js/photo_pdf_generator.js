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
     * Buat objek jsPDF dan kembalikan { blob, filename, totalPhotos, totalPages }
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

        // Pre-calculate total pages (maks 4 foto per halaman, dan setiap cabang mulai di halaman baru)
        let totalPages = 0;
        activeCodes.forEach(code => {
            const count = grouped[code].length;
            totalPages += Math.max(1, Math.ceil(count / 4));
        });

        let currentPage = 0;

        function drawPageHeaderAndFooter(code, branchPhotoCount, branchPageIdx, branchTotalPages) {
            // Top Navy & Cyan Bar
            doc.setFillColor(0, 43, 73); // #002b49
            doc.rect(0, 0, pageW, 4, 'F');
            doc.setFillColor(0, 183, 205); // #00B7CD
            doc.rect(0, 4, pageW, 1.5, 'F');

            // Header Box
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

            // Right Meta Pill Box
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

            // Divider Line
            doc.setDrawColor(226, 232, 240);
            doc.setLineWidth(0.4);
            doc.line(marginX, 28.5, pageW - marginX, 28.5);

            // Branch Banner Bar
            const numLabel = AIRPORT_NUMBERS[code] ? `${AIRPORT_NUMBERS[code]}. ` : '';
            const fullAirportName = AIRPORT_NAMES[code] || `Kantor Cabang ${code}`;
            doc.setFillColor(0, 43, 73);
            doc.roundedRect(marginX, 31.5, contentW, 11, 2, 2, 'F');

            // IATA Badge inside Banner
            doc.setFillColor(0, 183, 205);
            doc.roundedRect(marginX + 2.5, 33.5, 18, 7, 1.5, 1.5, 'F');
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(8.5);
            doc.setTextColor(255, 255, 255);
            doc.text(`${numLabel}${code}`, marginX + 11.5, 38.2, { align: 'center' });

            // Airport Name inside Banner
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(9.5);
            doc.setTextColor(255, 255, 255);
            doc.text(fullAirportName.toUpperCase(), marginX + 23.5, 38.2);

            // Right Count inside Banner
            const pageSuffix = branchTotalPages > 1 ? ` (Lembar ${branchPageIdx}/${branchTotalPages})` : '';
            doc.setFont('helvetica', 'bold');
            doc.setFontSize(8);
            doc.setTextColor(186, 230, 253);
            doc.text(`${branchPhotoCount} Foto Terlampir${pageSuffix}`, pageW - marginX - 3.5, 38.2, { align: 'right' });

            // Footer
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

        // Loop per cabang
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
                const cardH = 112; // 2 rows * 112 + 6 = 230mm (fits between y=46 and y=278)
                const imgH = 82;

                const cardX = marginX + col * (cardW + gapX);
                const cardY = 46 + row * (cardH + gapY);

                // Card Outer Border & Background
                doc.setFillColor(255, 255, 255);
                doc.setDrawColor(203, 213, 225);
                doc.setLineWidth(0.35);
                doc.roundedRect(cardX, cardY, cardW, cardH, 2.5, 2.5, 'FD');

                // Render & Embed Image
                const dataUrl = await renderHighResPhotoBox(photo.url);
                doc.addImage(dataUrl, 'JPEG', cardX + 1.5, cardY + 1.5, cardW - 3, imgH);

                // Metadata Footer Box inside Card
                const metaTopY = cardY + imgH + 3;
                doc.setFillColor(248, 250, 252);
                doc.rect(cardX + 0.5, cardY + imgH + 1.5, cardW - 1, cardH - imgH - 2, 'F');

                // Area Badge Pill
                const areaText = `AREA: ${(photo.area_tag || 'UMUM').toUpperCase()}`;
                doc.setFillColor(0, 43, 73);
                doc.roundedRect(cardX + 3, metaTopY + 1, 36, 5.5, 1.2, 1.2, 'F');
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(7);
                doc.setTextColor(56, 189, 248);
                doc.text(areaText.substring(0, 22), cardX + 5, metaTopY + 4.8);

                // Photo Number Label on Right
                doc.setFont('helvetica', 'bold');
                doc.setFontSize(7);
                doc.setTextColor(100, 116, 139);
                doc.text(`Foto #${pIdx + 1} (${code})`, cardX + cardW - 3, metaTopY + 4.8, { align: 'right' });

                // Caption Text (Multi-line wrapped cleanly up to 3 lines)
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

    async function shareOrDownloadPhotoPdf(options) {
        try {
            if (typeof window.showKawungLoading === 'function') {
                window.showKawungLoading('Menyiapkan Dokumen PDF Resmi...', 'Menyusun halaman dokumentasi foto A4...');
            }
            const res = await buildPhotoDocumentPdf(options);
            if (typeof window.hideKawungLoading === 'function') {
                window.hideKawungLoading();
            }
            if (!res) return { shared: false, downloaded: false };

            const isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent || '');
            const pdfFile = new File([res.blob], res.filename, { type: 'application/pdf' });

            if (isMobile && navigator.canShare && navigator.canShare({ files: [pdfFile] })) {
                try {
                    await navigator.share({
                        title: options.shareTitle || 'Dokumentasi Foto Laporan Harian Airside',
                        text: options.shareText || '',
                        files: [pdfFile]
                    });
                    return { shared: true, downloaded: false, ...res };
                } catch (shareErr) {
                    if (shareErr && shareErr.name === 'AbortError') {
                        return { shared: false, aborted: true, ...res };
                    }
                }
            }

            // Desktop / Fallback: Trigger automatic download of the PDF file
            res.doc.save(res.filename);
            return { shared: false, downloaded: true, ...res };
        } catch (err) {
            if (typeof window.hideKawungLoading === 'function') {
                window.hideKawungLoading();
            }
            console.error('Error shareOrDownloadPhotoPdf:', err);
            return { shared: false, downloaded: false, error: err };
        }
    }

    window.AirsidePhotoPdf = {
        buildPhotoDocumentPdf,
        downloadPhotoPdf,
        shareOrDownloadPhotoPdf,
        formatIndonesianDateStr
    };
})(window);

