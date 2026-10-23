$targetFile = "d:\Hendardinata\Basement\Project\Oktober 2026\wa-dir\airside-report-flask\app\templates\gm_dashboard.html"
$content = [System.IO.File]::ReadAllText($targetFile, [System.Text.Encoding]::UTF8)

$startMarker = 'contentBox.innerHTML = `' + "`r`n" + '                    <div class="dh-edit-container">'
if (-not $content.Contains($startMarker)) {
    $startMarker = "contentBox.innerHTML = `\n                    <div class=`"dh-edit-container`">"
}

$endMarker = '                    </div>' + "`r`n" + '                    `;' + "`r`n" + '                } else {'
if (-not $content.Contains($endMarker)) {
    $endMarker = "                    </div>\n                    `;\n                } else {"
}

if (-not $content.Contains($startMarker)) {
    Write-Error "Start marker not found!"
    exit 1
}

if (-not $content.Contains($endMarker)) {
    Write-Error "End marker not found!"
    exit 1
}

$newBody = @'
contentBox.innerHTML = `
                    <!-- STICKY TOP EXECUTIVE BANNER -->
                    <div class="doc-inline-edit-banner no-print">
                        <div class="doc-inline-edit-left">
                            <div class="doc-inline-edit-icon">
                                <i class="fa-solid fa-pen-nib"></i>
                            </div>
                            <div>
                                <div class="doc-inline-edit-title">
                                    <span>Mode Koreksi Langsung (WYSIWYG)</span>
                                    <span class="doc-editing-pill"><i class="fa-solid fa-circle-dot fa-fade me-1"></i> Live Editor</span>
                                </div>
                                <div class="doc-inline-edit-sub">
                                    Edit nilai langsung pada format resmi A4 di bawah ini. Klik Simpan setelah selesai.
                                </div>
                            </div>
                        </div>
                        <div class="doc-inline-edit-actions">
                            <button type="button" class="btn-inline-cancel" onclick="openDetailModal('${rep.report_id}')" title="Batalkan perubahan dan kembali ke dokumen">
                                <i class="fa-solid fa-arrow-left me-1"></i> Batal
                            </button>
                            <button type="button" class="btn-inline-save" onclick="submitDhSelfEdit('${rep.report_id}', false)" title="Simpan perubahan ke antrean Staging">
                                <i class="fa-solid fa-floppy-disk me-1"></i> Simpan Draf
                            </button>
                            <button type="button" class="btn-inline-approve" onclick="submitDhSelfEdit('${rep.report_id}', true)" title="Simpan perubahan dan langsung sahkan laporan">
                                <i class="fa-solid fa-circle-check me-1"></i> Simpan & Sahkan
                            </button>
                        </div>
                    </div>

                    <form id="dhSelfEditForm" onsubmit="event.preventDefault();">
                        <input type="hidden" name="TANGGAL" value="${safe(d.TANGGAL || rep.tanggal)}">
                        <input type="hidden" name="KANTOR_CABANG" value="${safe(d.KANTOR_CABANG || branchCode)}">

                        <div class="a4-document-page editing">
                            <!-- HEADER DOKUMEN RESMI A4 -->
                            <div class="doc-header-block">
                                <div class="doc-header-left">
                                    <div class="doc-header-brand-line">
                                        <img src="/static/img/logo-kawung.png" alt="Logo Kawung" class="doc-kawung-logo">
                                        <span class="doc-brand-title">Injourney airports</span>
                                    </div>
                                    <h1 class="doc-title-main">LAPORAN HARIAN AIRSIDE</h1>
                                    <div class="doc-subtitle-branch">KANTOR CABANG ${branchCode}</div>
                                </div>
                                <div class="doc-header-right">
                                    <div class="doc-meta-item">
                                        <span class="doc-meta-caption">TANGGAL LAPORAN</span>
                                        <span class="doc-meta-value">${formattedDate}</span>
                                    </div>
                                    <div class="doc-meta-item">
                                        <span class="doc-meta-caption">NOMOR LAPORAN</span>
                                        <span class="doc-meta-value">${rep.report_id || '-'}</span>
                                    </div>
                                </div>
                            </div>

                            <div class="doc-divider-solid"></div>

                            <!-- FORMAL GREETING & RECIPIENTS INTRO (LIVE EDITABLE) -->
                            <div class="doc-formal-intro-box">
                                <div class="doc-greeting-title">
                                    <div><em>Assalamu’alaikum Wr. Wb.</em></div>
                                    <div style="margin-top: 0.45rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                                        <em>Sapaan:</em>
                                        <input type="text" name="SAPAAN" class="doc-inline-input" style="max-width: 260px; font-weight: 700; font-style: italic; color: #002b49;" value="${safe(d.SAPAAN || 'Selamat Pagi')}" placeholder="Contoh: Selamat Pagi">
                                    </div>
                                </div>

                                <div class="doc-recipient-block">
                                    <div class="doc-recipient-caption">Kepada Yth. :</div>
                                    <div style="display: flex; flex-direction: column; gap: 0.45rem; margin-top: 0.45rem;">
                                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                                            <span style="font-weight: 800; color: #003366; width: 18px;">1.</span>
                                            <input type="text" name="PENERIMA_1" class="doc-inline-input" value="${safe(d.PENERIMA_1 || 'Pak DT API (Direktur Teknik Angkasa Pura Indonesia)')}" placeholder="Penerima 1">
                                        </div>
                                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                                            <span style="font-weight: 800; color: #003366; width: 18px;">2.</span>
                                            <input type="text" name="PENERIMA_2" class="doc-inline-input" value="${safe(d.PENERIMA_2 || 'Pak GH API (Airport Facility Management Group Head)')}" placeholder="Penerima 2">
                                        </div>
                                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                                            <span style="font-weight: 800; color: #003366; width: 18px;">3.</span>
                                            <input type="text" name="PENERIMA_3" class="doc-inline-input" value="${safe(d.PENERIMA_3)}" placeholder="(Penerima 3 - opsional)">
                                        </div>
                                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                                            <span style="font-weight: 800; color: #003366; width: 18px;">4.</span>
                                            <input type="text" name="PENERIMA_4" class="doc-inline-input" value="${safe(d.PENERIMA_4)}" placeholder="(Penerima 4 - opsional)">
                                        </div>
                                    </div>
                                </div>

                                <div class="doc-statement-text">
                                    Mohon izin, menyampaikan Laporan Harian Kondisi Fasilitas Sisi Udara di PT Angkasa Pura Indonesia 
                                </div>

                                <div class="doc-intro-meta-grid">
                                    <div class="doc-intro-meta-item">
                                        <span class="doc-intro-meta-label">Tanggal</span>
                                        <span class="doc-intro-meta-sep">:</span>
                                        <span class="doc-intro-meta-val"><strong>${formattedDate}</strong></span>
                                    </div>
                                    <div class="doc-intro-meta-item">
                                        <span class="doc-intro-meta-label">Petugas Pengirim</span>
                                        <span class="doc-intro-meta-sep">:</span>
                                        <span class="doc-intro-meta-val"><strong style="color: #0284c7;">${senderName}</strong></span>
                                    </div>
                                    <div class="doc-intro-meta-item">
                                        <span class="doc-intro-meta-label">Wilayah</span>
                                        <span class="doc-intro-meta-sep">:</span>
                                        <span class="doc-intro-meta-val">Region II</span>
                                    </div>
                                    <div class="doc-intro-meta-item">
                                        <span class="doc-intro-meta-label">Unit Cabang</span>
                                        <span class="doc-intro-meta-sep">:</span>
                                        <span class="doc-intro-meta-val">1. ${branchCode}</span>
                                    </div>
                                    <div class="doc-intro-meta-item">
                                        <span class="doc-intro-meta-label">Status Editor</span>
                                        <span class="doc-intro-meta-sep">:</span>
                                        <span class="doc-intro-meta-val" style="color: #0284c7; font-weight: 800;"><i class="fa-solid fa-pen-to-square me-1"></i> Mode Koreksi Mandiri DH</span>
                                    </div>
                                </div>
                            </div>

                            <!-- A. RUNWAY -->
                            <div class="doc-section-head">
                                <div class="doc-section-badge">A</div>
                                <h2 class="doc-section-heading">RUNWAY</h2>
                            </div>
                            <div class="doc-pairs-container">
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">•  Kondisi keseluruhan runway</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <select name="RUNWAY_KONDISI" class="doc-inline-select status-select">
                                            <option value="SERVICEABLE" ${sel(d.RUNWAY_KONDISI, 'SERVICEABLE')}>SERVICEABLE</option>
                                            <option value="UNSERVICEABLE" ${sel(d.RUNWAY_KONDISI, 'UNSERVICEABLE')}>UNSERVICEABLE</option>
                                            <option value="BAIK" ${sel(d.RUNWAY_KONDISI, 'BAIK')}>BAIK</option>
                                            <option value="RUSAK" ${sel(d.RUNWAY_KONDISI, 'RUSAK')}>RUSAK</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">•  Performance pavement</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="text" name="RUNWAY_PCI" class="doc-inline-input num-input" value="${safe(d.RUNWAY_PCI || '100')}">
                                            <span class="doc-inline-suffix">% PCI</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jml Titik Rusak</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="RUNWAY_TITIK_RUSAK" class="doc-inline-input num-input" value="${safe(d.RUNWAY_TITIK_RUSAK || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jenis kerusakan</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div style="display:flex; flex-direction:column; gap:0.4rem; width:100%; max-width:550px;">
                                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                                <span style="font-size:0.8rem; color:#64748b; width:75px; flex-shrink:0;">Diperbaiki:</span>
                                                <input type="text" name="RUNWAY_JENIS_DIPERBAIKI" class="doc-inline-input" value="${safe(d.RUNWAY_JENIS_DIPERBAIKI)}" placeholder="Contoh: Crack / Spalling / Nihil">
                                            </div>
                                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                                <span style="font-size:0.8rem; color:#64748b; width:75px; flex-shrink:0;">Belum:</span>
                                                <input type="text" name="RUNWAY_JENIS_BELUM" class="doc-inline-input" value="${safe(d.RUNWAY_JENIS_BELUM)}" placeholder="Contoh: Raveling / Depresi / Nihil">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jml titik yang sudah diperbaiki</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="RUNWAY_TITIK_DIPERBAIKI" class="doc-inline-input num-input" style="color: #16a34a; font-weight: 700;" value="${safe(d.RUNWAY_TITIK_DIPERBAIKI || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jml titik yang belum diperbaiki</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="RUNWAY_TITIK_BELUM" class="doc-inline-input num-input" style="color: #ea580c; font-weight: 700;" value="${safe(d.RUNWAY_TITIK_BELUM || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jml titik rusak berulang > 1x</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="RUNWAY_TITIK_BERULANG" class="doc-inline-input num-input" value="${safe(d.RUNWAY_TITIK_BERULANG || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>

                                <!-- Subgroup Marka Runway -->
                                <div class="doc-subgroup-card">
                                    <div class="doc-subgroup-title">•  Marka :</div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Standar</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="RUNWAY_MARKA_STD" class="doc-inline-input" style="max-width:280px;" value="${safe(d.RUNWAY_MARKA_STD || '1x / Tahun')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Realisasi</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="RUNWAY_MARKA_REALISASI" class="doc-inline-input" style="max-width:280px;" value="${safe(d.RUNWAY_MARKA_REALISASI || '-')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Performance</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="RUNWAY_MARKA_PERF" class="doc-inline-input" style="max-width:280px; font-weight:700; color:#002b49;" value="${safe(d.RUNWAY_MARKA_PERF || '100%')}">
                                        </div>
                                    </div>
                                </div>

                                <!-- Subgroup Standing Water Runway -->
                                <div class="doc-subgroup-card">
                                    <div class="doc-subgroup-title">•  Standing Water :</div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Pengukuran</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="RUNWAY_STANDING_WATER" class="doc-inline-input" style="max-width:280px;" value="${safe(d.RUNWAY_STANDING_WATER || 'Nihil / Sesuai Standar')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Performance</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="RUNWAY_WATER_PERF" class="doc-inline-input" style="max-width:280px; font-weight:700; color:#002b49;" value="${safe(d.RUNWAY_WATER_PERF || '100%')}">
                                        </div>
                                    </div>
                                </div>

                                <!-- Subgroup Rubber Removal Runway -->
                                <div class="doc-subgroup-card">
                                    <div class="doc-subgroup-title">•  Rubber Removal :</div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Standar ketentuan</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="RUNWAY_RUBBER_STD" class="doc-inline-input" style="max-width:280px;" value="${safe(d.RUNWAY_RUBBER_STD || '4x / thn')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Realisasi</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="RUNWAY_RUBBER_REAL" class="doc-inline-input" style="max-width:280px;" value="${safe(d.RUNWAY_RUBBER_REAL || '-')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Nilai Skid</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="RUNWAY_RUBBER_SKID" class="doc-inline-input" style="max-width:280px; font-weight:700; color:#002b49;" value="${safe(d.RUNWAY_RUBBER_SKID || '-')}">
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- B. TAXIWAY -->
                            <div class="doc-section-head">
                                <div class="doc-section-badge">B</div>
                                <h2 class="doc-section-heading">TAXIWAY</h2>
                            </div>
                            <div class="doc-pairs-container">
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">•  Kondisi keseluruhan Taxiway</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div style="display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap;">
                                            <select name="TAXIWAY_STATUS" class="doc-inline-select status-select">
                                                <option value="SERVICEABLE" ${sel(d.TAXIWAY_STATUS, 'SERVICEABLE')}>SERVICEABLE</option>
                                                <option value="UNSERVICEABLE" ${sel(d.TAXIWAY_STATUS, 'UNSERVICEABLE')}>UNSERVICEABLE</option>
                                                <option value="BAIK" ${sel(d.TAXIWAY_STATUS, 'BAIK')}>BAIK</option>
                                                <option value="RUSAK" ${sel(d.TAXIWAY_STATUS, 'RUSAK')}>RUSAK</option>
                                            </select>
                                            <span style="font-size:0.8rem; color:#64748b;">Nama TWY:</span>
                                            <input type="text" name="TAXIWAY_NAMA" class="doc-inline-input" style="max-width:160px;" value="${safe(d.TAXIWAY_NAMA || 'TWY A, B, C')}" placeholder="TWY A, B, C">
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">•  Performance pavement</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="text" name="TAXIWAY_PCI" class="doc-inline-input num-input" value="${safe(d.TAXIWAY_PCI || '100')}">
                                            <span class="doc-inline-suffix">% PCI</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jml Titik Rusak</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="TWY_TITIK_RUSAK" class="doc-inline-input num-input" value="${safe(d.TWY_TITIK_RUSAK || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jenis kerusakan</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div style="display:flex; flex-direction:column; gap:0.4rem; width:100%; max-width:550px;">
                                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                                <span style="font-size:0.8rem; color:#64748b; width:75px; flex-shrink:0;">Diperbaiki:</span>
                                                <input type="text" name="TWY_JENIS_DIPERBAIKI" class="doc-inline-input" value="${safe(d.TWY_JENIS_DIPERBAIKI)}" placeholder="Contoh: Crack filling, patch">
                                            </div>
                                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                                <span style="font-size:0.8rem; color:#64748b; width:75px; flex-shrink:0;">Belum:</span>
                                                <input type="text" name="TWY_JENIS_BELUM" class="doc-inline-input" value="${safe(d.TWY_JENIS_BELUM)}" placeholder="Contoh: Spalling / Nihil">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jml titik yang sudah diperbaiki</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="TWY_TITIK_DIPERBAIKI" class="doc-inline-input num-input" style="color: #16a34a; font-weight: 700;" value="${safe(d.TWY_TITIK_DIPERBAIKI || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jml titik yang belum diperbaiki</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="TWY_TITIK_BELUM" class="doc-inline-input num-input" style="color: #ea580c; font-weight: 700;" value="${safe(d.TWY_TITIK_BELUM || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jml titik rusak berulang > 1x</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="TWY_TITIK_BERULANG" class="doc-inline-input num-input" value="${safe(d.TWY_TITIK_BERULANG || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>

                                <!-- Subgroup Marka Taxiway -->
                                <div class="doc-subgroup-card">
                                    <div class="doc-subgroup-title">•  Marka :</div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Standar</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="TWY_MARKA_STD" class="doc-inline-input" style="max-width:280px;" value="${safe(d.TWY_MARKA_STD || '1x / Tahun')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Realisasi</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="TWY_MARKA_REALISASI" class="doc-inline-input" style="max-width:280px;" value="${safe(d.TWY_MARKA_REALISASI || '-')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Performance</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="TWY_MARKA_PERF" class="doc-inline-input" style="max-width:280px; font-weight:700; color:#002b49;" value="${safe(d.TWY_MARKA_PERF || '100%')}">
                                        </div>
                                    </div>
                                </div>

                                <!-- Subgroup Standing Water Taxiway -->
                                <div class="doc-subgroup-card">
                                    <div class="doc-subgroup-title">•  Standing Water :</div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Pengukuran</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="TWY_STANDING_WATER" class="doc-inline-input" style="max-width:280px;" value="${safe(d.TWY_STANDING_WATER || 'Nihil / Sesuai Standar')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Performance</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <strong style="color: #002b49;">100%</strong>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- C. APRON -->
                            <div class="doc-section-head">
                                <div class="doc-section-badge">C</div>
                                <h2 class="doc-section-heading">APRON</h2>
                            </div>
                            <div class="doc-pairs-container">
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">•  Kondisi keseluruhan. Apron</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <select name="APRON_KONDISI" class="doc-inline-select status-select">
                                            <option value="SERVICEABLE" ${sel(d.APRON_KONDISI, 'SERVICEABLE')}>SERVICEABLE</option>
                                            <option value="UNSERVICEABLE" ${sel(d.APRON_KONDISI, 'UNSERVICEABLE')}>UNSERVICEABLE</option>
                                            <option value="BAIK" ${sel(d.APRON_KONDISI, 'BAIK')}>BAIK</option>
                                            <option value="RUSAK" ${sel(d.APRON_KONDISI, 'RUSAK')}>RUSAK</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">•  Performance pavement</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="text" name="APRON_PCI" class="doc-inline-input num-input" value="${safe(d.APRON_PCI || '100')}">
                                            <span class="doc-inline-suffix">% PCI</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jumlah Lokasi Perbaikan</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="APN_TITIK_RUSAK" class="doc-inline-input num-input" value="${safe(d.APN_TITIK_RUSAK || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jenis kerusakan</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div style="display:flex; flex-direction:column; gap:0.4rem; width:100%; max-width:550px;">
                                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                                <span style="font-size:0.8rem; color:#64748b; width:75px; flex-shrink:0;">Diperbaiki:</span>
                                                <input type="text" name="APN_JENIS_DIPERBAIKI" class="doc-inline-input" value="${safe(d.APN_JENIS_DIPERBAIKI)}" placeholder="Contoh: Joint sealant / Spalling">
                                            </div>
                                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                                <span style="font-size:0.8rem; color:#64748b; width:75px; flex-shrink:0;">Belum:</span>
                                                <input type="text" name="APN_JENIS_BELUM" class="doc-inline-input" value="${safe(d.APN_JENIS_BELUM)}" placeholder="Contoh: Retak sudut / Nihil">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Realisasi Perbaikan</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="APN_TITIK_DIPERBAIKI" class="doc-inline-input num-input" style="color: #16a34a; font-weight: 700;" value="${safe(d.APN_TITIK_DIPERBAIKI || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Rencana Perbaikan</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="APN_TITIK_BELUM" class="doc-inline-input num-input" style="color: #ea580c; font-weight: 700;" value="${safe(d.APN_TITIK_BELUM || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Jml titik rusak berulang > 1x</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <div class="doc-inline-group">
                                            <input type="number" min="0" name="APN_TITIK_BERULANG" class="doc-inline-input num-input" value="${safe(d.APN_TITIK_BERULANG || '0')}">
                                            <span class="doc-inline-suffix">titik</span>
                                        </div>
                                    </div>
                                </div>

                                <!-- Subgroup Marka Apron -->
                                <div class="doc-subgroup-card">
                                    <div class="doc-subgroup-title">•  Marka :</div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Standar</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="APN_MARKA_STD" class="doc-inline-input" style="max-width:280px;" value="${safe(d.APN_MARKA_STD || '1x / Tahun')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Realisasi</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="APN_MARKA_REALISASI" class="doc-inline-input" style="max-width:280px;" value="${safe(d.APN_MARKA_REALISASI || '-')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Performance</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="APN_MARKA_PERF" class="doc-inline-input" style="max-width:280px; font-weight:700; color:#002b49;" value="${safe(d.APN_MARKA_PERF || '100%')}">
                                        </div>
                                    </div>
                                </div>

                                <!-- Subgroup Standing Water Apron -->
                                <div class="doc-subgroup-card">
                                    <div class="doc-subgroup-title">•  Standing Water :</div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Pengukuran</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <input type="text" name="APN_STANDING_WATER" class="doc-inline-input" style="max-width:280px;" value="${safe(d.APN_STANDING_WATER || 'Nihil / Sesuai Standar')}">
                                        </div>
                                    </div>
                                    <div class="doc-pair-row sub-row">
                                        <div class="doc-pair-key sub-key">Performance</div>
                                        <div class="doc-pair-sep">:</div>
                                        <div class="doc-pair-val">
                                            <strong style="color: #002b49;">100%</strong>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- D. PEMOTONGAN RUMPUT -->
                            <div class="doc-section-head">
                                <div class="doc-section-badge">D</div>
                                <h2 class="doc-section-heading">PEMOTONGAN RUMPUT</h2>
                            </div>
                            <div class="doc-pairs-container">
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Standar</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <input type="text" name="RUMPUT_STD" class="doc-inline-input" style="max-width:280px;" value="${safe(d.RUMPUT_STD || '12 x / 1 Tahun')}">
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Realisasi</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <input type="text" name="RUMPUT_REALISASI" class="doc-inline-input" style="max-width:280px;" value="${safe(d.RUMPUT_REALISASI || '-')}">
                                    </div>
                                </div>
                                <div class="doc-pair-row">
                                    <div class="doc-pair-key">Performance</div>
                                    <div class="doc-pair-sep">:</div>
                                    <div class="doc-pair-val">
                                        <input type="text" name="RUMPUT_PERF" class="doc-inline-input" style="max-width:280px; font-weight:700; color:#002b49;" value="${safe(d.RUMPUT_PERF || '100%')}">
                                    </div>
                                </div>
                            </div>

                            <!-- E. CATATAN KHUSUS -->
                            <div class="doc-section-head">
                                <div class="doc-section-badge">E</div>
                                <h2 class="doc-section-heading">CATATAN KHUSUS</h2>
                            </div>
                            <div style="margin-bottom: 2rem;">
                                <div class="doc-inline-notes-list">
                                    ${[1, 2, 3, 4, 5, 6, 7].map(num => `
                                    <div class="doc-inline-note-item">
                                        <span class="doc-inline-note-num">${num}.</span>
                                        <input type="text" name="CATATAN_${num}" class="doc-inline-input" value="${safe(d['CATATAN_' + num])}" placeholder="(Catatan ke-${num}, kosongkan jika tidak ada)">
                                    </div>
                                    `).join('')}
                                </div>
                            </div>

                            <!-- LEMBAR PENGESAHAN DOKUMEN -->
                            <div class="doc-sign-wrapper">
                                <div class="doc-sign-title">LEMBAR PENGESAHAN LAPORAN</div>
                                <div class="doc-sign-grid">
                                    <div class="doc-sign-col">
                                        <div class="doc-sign-role">Dilaporkan Oleh:</div>
                                        <div class="doc-sign-dept">Petugas Sisi Udara (Airside) — Kantor Cabang ${branchCode}</div>
                                        <div class="doc-sign-spacer"></div>
                                        <div class="doc-sign-name">${fmt(rep.submitted_by, 'Petugas Airside')}</div>
                                        ${rep.submitted_by_username ? `<div style="font-size:0.75rem; color:#0284c7; font-weight:600; margin-top:0.15rem;"><i class="fa-solid fa-user-tag me-1"></i>@${rep.submitted_by_username}</div>` : ''}
                                        <div class="doc-sign-meta">Tanggal Pengajuan: ${formattedDate}</div>
                                    </div>
                                    <div class="doc-sign-col">
                                        <div class="doc-sign-role">Diteliti & Disetujui Oleh:</div>
                                        <div class="doc-sign-dept">Department Head — Kantor Cabang ${branchCode}</div>
                                        <div class="doc-sign-spacer"></div>
                                        <div class="doc-sign-name">{{ current_user.name | default('Department Head') }}</div>
                                        <div class="doc-sign-meta">Status: <span style="font-weight: 700; color: #0284c7;">Sedang Mengoreksi Dokumen</span></div>
                                    </div>
                                </div>

                                <!-- Sticky / Bottom Action Bar -->
                                <div class="dh-edit-action-bar no-print">
                                    <div class="dh-edit-action-left">
                                        <button type="button" class="btn-dh-edit-cancel" onclick="openDetailModal('${rep.report_id}')">
                                            <i class="fa-solid fa-arrow-left me-1"></i> Batal & Kembali ke Pratinjau
                                        </button>
                                    </div>
                                    <div class="dh-edit-action-right" style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
                                        <button type="button" class="btn-dh-edit-save" onclick="submitDhSelfEdit('${rep.report_id}', false)">
                                            <i class="fa-solid fa-floppy-disk me-1"></i> Simpan Koreksi (Draf)
                                        </button>
                                        <button type="button" class="btn-dh-edit-approve" onclick="submitDhSelfEdit('${rep.report_id}', true)">
                                            <i class="fa-solid fa-circle-check me-1"></i> Simpan & Langsung Sahkan
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- FOOTER RESMI DOKUMEN -->
                            <div class="doc-footer-bar">
                                <div class="doc-footer-left">
                                    <strong>PT Angkasa Pura Indonesia</strong> • Regional II — Sistem Laporan Operasional Sisi Udara
                                </div>
                                <div class="doc-footer-right">
                                    Dokumen Resmi Laporan Airside • ${rep.report_id || '-'}
                                </div>
                            </div>
                        </div>
                    </form>
                    `;
                } else {
                    contentBox.innerHTML = `<div class="alert alert-danger" style="margin:2rem;">${res.error || 'Gagal memuat formulir koreksi.'}</div>`;
                }
'@

$idxStart = $content.IndexOf($startMarker)
$idxEnd = $content.IndexOf($endMarker) + $endMarker.Length

$newContent = $content.Substring(0, $idxStart) + $newBody + $content.Substring($idxEnd)
[System.IO.File]::WriteAllText($targetFile, $newContent, [System.Text.Encoding]::UTF8)

Write-Host "SUCCESS: Option 1 Inline Live Document Editor successfully injected!"
