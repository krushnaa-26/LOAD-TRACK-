/**
 * LOAD TRACK — RTO Mobile Officer App Script
 */

const API_BASE = window.location.origin.includes('5000') || window.location.origin.includes('127.0.0.1')
    ? '' 
    : 'http://localhost:5000';

let currentOfficer = null;
let pollTimer = null;
let currentInspectionNotifId = null;

document.addEventListener('DOMContentLoaded', () => {
    initAuthCheck();
    initLoginForm();
});

/* Quick Login Helper */
function fillLogin(badge, label) {
    document.getElementById('badgeInput').value = badge;
    document.getElementById('passwordInput').value = 'password123';
}

/* Check Existing Session */
async function initAuthCheck() {
    const savedBadge = localStorage.getItem('rto_badge_id');
    if (savedBadge) {
        try {
            const res = await fetch(`${API_BASE}/api/officer/me?badge_id=${savedBadge}`);
            const data = await res.json();
            if (data.success && data.officer) {
                onLoginSuccess(data.officer);
                return;
            }
        } catch (e) {
            console.warn('Session restore error:', e);
        }
    }
    showScreen('loginScreen');
}

/* Login Form Handler */
function initLoginForm() {
    const loginForm = document.getElementById('loginForm');
    const loginAlert = document.getElementById('loginAlert');
    const loginBtn = document.getElementById('loginBtn');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginAlert.classList.add('hidden');

        const badgeId = document.getElementById('badgeInput').value.trim();
        const password = document.getElementById('passwordInput').value.trim();

        loginBtn.disabled = true;
        loginBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AUTHENTICATING...';

        try {
            const res = await fetch(`${API_BASE}/api/officer/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ badge_id: badgeId, password: password })
            });

            const data = await res.json();

            if (res.ok && data.success) {
                localStorage.setItem('rto_badge_id', data.officer.badge_id);
                onLoginSuccess(data.officer);
            } else {
                loginAlert.textContent = data.error || 'Invalid credentials.';
                loginAlert.classList.remove('hidden');
            }
        } catch (err) {
            console.error('Login error:', err);
            loginAlert.textContent = 'Connection error connecting to Flask backend.';
            loginAlert.classList.remove('hidden');
        } finally {
            loginBtn.disabled = false;
            loginBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> OFFICER LOGIN';
        }
    });

    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.removeItem('rto_badge_id');
        if (pollTimer) clearInterval(pollTimer);
        currentOfficer = null;
        showScreen('loginScreen');
    });
}

function onLoginSuccess(officer) {
    currentOfficer = officer;
    document.getElementById('officerName').textContent = officer.name;
    document.getElementById('officerJurisdiction').textContent = officer.jurisdiction_area;

    showScreen('portalScreen');
    showRtoView('notificationsView');

    // Start Real-Time Notification Polling (Every 4 seconds)
    loadNotifications();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(loadNotifications, 4000);
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function showRtoView(viewId, navBtn = null) {
    document.querySelectorAll('.rto-view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');

    if (navBtn) {
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        navBtn.classList.add('active');
    }

    if (viewId === 'notificationsView') {
        loadNotifications();
    } else if (viewId === 'historyView') {
        loadHistory();
    }
}

/* ==================== NOTIFICATIONS POLLING ==================== */
async function loadNotifications() {
    if (!currentOfficer) return;

    try {
        const res = await fetch(`${API_BASE}/api/officer/notifications?badge_id=${currentOfficer.badge_id}`);
        const data = await res.json();

        if (data.success) {
            const unreadCount = data.unread_count;
            const notifs = data.notifications;

            // Badges
            document.getElementById('unreadCountBadge').textContent = `${unreadCount} NEW ALERTS`;
            const bottomBadge = document.getElementById('bottomNavBadge');
            if (unreadCount > 0) {
                bottomBadge.textContent = unreadCount;
                bottomBadge.classList.remove('hidden');
            } else {
                bottomBadge.classList.add('hidden');
            }

            const listEl = document.getElementById('notificationsList');
            if (notifs.length === 0) {
                listEl.innerHTML = '<div class="loading-state"><i class="fa-solid fa-shield-check"></i> No active overload alerts in your jurisdiction.</div>';
                return;
            }

            listEl.innerHTML = '';
            notifs.forEach(n => {
                const card = document.createElement('div');
                card.className = `notif-card ${n.is_read ? 'read' : ''}`;
                
                const formattedTime = new Date(n.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
                const scan = n.scan || {};
                const score = scan.composite_score || '--';

                card.innerHTML = `
                    <div class="notif-header">
                        <span class="notif-plate">${n.plate_number || 'VEHICLE'}</span>
                        <span class="notif-score">Score: ${score}%</span>
                    </div>
                    <div class="notif-msg">${n.message}</div>
                    <div class="notif-footer">
                        <span><i class="fa-solid fa-clock"></i> ${formattedTime}</span>
                        <span style="color:var(--primary-color); font-weight:600;">Tap to Inspect <i class="fa-solid fa-chevron-right"></i></span>
                    </div>
                `;

                card.addEventListener('click', () => openInspectionScreen(n.id));
                listEl.appendChild(card);
            });
        }
    } catch (err) {
        console.error('Polling error:', err);
    }
}

/* ==================== INSPECTION SCREEN ==================== */
async function openInspectionScreen(notifId) {
    currentInspectionNotifId = notifId;
    showRtoView('inspectionView');
    
    // Mark as read immediately
    fetch(`${API_BASE}/api/officer/notifications/${notifId}/read`, { method: 'POST' });

    const container = document.getElementById('inspectionDetailContainer');
    container.innerHTML = '<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Fetching multi-sensor inspection telemetry...</div>';

    try {
        const res = await fetch(`${API_BASE}/api/officer/inspections/${notifId}`);
        const data = await res.json();

        if (data.success) {
            const notif = data.notification;
            const scan = data.scan || {};
            const vehicle = data.vehicle || {};
            const images = data.images || {};
            const challan = data.challan || {};

            const regPhoto = images.registered_rto_photo;
            const scanPhoto = scan.image_url ? (API_BASE + scan.image_url) : images.toll_camera_photo;

            container.innerHTML = `
                <div style="background:#16191d; border:1px solid var(--card-border); border-radius:12px; padding:14px; margin-bottom:14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span class="notif-plate" style="font-size:20px;">${vehicle.plate_number}</span>
                        <span class="badge" style="background:rgba(239, 68, 68, 0.2); color:#ef4444; padding:4px 8px; border-radius:6px; font-weight:700; font-size:12px;">
                            ${scan.classification ? scan.classification.toUpperCase().replace(/_/g, ' ') : 'VIOLATION'}
                        </span>
                    </div>
                    <div style="font-size:12px; color:var(--text-muted);">${vehicle.model_name} • Owner: ${vehicle.owner_name} (${vehicle.owner_phone})</div>
                </div>

                <h4 style="font-size:12px; color:var(--text-muted); margin-bottom:8px; font-weight:700;">VISUAL PROFILES COMPARISON</h4>
                <div class="photo-compare-box">
                    <div class="photo-card">
                        <img src="${regPhoto}" alt="RTO Base Spec">
                        <div class="photo-card-label">RTO REGISTERED PHOTO</div>
                    </div>
                    <div class="photo-card">
                        <img src="${scanPhoto}" alt="Toll Camera Scan">
                        <div class="photo-card-label">TOLL CAMERA SCAN</div>
                    </div>
                </div>

                <div style="background:#16191d; border:1px solid var(--card-border); border-radius:12px; padding:12px; margin-bottom:14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:11px; font-weight:700; color:var(--text-muted);">COMPOSITE DEVIATION SCORE</span>
                        <span class="mono-font" style="font-size:20px; font-weight:700; color:var(--primary-color);">${scan.composite_score || '--'}%</span>
                    </div>
                </div>

                <h4 style="font-size:12px; color:var(--text-muted); margin-bottom:8px; font-weight:700;">MULTI-SENSOR MEASUREMENTS vs RTO SPEC</h4>
                <div class="telemetry-grid">
                    <div class="telem-item">
                        <div class="telem-label">WEIGHT (WIM)</div>
                        <div class="telem-val" style="color:${scan.weight_deviation_pct > 100 ? '#ef4444' : '#10b981'}">${scan.actual_weight_kg ? scan.actual_weight_kg.toLocaleString() : '--'} kg</div>
                        <div style="font-size:10px; color:var(--text-muted);">Reg: ${vehicle.certified_capacity_kg ? vehicle.certified_capacity_kg.toLocaleString() : '--'} kg (${scan.weight_deviation_pct}%)</div>
                    </div>

                    <div class="telem-item">
                        <div class="telem-label">AXLE COUNT</div>
                        <div class="telem-val" style="color:${scan.axle_deviation_pct > 100 ? '#ef4444' : '#10b981'}">${scan.measured_axle_count} Axles</div>
                        <div style="font-size:10px; color:var(--text-muted);">Reg: ${vehicle.certified_axle_count} Axles (${scan.axle_deviation_pct}%)</div>
                    </div>

                    <div class="telem-item">
                        <div class="telem-label">LiDAR LENGTH</div>
                        <div class="telem-val" style="color:${scan.length_deviation_pct > 100 ? '#ef4444' : '#10b981'}">${scan.measured_length_mm} mm</div>
                        <div style="font-size:10px; color:var(--text-muted);">Reg: ${vehicle.certified_length_mm} mm (${scan.length_deviation_pct}%)</div>
                    </div>

                    <div class="telem-item">
                        <div class="telem-label">IR HEIGHT CURTAIN</div>
                        <div class="telem-val" style="color:${scan.height_deviation_pct > 100 ? '#ef4444' : '#10b981'}">${scan.measured_height_mm} mm</div>
                        <div style="font-size:10px; color:var(--text-muted);">Reg: ${vehicle.certified_height_mm} mm (${scan.height_deviation_pct}%)</div>
                    </div>

                    <div class="telem-item">
                        <div class="telem-label">VOLUME DEVIATION</div>
                        <div class="telem-val">${scan.measured_volume_m3} m³</div>
                        <div style="font-size:10px; color:var(--text-muted);">Reg: ${vehicle.certified_volume_m3} m³ (${scan.volume_deviation_pct}%)</div>
                    </div>

                    <div class="telem-item">
                        <div class="telem-label">CNN SHAPE MATCH</div>
                        <div class="telem-val" style="color:var(--primary-color);">${scan.camera_shape_match_pct || 95}%</div>
                        <div style="font-size:10px; color:var(--text-muted);">Visual Profile Match</div>
                    </div>
                </div>

                ${notif.status === 'pending_inspection' ? `
                    <div class="action-buttons-group">
                        <button class="btn-confirm" onclick="actionVerifyViolation(${notif.id})">
                            <i class="fa-solid fa-gavel"></i> CONFIRM VIOLATION → RAISE CHALLAN (₹${challan.fine_amount ? challan.fine_amount.toLocaleString() : '5,000'})
                        </button>
                        <button class="btn-dismiss" onclick="actionDismissViolation(${notif.id})">
                            <i class="fa-solid fa-xmark"></i> DISMISS (FALSE POSITIVE)
                        </button>
                    </div>
                ` : `
                    <div style="text-align:center; padding:14px; background:#1e242b; border-radius:10px; font-weight:700; color:${notif.status === 'confirmed' ? '#ef4444' : '#9ca3af'};">
                        STATUS: ${notif.status.toUpperCase()}
                    </div>
                `}
            `;
        } else {
            container.innerHTML = `<div style="color:var(--status-red);">${data.error}</div>`;
        }
    } catch (err) {
        container.innerHTML = '<div style="color:var(--status-red);">Error connecting to inspection backend.</div>';
    }
}

/* Action: Confirm Violation */
async function actionVerifyViolation(notifId) {
    if (!confirm('Are you sure you want to verify and confirm this violation challan?')) return;

    try {
        const res = await fetch(`${API_BASE}/api/officer/inspections/${notifId}/verify`, { method: 'POST' });
        const data = await res.json();

        if (res.ok && data.success) {
            alert('Violation Confirmed! Challan verified and sent to offender vehicle owner.');
            showRtoView('notificationsView');
        } else {
            alert(data.error || 'Failed to verify violation.');
        }
    } catch (err) {
        alert('Connection error.');
    }
}

/* Action: Dismiss Violation */
async function actionDismissViolation(notifId) {
    if (!confirm('Dismiss this alert as a false positive? No fine will be levied.')) return;

    try {
        const res = await fetch(`${API_BASE}/api/officer/inspections/${notifId}/dismiss`, { method: 'POST' });
        const data = await res.json();

        if (res.ok && data.success) {
            alert('Inspection dismissed as false positive.');
            showRtoView('notificationsView');
        } else {
            alert(data.error || 'Failed to dismiss inspection.');
        }
    } catch (err) {
        alert('Connection error.');
    }
}

/* ==================== HISTORY VIEW ==================== */
async function loadHistory() {
    if (!currentOfficer) return;
    const listEl = document.getElementById('historyList');
    listEl.innerHTML = '<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Fetching officer inspection history...</div>';

    try {
        const res = await fetch(`${API_BASE}/api/officer/history?badge_id=${currentOfficer.badge_id}`);
        const data = await res.json();

        if (data.success && data.history.length > 0) {
            listEl.innerHTML = '';
            data.history.forEach(h => {
                const card = document.createElement('div');
                card.className = 'notif-card read';
                card.style.borderLeftColor = h.status === 'confirmed' ? 'var(--status-red)' : 'var(--text-muted)';
                
                const time = new Date(h.created_at).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });

                card.innerHTML = `
                    <div class="notif-header">
                        <span class="notif-plate">${h.plate_number || 'VEHICLE'}</span>
                        <span class="badge" style="background:${h.status === 'confirmed' ? 'rgba(239, 68, 68, 0.2)' : '#262b33'}; color:${h.status === 'confirmed' ? '#ef4444' : '#9ca3af'}; font-size:10px; padding:2px 6px; border-radius:4px;">
                            ${h.status.toUpperCase()}
                        </span>
                    </div>
                    <div class="notif-msg" style="font-size:11px;">${h.message}</div>
                    <div class="notif-footer">
                        <span><i class="fa-solid fa-clock"></i> ${time}</span>
                    </div>
                `;
                listEl.appendChild(card);
            });
        } else {
            listEl.innerHTML = '<div class="loading-state"><i class="fa-solid fa-box-archive"></i> No past inspection history found.</div>';
        }
    } catch (err) {
        listEl.innerHTML = '<div class="loading-state" style="color:var(--status-red);">Failed to load history.</div>';
    }
}
