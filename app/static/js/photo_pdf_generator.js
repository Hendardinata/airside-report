/**
 * Generator Dokumen Resmi Lampiran Foto Lapangan Airside (Standar A4 Korporat)
 * PT Angkasa Pura Indonesia (InJourney Airports) — Regional II
 *
 * Mendukung 2 Output Dokumen Resmi:
 * 1. Lembar Dokumen A4 Terstruktur per Cabang (PNG Resolusi Tinggi):
 *    - Berlatar putih bersih standar dokumen A4 korporat InJourney Airports.
 *    - Dikelompokkan rapi per cabang (1. DPS, 2. LOP, 3. KOE, 4. BWX) dengan banner pemisah cabang.
 *    - Jika jumlah foto ganjil (misal 1 atau 3 foto), foto terakhir otomatis ditempatkan simetris di tengah
 *      sehingga tidak pernah ada ruang kosong pincang.
 *    - Memungkinkan pengiriman 1x Kerja di HP (navigator.share mengirim Dokumen + Teks sekaligus dalam 1 langkah!)
 *      dan 1x Kerja di Laptop/PC (otomatis disalin ke Clipboard untuk Ctrl+V sekaligus membuka chat WA).
 * 2. File Dokumen PDF Multi-Halaman (.PDF) untuk unduhan arsip resmi A4.
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
    let cachedLogoImg = null;

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

    async function getLogoImage() {
        if (cachedLogoImg) return cachedLogoImg;
        try {
            cachedLogoImg = await loadImage('/static/img/logo-kawung.png');
            return cachedLogoImg;
        } catch (e) {
            return null;
        }
    }

    async function getLogoDataUrl() {
        if (cachedLogoDataUrl) return cachedLogoDataUrl;
        try {
            const img = await getLogoImage();
            if (!img) return null;
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

    function drawRoundedRect(ctx, x, y, w, h, r, fillStyle, strokeStyle, lineWidth) {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
        if (fillStyle) {
            ctx.fillStyle = fillStyle;
            ctx.fill();
        }
        if (strokeStyle) {
            ctx.strokeStyle = strokeStyle;
            ctx.lineWidth = lineWidth || 1;
            ctx.stroke();
        }
    }

    function wrapCanvasText(ctx, text, maxWidth, maxLines) {
        const words = String(text || '').split(/\s+/);
        const lines = [];
        let currentLine = '';

        for (let i = 0; i < words.length; i++) {
            const testLine = currentLine ? `${currentLine} ${words[i]}` : words[i];
            const metrics = ctx.measureText(testLine);
            if (metrics.width > maxWidth && currentLine) {
                lines.push(currentLine);
                currentLine = words[i];
                if (lines.length >= maxLines - 1) {
                    break;
                }
            } else {
                currentLine = testLine;
            }
        }
        if (currentLine && lines.length < maxLines) {
            lines.push(currentLine);
        }
        return lines;
    }

    /**
     * Bangun Lembar Dokumen A4 Putih Resmi Terstruktur per Cabang (Blob PNG)
     * Digunakan untuk pengiriman 1x Kerja di WhatsApp Mobile (navigator.share) & Desktop (Ctrl+V).
     */
    async function buildStructuredDocumentBlob(options) {
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
        if (totalPhotos === 0) return null;

        const docW = 1400;
        const marginX = 48;
        const contentW = docW - marginX * 2; // 1304 px
        const gapX = 28;
        const gapY = 24;
        const cardW = (contentW - gapX) / 2; // 638 px
        const cardH = 468;
        const imgH = 362;

        const headerH = 142;
        const branchBannerH = 58;
        const branchGap = 34;
        const footerH = 66;

        // Hitung tinggi total dokumen secara presisi
        let totalHeight = headerH + 24;
        activeCodes.forEach((code, idx) => {
            const count = grouped[code].length;
            const rows = Math.ceil(count / 2);
            totalHeight += branchBannerH + 18 + rows * cardH + Math.max(0, rows - 1) * gapY;
            if (idx < activeCodes.length - 1) {
                totalHeight += branchGap;
            }
        });
        totalHeight += 30 + footerH;

        const canvas = document.createElement('canvas');
        canvas.width = docW;
        canvas.height = totalHeight;
        const ctx = canvas.getContext('2d');

        // Background Kertas Dokumen Putih Bersih
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, docW, totalHeight);

        // Top Corporate Accent Bar
        ctx.fillStyle = '#002b49';
        ctx.fillRect(0, 0, docW, 12);
        ctx.fillStyle = '#00B7CD';
        ctx.fillRect(0, 12, docW, 5);

        // Logo Kawung
        const logoImg = await getLogoImage();
        let titleStartX = marginX;
        if (logoImg) {
            ctx.drawImage(logoImg, marginX, 34, 76, 76);
            titleStartX = marginX + 94;
        }

        // Kop Surat Resmi
        ctx.fillStyle = '#008ca5';
        ctx.font = 'bold 19px sans-serif';
        ctx.fillText('INJOURNEY AIRPORTS — PT ANGKASA PURA INDONESIA', titleStartX, 52);

        ctx.fillStyle = '#002b49';
        ctx.font = 'bold 30px sans-serif';
        ctx.fillText('LAMPIRAN DOKUMENTASI FOTO FASILITAS SISI UDARA', titleStartX, 86);

        ctx.fillStyle = '#64748b';
        ctx.font = '19px sans-serif';
        ctx.fillText(
            isSingleBranch
                ? `Laporan Harian Kondisi Fasilitas Airside — Kantor Cabang ${defaultBranch}`
                : `Laporan Harian Kondisi Fasilitas Airside — Kantor Regional II (${activeCodes.length} Cabang)`,
            titleStartX,
            114
        );

        // Kotak Metadata Kanan Atas
        const metaW = 340;
        const metaX = docW - marginX - metaW;
        drawRoundedRect(ctx, metaX, 30, metaW, 92, 12, '#f8fafc', '#cbd5e1', 2);

        ctx.fillStyle = '#64748b';
        ctx.font = 'bold 14px sans-serif';
        ctx.fillText('TANGGAL LAPORAN', metaX + 20, 54);

        ctx.fillStyle = '#0f172a';
        ctx.font = 'bold 21px sans-serif';
        ctx.fillText(String(formattedDate), metaX + 20, 82);

        ctx.fillStyle = '#0369a1';
        ctx.font = 'bold 15px sans-serif';
        ctx.fillText(`Total Dokumentasi: ${totalPhotos} Foto Lapangan`, metaX + 20, 107);

        // Garis Pemisah Kop
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(marginX, headerH);
        ctx.lineTo(docW - marginX, headerH);
        ctx.stroke();

        let curY = headerH + 24;

        // Render Setiap Cabang Secara Terpisah & Berurutan
        for (let bIdx = 0; bIdx < activeCodes.length; bIdx++) {
            const code = activeCodes[bIdx];
            const branchPhotos = grouped[code];
            const numLabel = AIRPORT_NUMBERS[code] ? `${AIRPORT_NUMBERS[code]}. ` : '';
            const fullAirportName = AIRPORT_NAMES[code] || `Kantor Cabang ${code}`;

            // Banner Header Cabang
            drawRoundedRect(ctx, marginX, curY, contentW, branchBannerH, 12, '#002b49', null, 0);

            // Pill Kode Cabang
            drawRoundedRect(ctx, marginX + 14, curY + 11, 110, 36, 8, '#00B7CD', null, 0);
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 20px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(`${numLabel}${code}`, marginX + 69, curY + 36);
            ctx.textAlign = 'left';

            // Nama Bandara
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 22px sans-serif';
            ctx.fillText(fullAirportName.toUpperCase(), marginX + 140, curY + 36);

            // Jumlah Foto Cabang di Kanan Banner
            ctx.fillStyle = '#bae6fd';
            ctx.font = 'bold 18px sans-serif';
            ctx.textAlign = 'right';
            ctx.fillText(`${branchPhotos.length} Foto Terlampir`, docW - marginX - 20, curY + 36);
            ctx.textAlign = 'left';

            curY += branchBannerH + 18;

            const rows = Math.ceil(branchPhotos.length / 2);
            for (let r = 0; r < rows; r++) {
                const idxLeft = r * 2;
                const idxRight = idxLeft + 1;
                const isLastSingleRow = idxRight >= branchPhotos.length;

                const rowItems = isLastSingleRow
                    ? [{ photo: branchPhotos[idxLeft], pIdx: idxLeft, x: marginX + Math.round((contentW - cardW) / 2) }]
                    : [
                        { photo: branchPhotos[idxLeft], pIdx: idxLeft, x: marginX },
                        { photo: branchPhotos[idxRight], pIdx: idxRight, x: marginX + cardW + gapX }
                    ];

                for (let c = 0; c < rowItems.length; c++) {
                    const item = rowItems[c];
                    const p = item.photo;
                    const cardX = item.x;
                    const cardY = curY;

                    // Kerangka Kartu Putih Bersih
                    drawRoundedRect(ctx, cardX, cardY, cardW, cardH, 12, '#ffffff', '#cbd5e1', 2);

                    // Area Gambar
                    const imgX = cardX + 8;
                    const imgY = cardY + 8;
                    const innerImgW = cardW - 16;

                    ctx.fillStyle = '#f1f5f9';
                    ctx.fillRect(imgX, imgY, innerImgW, imgH);

                    try {
                        const img = await loadImage(p.url);
                        const iw = img.width || innerImgW;
                        const ih = img.height || imgH;
                        const scale = Math.max(innerImgW / iw, imgH / ih);
                        const sw = innerImgW / scale;
                        const sh = imgH / scale;
                        const sx = Math.max(0, (iw - sw) / 2);
                        const sy = Math.max(0, (ih - sh) / 2);
                        ctx.drawImage(img, sx, sy, sw, sh, imgX, imgY, innerImgW, imgH);
                    } catch (e) {
                        ctx.fillStyle = '#e2e8f0';
                        ctx.fillRect(imgX, imgY, innerImgW, imgH);
                        ctx.fillStyle = '#64748b';
                        ctx.font = 'bold 20px sans-serif';
                        ctx.textAlign = 'center';
                        ctx.fillText('Foto Dokumentasi', imgX + innerImgW / 2, imgY + imgH / 2);
                        ctx.textAlign = 'left';
                    }

                    // Kotak Keterangan di Bawah Foto
                    const metaY = imgY + imgH + 6;
                    const metaH = cardH - imgH - 22;
                    drawRoundedRect(ctx, imgX, metaY, innerImgW, metaH, 8, '#f8fafc', '#e2e8f0', 1);

                    // Badge Area
                    const areaLabel = `AREA: ${(p.area_tag || 'UMUM').toUpperCase()}`;
                    drawRoundedRect(ctx, imgX + 12, metaY + 10, 210, 28, 6, '#002b49', null, 0);
                    ctx.fillStyle = '#38bdf8';
                    ctx.font = 'bold 14px sans-serif';
                    ctx.fillText(areaLabel.substring(0, 24), imgX + 22, metaY + 29);

                    // Nomor Foto di Kanan
                    ctx.fillStyle = '#64748b';
                    ctx.font = 'bold 14px sans-serif';
                    ctx.textAlign = 'right';
                    ctx.fillText(`Foto #${item.pIdx + 1} (${code})`, imgX + innerImgW - 12, metaY + 29);
                    ctx.textAlign = 'left';

                    // Keterangan / Caption (Multi-baris rapi)
                    const rawCap = (p.caption && String(p.caption).trim())
                        ? String(p.caption).trim()
                        : `Dokumentasi pemeriksaan kondisi fasilitas ${p.area_tag || 'sisi udara'} cabang ${code}.`;
                    ctx.fillStyle = '#1e293b';
                    ctx.font = '16px sans-serif';
                    const capLines = wrapCanvasText(ctx, rawCap, innerImgW - 24, 2);
                    capLines.forEach((line, lIdx) => {
                        ctx.fillText(line, imgX + 12, metaY + 56 + lIdx * 20);
                    });
                }

                curY += cardH + (r < rows - 1 ? gapY : 0);
            }

            if (bIdx < activeCodes.length - 1) {
                curY += branchGap;
            }
        }

        // Footer Dokumen Resmi
        const footerTopY = totalHeight - footerH;
        ctx.strokeStyle = '#cbd5e1';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(marginX, footerTopY);
        ctx.lineTo(docW - marginX, footerTopY);
        ctx.stroke();

        ctx.fillStyle = '#475569';
        ctx.font = 'bold 16px sans-serif';
        ctx.fillText('PT Angkasa Pura Indonesia (InJourney Airports) — Regional II', marginX, footerTopY + 34);

        ctx.fillStyle = '#64748b';
        ctx.font = '16px sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(
            `Dokumen Resmi Lampiran Foto Airside • Tanggal: ${formattedDate}`,
            docW - marginX,
            footerTopY + 34
        );
        ctx.textAlign = 'left';

        const safeDate = (dateStr || 'Harian').replace(/[^0-9a-zA-Z_-]/g, '-');
        const filename = isSingleBranch
            ? `Dokumentasi_Foto_Airside_${defaultBranch}_${safeDate}.png`
            : `Dokumentasi_Foto_Airside_Regional_II_${safeDate}.png`;

        const blob = await new Promise((resolve) => {
            canvas.toBlob((b) => resolve(b), 'image/png', 0.94);
        });

        return {
            blob,
            filename,
            totalPhotos
        };
    }

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

    /**
     * Buat objek jsPDF (.PDF A4 Multi-Halaman) untuk diunduh/diarsipkan
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
            doc.setFillColor(0, 43, 73);
            doc.rect(0, 0, pageW, 4, 'F');
            doc.setFillColor(0, 183, 205);
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

                // Jika foto ini adalah foto ganjil terakhir pada halaman tersebut, posisikan simetris di tengah!
                const isLastOddInBranch = (pIdx === branchPhotos.length - 1) && (slotInPage % 2 === 0);
                const cardX = isLastOddInBranch
                    ? marginX + (contentW - cardW) / 2
                    : marginX + col * (cardW + gapX);
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

    /**
     * PENGIRIMAN 1X KERJA (SATU LANGKAH LANGSUNG TERKIRIM DOKUMEN + TEKS)
     *
     * - Di HP (Mobile):
     *   Menggunakan Lembar Dokumen A4 Putih Resmi (PNG) di dalam navigator.share({ files: [docFile], text: waText })
     *   sehingga aplikasi WhatsApp di HP langsung menyertakan Dokumen A4 + Teks Laporan sekaligus dalam 1x Kirim!
     * - Di Laptop / PC (Desktop):
     *   Otomatis menyalin Lembar Dokumen A4 Putih Resmi ke Clipboard (siap Ctrl+V) DAN langsung membuka ruang chat
     *   WhatsApp dalam 1x klik tanpa popup yang menghalangi!
     */
    async function sendPdfAndTextViaWhatsApp(options) {
        const opts = options || {};
        const waUrl = opts.waUrl || '';
        const waText = opts.waText || '';
        const isMobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent || '');

        // 1. Di HP (Mobile): Kirim Lembar Dokumen A4 Resmi + Teks sekaligus dalam 1x Kerja via navigator.share
        if (isMobile && navigator.canShare) {
            let docRes = opts.cachedDocRes || null;
            if (!docRes) {
                docRes = await buildStructuredDocumentBlob(opts);
            }
            if (docRes && docRes.blob) {
                const docFile = new File([docRes.blob], docRes.filename, { type: 'image/png' });
                if (navigator.canShare({ files: [docFile] })) {
                    try {
                        await navigator.share({
                            title: opts.shareTitle || 'Laporan Harian & Dokumentasi Airside',
                            text: waText,
                            files: [docFile]
                        });
                        return { shared: true, completed: true };
                    } catch (shareErr) {
                        if (shareErr && shareErr.name === 'AbortError') {
                            return { aborted: true, completed: false };
                        }
                    }
                }
            }
        }

        // 2. Di Laptop / PC (Desktop): Salin Lembar Dokumen A4 Resmi ke Clipboard (Ctrl+V) + Langsung Buka WA (1x Klik!)
        try {
            if (navigator.clipboard && typeof ClipboardItem !== 'undefined') {
                const blobPromise = opts.cachedDocRes && opts.cachedDocRes.blob
                    ? Promise.resolve(opts.cachedDocRes.blob)
                    : buildStructuredDocumentBlob(opts).then(r => (r ? r.blob : null));
                await navigator.clipboard.write([new ClipboardItem({ 'image/png': blobPromise })]);
            }
        } catch (clipErr) {
            console.warn('Auto-copy dokumen A4 ke clipboard gagal:', clipErr);
        }

        if (waUrl) {
            window.open(waUrl, '_blank');
        }
        return { completed: true };
    }

    async function shareOrDownloadPhotoPdf(options) {
        return sendPdfAndTextViaWhatsApp(options);
    }

    window.AirsidePhotoPdf = {
        buildStructuredDocumentBlob,
        buildPhotoDocumentPdf,
        downloadPhotoPdf,
        shareOrDownloadPhotoPdf,
        sendPdfAndTextViaWhatsApp,
        formatIndonesianDateStr
    };
})(window);
