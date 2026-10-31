/**
 * LOAD TRACK — Frontend Application Logic
 * Integrates plain HTML/JS with Flask REST API via fetch()
 */

const API_BASE = window.location.origin.includes('5000') || window.location.origin.includes('127.0.0.1')
    ? '' 
    : 'http://localhost:5000';

let selectedSampleFilename = null;
let uploadedFile = null;
let currentTab = 'operatorTab';
let expandedRowId = null;

// DOM Elements Initialization
document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initTabs();
    initDropzone();
    initSampleGrid();
    initEventListeners();
    loadDashboardStats();
    loadChallansTable();
    loadTollGateDashboard();
});

/* ==================== SYSTEM CLOCK ==================== */
function initClock() {
    const clockEl = document.getElementById('systemClock');
    const updateTime = () => {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString('en-US', { hour12: false }) + ' IST';
    };
    updateTime();
    setInterval(updateTime, 1000);
}

/* ==================== TAB NAVIGATION ==================== */
function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');

    const switchTab = (targetId) => {
        const tabBtn = document.querySelector(`.nav-tab[data-tab="${targetId}"]`);
        if (!tabBtn) return;
        tabs.forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        tabBtn.classList.add('active');
        const targetEl = document.getElementById(targetId);
        if (targetEl) targetEl.classList.add('active');
        currentTab = targetId;

        if (targetId === 'rtoTab') {
            loadDashboardStats();
            loadChallansTable();
        } else if (targetId === 'liveDashboardTab') {
            loadTollGateDashboard();
        }
    };

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.getAttribute('data-tab');
            switchTab(target);
        });
    });

    // Support direct linking via URL query param (?tab=liveDashboardTab) or URL hash (#liveDashboardTab)
    const urlParams = new URLSearchParams(window.location.search);
    const paramTab = urlParams.get('tab');
    const hashTab = window.location.hash.replace('#', '');
    const activeTabTarget = paramTab || hashTab;

    if (activeTabTarget && document.getElementById(activeTabTarget)) {
        switchTab(activeTabTarget);
    }
}

/* ==================== SAMPLE IMAGES GRID ==================== */
async function initSampleGrid() {
    const gridEl = document.getElementById('sampleGrid');
    try {
        const response = await fetch(`${API_BASE}/api/samples`);
        const data = await response.json();

        if (data.success && data.samples.length > 0) {
            gridEl.innerHTML = '';
            data.samples.forEach(sample => {
                const card = document.createElement('div');
                card.className = 'sample-card';
                card.innerHTML = `
                    <img src="${API_BASE}${sample.url}" alt="${sample.plate}">
                    <span>${sample.plate}</span>
                `;
                card.addEventListener('click', () => selectSampleImage(sample.filename, card));
                gridEl.appendChild(card);
            });
        } else {
            gridEl.innerHTML = '<div class="sample-loading">No sample images available</div>';
        }
    } catch (err) {
        console.error('Failed to load sample images:', err);
        gridEl.innerHTML = '<div class="sample-loading">Samples offline</div>';
    }
}

function selectSampleImage(filename, cardElement) {
    document.querySelectorAll('.sample-card').forEach(c => c.classList.remove('active'));
    cardElement.classList.add('active');
    selectedSampleFilename = filename;
    uploadedFile = null;

    // Reset dropzone preview
    document.getElementById('dropzoneContent').classList.remove('hidden');
    document.getElementById('previewBox').classList.add('hidden');
    document.getElementById('imageInput').value = '';

    showToast(`Selected test plate sample: ${filename.replace('_', ' ').replace('.jpg', '')}`, 'info');
}

/* ==================== DROPZONE & FILE UPLOAD ==================== */
function initDropzone() {
    const dropzone = document.getElementById('dropzone');
    const imageInput = document.getElementById('imageInput');
    const imagePreview = document.getElementById('imagePreview');
    const dropzoneContent = document.getElementById('dropzoneContent');
    const previewBox = document.getElementById('previewBox');
    const removeImgBtn = document.getElementById('removeImgBtn');

    imageInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileSelection(e.target.files[0]);
        }
    });

    removeImgBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        uploadedFile = null;
        imageInput.value = '';
        dropzoneContent.classList.remove('hidden');
        previewBox.classList.add('hidden');
    });
}

function handleFileSelection(file) {
    uploadedFile = file;
    selectedSampleFilename = null;
    document.querySelectorAll('.sample-card').forEach(c => c.classList.remove('active'));

    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('imagePreview').src = e.target.result;
        document.getElementById('dropzoneContent').classList.add('hidden');
        document.getElementById('previewBox').classList.remove('hidden');
    };
    reader.readAsDataURL(file);
}

/* ==================== EVENT LISTENERS ==================== */
function initEventListeners() {
    // Auto-Simulate Weight Button
    document.getElementById('autoSimulateBtn').addEventListener('click', () => {
        const weights = [18500, 27400, 34200, 39800, 44500, 48200, 52100];
        const randomWeight = weights[Math.floor(Math.random() * weights.length)];
        document.getElementById('weightInput').value = randomWeight;
        showToast(`Weighbridge sensor calibrated to ${randomWeight.toLocaleString()} kg`, 'info');
    });

    // Scan Vehicle Button
    document.getElementById('scanBtn').addEventListener('click', handleScanVehicle);

    // Refresh Table Button
    document.getElementById('refreshTableBtn').addEventListener('click', () => {
        loadDashboardStats();
        loadChallansTable();
        showToast('RTO Registry refreshed', 'info');
    });

    // Refresh Live Toll Dashboard
    document.getElementById('refreshLiveDashboardBtn').addEventListener('click', () => {
        loadTollGateDashboard();
        showToast('Toll Gate Dashboard feeds updated', 'info');
    });

    // Status Filter Change
    document.getElementById('statusFilter').addEventListener('change', loadChallansTable);

    // Modal Close
    document.getElementById('closeModalBtn').addEventListener('click', () => {
        document.getElementById('vehicleModal').classList.add('hidden');
    });
    document.getElementById('vehicleModal').addEventListener('click', (e) => {
        if (e.target.id === 'vehicleModal') {
            document.getElementById('vehicleModal').classList.add('hidden');
        }
    });
}

/* ==================== SCAN VEHICLE FUNCTION ==================== */
async function handleScanVehicle() {
    const scanBtn = document.getElementById('scanBtn');
    const weightInput = document.getElementById('weightInput');
    const manualPlateInput = document.getElementById('manualPlateInput');
    const plazaSelect = document.getElementById('plazaSelect');
    const simModeSelect = document.getElementById('simModeSelect');

    const weightVal = parseInt(weightInput.value, 10);
    if (!weightVal || weightVal <= 0) {
        showToast('Please enter a valid weighbridge weight (in kg).', 'warning');
        return;
    }

    if (!uploadedFile && !selectedSampleFilename && !manualPlateInput.value.trim()) {
        showToast('Please select a sample image, upload a plate photo, or type a plate number.', 'warning');
        return;
    }

    // Prepare FormData payload
    const formData = new FormData();
    formData.append('weight', weightVal);
    formData.append('toll_plaza', plazaSelect.value);
    formData.append('simulation_mode', simModeSelect.value);

    if (manualPlateInput.value.trim()) {
        formData.append('plate_number', manualPlateInput.value.trim());
    }

    if (uploadedFile) {
        formData.append('image', uploadedFile);
    } else if (selectedSampleFilename) {
        formData.append('sample_filename', selectedSampleFilename);
    }

    // UI Loading state
    scanBtn.disabled = true;
    scanBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> RUNNING SENSORS & COMPOSITE SCORING...';

    try {
        const response = await fetch(`${API_BASE}/api/scan`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            renderScanResult(data);
            showToast(`Scan complete for ${data.vehicle.plate_number}. Score: ${data.composite_score}%`, 'success');
            loadDashboardStats();
            loadTollGateDashboard();
        } else {
            showToast(data.error || 'Scan processing failed.', 'danger');
        }

    } catch (err) {
        console.error('Scan API Error:', err);
        showToast('Connection error connecting to Flask backend.', 'danger');
    } finally {
        scanBtn.disabled = false;
        scanBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> SCAN VEHICLE & PROCESS SENSORS';
    }
}

/* ==================== RENDER SCAN RESULT ==================== */
function renderScanResult(data) {
    document.getElementById('emptyResultState').classList.add('hidden');
    document.getElementById('resultContainer').classList.remove('hidden');

    const vehicle = data.vehicle;
    const scan = data.scan;
    const ocr = data.ocr;
    const challan = data.challan;

    // Top Result Badge
    const badgeEl = document.getElementById('resultBadge');
    if (data.classification === 'underload') {
        badgeEl.className = 'badge badge-success';
        badgeEl.textContent = 'PASSED • UNDERLOAD';
    } else if (data.classification === 'moderate') {
        badgeEl.className = 'badge badge-warning';
        badgeEl.textContent = 'PASSED • MODERATE';
    } else if (data.classification === 'overload_modification_flag') {
        badgeEl.className = 'badge badge-danger';
        badgeEl.textContent = 'FLAGGED • STRUCTURAL MODIFICATION';
    } else {
        badgeEl.className = 'badge badge-danger';
        badgeEl.textContent = 'VIOLATION • OVERLOAD';
    }

    // OCR Plate Info
    document.getElementById('resultPlateNumber').textContent = vehicle.plate_number;
    document.getElementById('resultConfidence').innerHTML = `<i class="fa-solid fa-microchip"></i> OCR Match • ${ocr.raw_text || vehicle.plate_number}`;

    const plateImg = document.getElementById('resultPlateImg');
    if (ocr.image_url) {
        plateImg.src = `${API_BASE}${ocr.image_url}`;
    } else {
        plateImg.src = 'https://via.placeholder.com/140x60/1a1d21/ffc933?text=NO+PLATE+IMG';
    }

    // Composite Score
    document.getElementById('compositeScoreVal').textContent = `${scan.composite_score}%`;

    // Vehicle Specs
    document.getElementById('resModel').textContent = vehicle.model_name;
    document.getElementById('resOwner').textContent = vehicle.owner_name;
    document.getElementById('resCapacity').textContent = `${vehicle.certified_capacity_kg.toLocaleString()} kg`;
    document.getElementById('resDimensions').textContent = `${vehicle.certified_length_mm}×${vehicle.certified_width_mm}×${vehicle.certified_height_mm}mm (${vehicle.certified_axle_count} Axles)`;

    // Multi-sensor readings display
    document.getElementById('sensorWeight').textContent = `${scan.actual_weight_kg.toLocaleString()} kg (${scan.weight_deviation_pct}%)`;
    document.getElementById('sensorAxles').textContent = `${scan.measured_axle_count} Axles (${scan.axle_deviation_pct}%)`;
    document.getElementById('sensorLength').textContent = `${scan.measured_length_mm} mm (${scan.length_deviation_pct}%)`;
    document.getElementById('sensorHeight').textContent = `${scan.measured_height_mm} mm (${scan.height_deviation_pct}%)`;
    document.getElementById('sensorVolume').textContent = `${scan.measured_volume_m3} m³ (${scan.volume_deviation_pct}%)`;
    document.getElementById('sensorShapeMatch').textContent = `${scan.camera_shape_match_pct}% Match`;

    // Weight Meter
    const pct = scan.weight_deviation_pct || data.load_percentage;
    document.getElementById('resLoadPct').textContent = `${pct}%`;
    document.getElementById('resActualWeight').textContent = `${scan.actual_weight_kg.toLocaleString()} kg`;
    document.getElementById('resCertifiedWeight').textContent = `${vehicle.certified_capacity_kg.toLocaleString()} kg`;

    const fillBar = document.getElementById('meterBarFill');
    const capPct = Math.min(135, pct);
    fillBar.style.width = `${(capPct / 135) * 100}%`;

    // Classification Card
    const cardEl = document.getElementById('classificationCard');
    const iconEl = document.getElementById('classIcon');
    const titleEl = document.getElementById('classTitle');
    const descEl = document.getElementById('classDesc');

    if (data.classification === 'underload') {
        cardEl.className = 'classification-card underload';
        iconEl.innerHTML = '<i class="fa-solid fa-circle-check"></i>';
        titleEl.textContent = 'COMPLIANT LOAD (UNDERLOAD)';
        descEl.textContent = `Vehicle parameters are comfortably within rated specs (Score: ${scan.composite_score}%).`;
    } else if (data.classification === 'moderate') {
        cardEl.className = 'classification-card moderate';
        iconEl.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i>';
        titleEl.textContent = 'NEAR CAPACITY (MODERATE)';
        descEl.textContent = `Vehicle operating near rated specs (Score: ${scan.composite_score}%). Cleared without penalty.`;
    } else if (data.classification === 'overload_modification_flag') {
        cardEl.className = 'classification-card overload';
        iconEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
        titleEl.textContent = 'STRUCTURAL MODIFICATION & OVERLOAD FLAGGED';
        descEl.textContent = `Critical parameter deviation detected (Score: ${scan.composite_score}%). Flagged for RTO Officer inspection & penalty.`;
    } else {
        cardEl.className = 'classification-card overload';
        iconEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i>';
        titleEl.textContent = 'ILLEGAL OVERLOAD DETECTED';
        descEl.textContent = `Vehicle weight exceeds certified GVW capacity (Score: ${scan.composite_score}%). Automated challan issued.`;
    }

    // Challan Box
    const challanBox = document.getElementById('challanAlertBox');
    if (challan) {
        challanBox.classList.remove('hidden');
        document.getElementById('chOffense').textContent = challan.offense_number === 1 ? '1st Offense' : `Repeat Offense (#${challan.offense_number})`;
        document.getElementById('chFine').textContent = `₹${challan.fine_amount.toLocaleString()}`;
        document.getElementById('chStatus').textContent = challan.status.replace(/_/g, ' ').toUpperCase();
        document.getElementById('chStatus').className = challan.status === 'escalated' ? 'badge badge-danger' : 'badge badge-warning';

        const smsEl = document.getElementById('chSms');
        if (smsEl) {
            const smsInfo = challan.sms_dispatch || {};
            const isReal = smsInfo.mode === 'real_twilio';
            smsEl.innerHTML = `<i class="fa-solid fa-paper-plane"></i> ${isReal ? 'TWILIO SMS DISPATCHED' : 'SIMULATED SMS DISPATCHED'}`;
            smsEl.className = isReal ? 'sms-badge sms-real' : 'sms-badge';
        }
    } else {
        challanBox.classList.add('hidden');
    }
}

/* ==================== TOLL GATE LIVE DASHBOARD TABLE ==================== */
async function loadTollGateDashboard() {
    const tbody = document.getElementById('tollDashboardTbody');
    if (!tbody) return;

    try {
        const res = await fetch(`${API_BASE}/api/scans?limit=30`);
        const data = await res.json();

        if (data.success && data.scans.length > 0) {
            tbody.innerHTML = '';
            data.scans.forEach(s => {
                const tr = document.createElement('tr');
                
                // Color coding based on classification
                let rowStyle = '';
                let classBadge = '';
                
                if (s.classification === 'underload') {
                    rowStyle = 'border-left: 4px solid #22c55e; background: rgba(34, 197, 94, 0.05);';
                    classBadge = '<span class="badge badge-success">Underload</span>';
                } else if (s.classification === 'moderate') {
                    rowStyle = 'border-left: 4px solid #eab308; background: rgba(234, 179, 8, 0.05);';
                    classBadge = '<span class="badge badge-warning">Moderate</span>';
                } else if (s.classification === 'overload_modification_flag') {
                    rowStyle = 'border-left: 4px solid #ef4444; background: rgba(239, 68, 68, 0.10);';
                    classBadge = '<span class="badge badge-danger"><i class="fa-solid fa-triangle-exclamation"></i> Modification Flag</span>';
                } else {
                    rowStyle = 'border-left: 4px solid #ef4444; background: rgba(239, 68, 68, 0.08);';
                    classBadge = '<span class="badge badge-danger">Overload</span>';
                }

                tr.style = rowStyle;
                tr.setAttribute('data-scan-id', s.id);

                const isRechecked = s.recheck_flag;

                tr.innerHTML = `
                    <td>
                        <strong class="mono-font" style="font-size:14px; color:var(--accent-yellow);">${s.plate_number}</strong>
                        <div style="font-size:11px; color:var(--text-muted);">${s.model_name || 'Commercial Truck'}</div>
                    </td>
                    <td class="mono-font"><strong>${s.weight_deviation_pct}%</strong></td>
                    <td class="mono-font">${s.axle_deviation_pct}%</td>
                    <td class="mono-font">${s.length_deviation_pct}%</td>
                    <td class="mono-font">${s.height_deviation_pct}%</td>
                    <td class="mono-font">${s.volume_deviation_pct}%</td>
                    <td class="mono-font" style="font-size:14px; font-weight:700;">${s.composite_score}%</td>
                    <td>${classBadge}</td>
                    <td>
                        <div style="display:flex; gap:6px; align-items:center;">
                            <button class="btn btn-secondary btn-sm" onclick="toggleDetailRow(${s.id}, event)" title="View sensor breakdown">
                                <i class="fa-solid fa-circle-info"></i> Details
                            </button>
                            <button class="btn btn-warning btn-sm" id="recheckBtn_${s.id}" onclick="flagForRecheck(${s.id}, event)" ${isRechecked ? 'disabled' : ''}>
                                ${isRechecked ? '<i class="fa-solid fa-check-double"></i> Flagged' : '<i class="fa-solid fa-flag"></i> Flag Re-check'}
                            </button>
                        </div>
                    </td>
                `;

                tbody.appendChild(tr);

                // Hidden Detail Row
                const detailTr = document.createElement('tr');
                detailTr.id = `detailRow_${s.id}`;
                detailTr.className = 'detail-drawer-row hidden';
                detailTr.innerHTML = `
                    <td colspan="9" style="background: #111417; padding: 16px; border-bottom: 2px solid var(--border-color);">
                        <div style="display:grid; grid-template-columns: 240px 1fr; gap:20px;">
                            <div>
                                <img src="${s.image_url ? (API_BASE + s.image_url) : 'https://via.placeholder.com/220x120/1a1d21/ffc933?text=CAMERA+CAP'}" 
                                     alt="Camera Scan" style="width:100%; border-radius:6px; border:1px solid var(--border-color); object-fit:cover;">
                                <div style="font-size:11px; color:var(--text-muted); margin-top:6px; text-align:center;">
                                    Toll Camera Capture • ${s.toll_plaza}
                                </div>
                            </div>
                            <div>
                                <h4 class="mono-font" style="color:var(--accent-yellow); font-size:15px; margin-bottom:10px;">
                                    FULL SENSOR TELEMETRY & BREAKDOWN — SCAN #${s.id}
                                </h4>
                                <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; font-size:12px;">
                                    <div style="background:#1a1d21; padding:10px; border-radius:6px; border:1px solid #2a2e33;">
                                        <div style="color:var(--text-muted); font-size:11px;">WEIGHBRIDGE (WIM)</div>
                                        <div><strong>${s.actual_weight_kg ? s.actual_weight_kg.toLocaleString() : '--'} kg</strong> / ${s.certified_capacity_kg ? s.certified_capacity_kg.toLocaleString() : '--'} kg</div>
                                        <div style="color:${s.weight_deviation_pct > 100 ? '#ef4444' : '#22c55e'}; font-weight:700;">Dev: ${s.weight_deviation_pct}%</div>
                                    </div>
                                    <div style="background:#1a1d21; padding:10px; border-radius:6px; border:1px solid #2a2e33;">
                                        <div style="color:var(--text-muted); font-size:11px;">AXLE COUNTER</div>
                                        <div><strong>${s.measured_axle_count} Axles</strong> / Reg: ${s.certified_axle_count || 3}</div>
                                        <div style="color:${s.axle_deviation_pct > 100 ? '#ef4444' : '#22c55e'}; font-weight:700;">Dev: ${s.axle_deviation_pct}%</div>
                                    </div>
                                    <div style="background:#1a1d21; padding:10px; border-radius:6px; border:1px solid #2a2e33;">
                                        <div style="color:var(--text-muted); font-size:11px;">LiDAR LENGTH × WIDTH</div>
                                        <div><strong>${s.measured_length_mm} × ${s.measured_width_mm} mm</strong></div>
                                        <div style="color:${s.length_deviation_pct > 100 ? '#ef4444' : '#22c55e'}; font-weight:700;">Len Dev: ${s.length_deviation_pct}%</div>
                                    </div>
                                    <div style="background:#1a1d21; padding:10px; border-radius:6px; border:1px solid #2a2e33;">
                                        <div style="color:var(--text-muted); font-size:11px;">IR HEIGHT CURTAIN</div>
                                        <div><strong>${s.measured_height_mm} mm</strong> / Reg: ${s.certified_height_mm || 3800}mm</div>
                                        <div style="color:${s.height_deviation_pct > 100 ? '#ef4444' : '#22c55e'}; font-weight:700;">Dev: ${s.height_deviation_pct}%</div>
                                    </div>
                                    <div style="background:#1a1d21; padding:10px; border-radius:6px; border:1px solid #2a2e33;">
                                        <div style="color:var(--text-muted); font-size:11px;">VOLUME & CLEARANCE</div>
                                        <div><strong>${s.measured_volume_m3 || '--'} m³</strong> | Clearance: ${s.measured_ground_clearance_mm || 290}mm</div>
                                        <div style="color:${s.volume_deviation_pct > 100 ? '#ef4444' : '#22c55e'}; font-weight:700;">Vol Dev: ${s.volume_deviation_pct}%</div>
                                    </div>
                                    <div style="background:#1a1d21; padding:10px; border-radius:6px; border:1px solid #2a2e33;">
                                        <div style="color:var(--text-muted); font-size:11px;">CNN VISUAL SHAPE MATCH</div>
                                        <div style="font-size:16px; font-weight:700; color:var(--accent-yellow);">${s.camera_shape_match_pct || 95.0}% Match</div>
                                        <div style="font-size:10px; color:var(--text-muted);">Against RTO Base Profile</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </td>
                `;
                tbody.appendChild(detailTr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:30px; color:var(--text-muted);">No scan records present on toll gate dashboard.</td></tr>';
        }

    } catch (err) {
        console.error('Error loading toll gate dashboard:', err);
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:var(--status-red);">Failed to fetch live toll dashboard feeds.</td></tr>';
    }
}

function toggleDetailRow(scanId, event) {
    if (event) event.stopPropagation();
    const detailRow = document.getElementById(`detailRow_${scanId}`);
    if (!detailRow) return;

    if (detailRow.classList.contains('hidden')) {
        detailRow.classList.remove('hidden');
    } else {
        detailRow.classList.add('hidden');
    }
}

async function flagForRecheck(scanId, event) {
    if (event) event.stopPropagation();
    const btn = document.getElementById(`recheckBtn_${scanId}`);
    if (btn) btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/scan/${scanId}/recheck`, {
            method: 'POST'
        });
        const data = await response.json();

        if (response.ok && data.success) {
            showToast(`Scan #${scanId} flagged for human officer review! Notification dispatched.`, 'warning');
            if (btn) btn.innerHTML = '<i class="fa-solid fa-check-double"></i> Flagged';
        } else {
            showToast(data.error || 'Failed to flag scan.', 'danger');
            if (btn) btn.disabled = false;
        }
    } catch (err) {
        console.error('Flag recheck error:', err);
        showToast('Error flagging scan for re-check.', 'danger');
        if (btn) btn.disabled = false;
    }
}

/* ==================== RTO DASHBOARD STATS ==================== */
async function loadDashboardStats() {
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        const data = await res.json();
        if (data.success) {
            const stats = data.stats;
            document.getElementById('statScanned').textContent = stats.scanned_today;
            document.getElementById('statOverloads').textContent = stats.overloads_today;
            document.getElementById('statChallans').textContent = stats.active_challans;
            document.getElementById('statSeizures').textContent = stats.seizure_orders;
        }
    } catch (err) {
        console.error('Failed to load stats:', err);
    }
}

/* ==================== CHALLANS TABLE ==================== */
async function loadChallansTable() {
    const tbody = document.getElementById('challansTbody');
    const filterVal = document.getElementById('statusFilter').value;

    try {
        let url = `${API_BASE}/api/challans`;
        if (filterVal) url += `?status=${filterVal}`;

        const res = await fetch(url);
        const data = await res.json();

        if (data.success && data.challans.length > 0) {
            tbody.innerHTML = '';
            data.challans.forEach(c => {
                const tr = document.createElement('tr');
                
                const formattedDate = new Date(c.created_at).toLocaleString('en-IN', {
                    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                });

                let statusBadge = '';
                if (c.status === 'pending_rto_verification') {
                    statusBadge = '<span class="badge badge-warning">PENDING RTO</span>';
                } else if (c.status === 'confirmed') {
                    statusBadge = '<span class="badge badge-success">CONFIRMED</span>';
                } else if (c.status === 'dismissed') {
                    statusBadge = '<span class="badge badge-neutral">DISMISSED</span>';
                } else {
                    statusBadge = '<span class="badge badge-danger">ESCALATED / SEIZURE</span>';
                }

                tr.innerHTML = `
                    <td class="mono-font">#CH-${c.id}</td>
                    <td>
                        <a href="#" class="plate-link mono-font" onclick="openVehicleModal('${c.plate_number}'); return false;">
                            ${c.plate_number}
                        </a>
                    </td>
                    <td>${c.model_name || '--'}</td>
                    <td>
                        <strong class="mono-font">${c.actual_weight_kg ? c.actual_weight_kg.toLocaleString() : '--'} kg</strong>
                        <div style="font-size:10px; color:var(--text-muted);">Score: ${c.composite_score || c.load_percentage}%</div>
                    </td>
                    <td><span class="badge badge-neutral">Offense #${c.offense_number}</span></td>
                    <td class="mono-font price-tag">₹${c.fine_amount.toLocaleString()}</td>
                    <td>${statusBadge}</td>
                    <td style="font-size:11px; color:var(--text-muted);">${formattedDate}</td>
                    <td>
                        ${c.status === 'pending_rto_verification' 
                            ? `<button class="btn btn-secondary btn-sm" onclick="verifyChallan(${c.id})"><i class="fa-solid fa-check"></i> Verify</button>`
                            : `<span style="font-size:11px; color:var(--status-green);"><i class="fa-solid fa-circle-check"></i> Processed</span>`
                        }
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:30px; color:var(--text-muted);">No challan records found matching selected filter.</td></tr>';
        }
    } catch (err) {
        console.error('Error loading table:', err);
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; color:var(--status-red);">Failed to connect to backend server.</td></tr>';
    }
}

/* ==================== VERIFY CHALLAN ACTION ==================== */
async function verifyChallan(challanId) {
    try {
        const response = await fetch(`${API_BASE}/api/challans/${challanId}/verify`, {
            method: 'POST'
        });
        const data = await response.json();

        if (response.ok && data.success) {
            showToast(`Challan #${challanId} verified & confirmed by RTO officer.`, 'success');
            loadDashboardStats();
            loadChallansTable();
        } else {
            showToast(data.error || 'Verification failed.', 'danger');
        }
    } catch (err) {
        console.error('Verify error:', err);
        showToast('Error verifying challan.', 'danger');
    }
}

/* ==================== VEHICLE DOSSIER MODAL ==================== */
async function openVehicleModal(plateNumber) {
    const modal = document.getElementById('vehicleModal');
    const modalBody = document.getElementById('modalBody');
    modal.classList.remove('hidden');
    modalBody.innerHTML = '<div class="modal-loading"><i class="fa-solid fa-spinner fa-spin"></i> Fetching vehicle audit dossier...</div>';

    try {
        const res = await fetch(`${API_BASE}/api/vehicles/${encodeURIComponent(plateNumber)}`);
        const data = await res.json();

        if (data.success) {
            const v = data.vehicle;
            const scans = data.scans;
            const challans = data.challans;

            let historyHtml = `
                <div style="margin-bottom:16px; background:#181b1e; padding:14px; border-radius:6px; border:1px solid var(--border-color);">
                    <h4 class="mono-font" style="color:var(--accent-yellow); font-size:20px;">${v.plate_number}</h4>
                    <p style="font-size:13px; color:var(--text-muted);">${v.model_name} (${v.manufacturer})</p>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px; margin-top:10px; font-size:12px;">
                        <div><strong>Owner:</strong> ${v.owner_name}</div>
                        <div><strong>Phone:</strong> ${v.owner_phone}</div>
                        <div><strong>Certified Specs:</strong> ${v.certified_length_mm}×${v.certified_width_mm}×${v.certified_height_mm}mm (${v.certified_axle_count} Axles)</div>
                        <div><strong>GVW Capacity:</strong> ${v.certified_capacity_kg.toLocaleString()} kg</div>
                        <div><strong>Violation Count:</strong> ${v.violation_count}</div>
                        <div><strong>Status:</strong> ${v.status}</div>
                    </div>
                </div>

                <h4 style="font-family:var(--font-heading); margin-bottom:10px;">MULTI-SENSOR SCAN HISTORY (${scans.length})</h4>
                <div style="max-height:180px; overflow-y:auto; margin-bottom:16px;">
                    <table class="data-table" style="font-size:11px;">
                        <thead>
                            <tr><th>Time</th><th>Weight</th><th>Axles</th><th>Dimensions</th><th>Score</th><th>Class</th></tr>
                        </thead>
                        <tbody>
                            ${scans.map(s => `
                                <tr>
                                    <td>${new Date(s.timestamp).toLocaleString('en-IN')}</td>
                                    <td class="mono-font">${s.actual_weight_kg.toLocaleString()} kg</td>
                                    <td class="mono-font">${s.measured_axle_count}</td>
                                    <td class="mono-font">${s.measured_length_mm}×${s.measured_height_mm}mm</td>
                                    <td class="mono-font" style="font-weight:700;">${s.composite_score}%</td>
                                    <td><span class="badge badge-${s.classification.includes('overload') ? 'danger' : s.classification === 'moderate' ? 'warning' : 'success'}">${s.classification}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>

                <h4 style="font-family:var(--font-heading); margin-bottom:10px;">CHALLAN RECORD (${challans.length})</h4>
                <div>
                    ${challans.length === 0 ? '<p style="font-size:12px; color:var(--text-muted);">No challans issued for this vehicle.</p>' : `
                        <table class="data-table" style="font-size:11px;">
                            <thead><tr><th>ID</th><th>Offense</th><th>Fine</th><th>Status</th></tr></thead>
                            <tbody>
                                ${challans.map(c => `
                                    <tr>
                                        <td class="mono-font">#CH-${c.id}</td>
                                        <td>Offense #${c.offense_number}</td>
                                        <td class="mono-font price-tag">₹${c.fine_amount.toLocaleString()}</td>
                                        <td>${c.status}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    `}
                </div>
            `;
            modalBody.innerHTML = historyHtml;
        } else {
            modalBody.innerHTML = `<div style="color:var(--status-red);">${data.error}</div>`;
        }

    } catch (err) {
        modalBody.innerHTML = '<div style="color:var(--status-red);">Failed to connect to backend server.</div>';
    }
}

/* ==================== TOAST NOTIFICATIONS ==================== */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let icon = 'fa-circle-info';
    if (type === 'success') icon = 'fa-circle-check';
    if (type === 'warning') icon = 'fa-triangle-exclamation';
    if (type === 'danger') icon = 'fa-circle-xmark';

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function roundVal(val) {
    return Math.round(val * 10) / 10;
}
