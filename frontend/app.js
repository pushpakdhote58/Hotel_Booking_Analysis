/* ============================================================
   Hotel Booking & Reservation Analytics – Dashboard JS
   ============================================================ */

const BASE = window.location.origin;

// ---- Color Palette ----
const COLORS = {
    teal:   '#0F766E',
    amber:  '#D97706',
    blue:   '#0284C7',
    green:  '#059669',
    purple: '#7C3AED',
    red:    '#DC2626',
};
const PALETTE = ['#0F766E','#D97706','#0284C7','#059669','#7C3AED','#DC2626','#0369A1','#B45309','#047857','#6D28D9','#B91C1C','#0E7490'];

// ---- Utility helpers ----
const fmt = {
    num:  (v) => v == null ? '--' : Number(v).toLocaleString('en-US'),
    curr: (v) => v == null ? '--' : '$' + Number(v).toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0}),
    pct:  (v) => v == null ? '--' : Number(v).toFixed(1) + '%',
    dec:  (v) => v == null ? '--' : Number(v).toFixed(2),
};

// ---- Chart registry (so we can destroy on refresh) ----
const charts = {};
function makeChart(id, cfg) {
    if (charts[id]) charts[id].destroy();
    const ctx = document.getElementById(id);
    if (!ctx) return null;
    cfg.options = cfg.options || {};
    cfg.options.responsive = true;
    cfg.options.maintainAspectRatio = false;
    charts[id] = new Chart(ctx.getContext('2d'), cfg);
    return charts[id];
}

// ---- API Fetcher ----
async function api(path) {
    const res = await fetch(`${BASE}${path}`);
    if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
    return res.json();
}

// ---- Connection status ----
async function checkConnection() {
    const dot = document.querySelector('.status-dot');
    const txt = document.querySelector('.status-text');
    try {
        await api('/api/health');
        dot.classList.remove('disconnected');
        txt.textContent = 'Connected';
    } catch {
        dot.classList.add('disconnected');
        txt.textContent = 'Disconnected';
    }
}

// ---- KPI Cards ----
async function loadKPIs() {
    const els = {
        'kpi-total-bookings': null,
        'kpi-occupancy-rate': null,
        'kpi-total-revenue':  null,
        'kpi-avg-stay':       null,
        'kpi-cancel-rate':    null,
        'kpi-avg-price':      null,
    };
    try {
        const d = await api('/api/kpis');
        set('kpi-total-bookings', fmt.num(d.total_bookings));
        set('kpi-occupancy-rate', fmt.pct(d.occupancy_rate));
        set('kpi-total-revenue',  fmt.curr(d.total_revenue));
        set('kpi-avg-stay',       fmt.dec(d.avg_stay_duration) + ' nights');
        set('kpi-cancel-rate',    fmt.pct(d.cancellation_rate));
        set('kpi-avg-price',      fmt.curr(d.avg_room_price));
    } catch {
        Object.keys(els).forEach(id => set(id, 'Error'));
    }
}
function set(id, val) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = val;
    el.classList.remove('skeleton');
}

// ======================================================
// OVERVIEW Charts
// ======================================================
async function loadOverviewCharts() {
    try {
        const [trends, rooms, channels, hotels] = await Promise.all([
            api('/api/trends/monthly'),
            api('/api/rooms'),
            api('/api/channels'),
            api('/api/hotels'),
        ]);

        // Monthly Booking Trend (line)
        makeChart('chartMonthlyTrend', {
            type: 'line',
            data: {
                labels: trends.map(r => r.month || r.arrival_date_month || `${r.arrival_date_year}-${r.arrival_date_month}`),
                datasets: [{
                    label: 'Bookings',
                    data: trends.map(r => r.total_bookings),
                    borderColor: COLORS.teal,
                    backgroundColor: 'rgba(15,118,110,.1)',
                    fill: true,
                    tension: .35,
                    pointRadius: 3,
                }, {
                    label: 'Cancellations',
                    data: trends.map(r => r.cancellations),
                    borderColor: COLORS.red,
                    backgroundColor: 'rgba(220,38,38,.1)',
                    fill: true,
                    tension: .35,
                    pointRadius: 3,
                }],
            },
        });

        // Room Type Count (bar)
        makeChart('chartRoomType', {
            type: 'bar',
            data: {
                labels: rooms.map(r => r.reserved_room_type || r.room_type),
                datasets: [{
                    label: 'Bookings',
                    data: rooms.map(r => r.count),
                    backgroundColor: PALETTE.slice(0, rooms.length),
                    borderRadius: 6,
                }],
            },
            options: { plugins: { legend: { display: false } } },
        });

        // Booking Channel (doughnut)
        makeChart('chartChannel', {
            type: 'doughnut',
            data: {
                labels: channels.map(r => r.distribution_channel || r.channel),
                datasets: [{
                    data: channels.map(r => r.count),
                    backgroundColor: PALETTE.slice(0, channels.length),
                    borderWidth: 2,
                }],
            },
            options: { plugins: { legend: { position: 'bottom' } } },
        });

        // Revenue by Hotel (bar)
        makeChart('chartHotelRevenue', {
            type: 'bar',
            data: {
                labels: hotels.map(r => r.hotel),
                datasets: [{
                    label: 'Revenue',
                    data: hotels.map(r => r.total_revenue || r.revenue),
                    backgroundColor: [COLORS.teal, COLORS.amber],
                    borderRadius: 6,
                }],
            },
            options: { plugins: { legend: { display: false } } },
        });
    } catch (e) { console.error('Overview charts error:', e); }
}

// ======================================================
// REVENUE Charts
// ======================================================
async function loadRevenueCharts() {
    try {
        const [trends, hotels, rooms] = await Promise.all([
            api('/api/trends/monthly'),
            api('/api/hotels'),
            api('/api/rooms'),
        ]);

        // Monthly Revenue Trend (line)
        makeChart('chartRevenueTrend', {
            type: 'line',
            data: {
                labels: trends.map(r => r.month || r.arrival_date_month || `${r.arrival_date_year}-${r.arrival_date_month}`),
                datasets: [{
                    label: 'Revenue',
                    data: trends.map(r => r.monthly_revenue || r.revenue),
                    borderColor: COLORS.blue,
                    backgroundColor: 'rgba(2,132,199,.1)',
                    fill: true,
                    tension: .35,
                    pointRadius: 3,
                }],
            },
        });

        // Revenue by Hotel (horizontal bar)
        makeChart('chartRevenueHotel', {
            type: 'bar',
            data: {
                labels: hotels.map(r => r.hotel),
                datasets: [{
                    label: 'Revenue',
                    data: hotels.map(r => r.total_revenue || r.revenue),
                    backgroundColor: [COLORS.teal, COLORS.amber],
                    borderRadius: 6,
                }],
            },
            options: { indexAxis: 'y' },
        });

        // Revenue by Room Type (bar)
        makeChart('chartRevenueRoom', {
            type: 'bar',
            data: {
                labels: rooms.map(r => r.reserved_room_type || r.room_type),
                datasets: [{
                    label: 'Revenue',
                    data: rooms.map(r => r.total_revenue || r.revenue),
                    backgroundColor: PALETTE.slice(0, rooms.length),
                    borderRadius: 6,
                }],
            },
            options: { plugins: { legend: { display: false } } },
        });
    } catch (e) { console.error('Revenue charts error:', e); }
}

// ======================================================
// OCCUPANCY Charts
// ======================================================
async function loadOccupancyCharts() {
    try {
        const [kpis, duration, trends] = await Promise.all([
            api('/api/kpis'),
            api('/api/duration'),
            api('/api/trends/monthly'),
        ]);

        const occRate = kpis.occupancy_rate || 0;

        // Occupancy Rate gauge (doughnut hack)
        makeChart('chartOccupancyGauge', {
            type: 'doughnut',
            data: {
                labels: ['Occupied', 'Vacant'],
                datasets: [{
                    data: [occRate, 100 - occRate],
                    backgroundColor: [COLORS.green, '#e2e8f0'],
                    borderWidth: 0,
                }],
            },
            options: {
                circumference: 180,
                rotation: -90,
                cutout: '75%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: true },
                },
            },
            plugins: [{
                id: 'gaugeText',
                afterDraw(chart) {
                    const { ctx, chartArea: { left, right, top, bottom } } = chart;
                    const cx = (left + right) / 2;
                    const cy = bottom - 20;
                    ctx.save();
                    ctx.font = 'bold 28px Inter, sans-serif';
                    ctx.fillStyle = '#0f172a';
                    ctx.textAlign = 'center';
                    ctx.fillText(occRate.toFixed(1) + '%', cx, cy);
                    ctx.font = '13px Inter, sans-serif';
                    ctx.fillStyle = '#64748b';
                    ctx.fillText('Occupancy Rate', cx, cy + 22);
                    ctx.restore();
                }
            }],
        });

        // Stay Duration Distribution (bar)
        makeChart('chartDuration', {
            type: 'bar',
            data: {
                labels: duration.map(r => r.total_stay_nights + ' nights'),
                datasets: [{
                    label: 'Bookings',
                    data: duration.map(r => r.count),
                    backgroundColor: COLORS.blue,
                    borderRadius: 4,
                }],
            },
            options: { plugins: { legend: { display: false } } },
        });

        // Weekend vs Weeknight comparison
        const weekendTotal = trends.reduce((s, r) => s + (r.weekend_nights || 0), 0);
        const weeknightTotal = trends.reduce((s, r) => s + (r.weeknight_nights || 0), 0);
        // If the monthly trends don't include these, compute from KPIs/duration fallback
        const hasWeekendData = weekendTotal > 0 || weeknightTotal > 0;

        makeChart('chartWeekendWeeknight', {
            type: 'bar',
            data: {
                labels: hasWeekendData ? ['Weekend Nights', 'Weeknight Nights'] : ['Weekend Stays', 'Weeknight Stays'],
                datasets: [{
                    label: 'Total Nights',
                    data: hasWeekendData ? [weekendTotal, weeknightTotal] : [0, 0],
                    backgroundColor: [COLORS.amber, COLORS.purple],
                    borderRadius: 6,
                }],
            },
            options: { plugins: { legend: { display: false } } },
        });

        // Try to get weekend/weeknight from hotels endpoint as fallback
        if (!hasWeekendData) {
            try {
                const hotels = await api('/api/hotels');
                const we = hotels.reduce((s, r) => s + (r.weekend_nights || r.stays_in_weekend_nights || 0), 0);
                const wn = hotels.reduce((s, r) => s + (r.weeknight_nights || r.stays_in_week_nights || 0), 0);
                if (we > 0 || wn > 0) {
                    makeChart('chartWeekendWeeknight', {
                        type: 'bar',
                        data: {
                            labels: ['Weekend Nights', 'Weeknight Nights'],
                            datasets: [{
                                label: 'Total Nights',
                                data: [we, wn],
                                backgroundColor: [COLORS.amber, COLORS.purple],
                                borderRadius: 6,
                            }],
                        },
                        options: { plugins: { legend: { display: false } } },
                    });
                }
            } catch {}
        }
    } catch (e) { console.error('Occupancy charts error:', e); }
}

// ======================================================
// CANCELLATIONS Charts
// ======================================================
async function loadCancellationCharts() {
    try {
        const [cancel, leadTime] = await Promise.all([
            api('/api/cancellations'),
            api('/api/lead-time'),
        ]);

        // By Hotel
        const byHotel = cancel.by_hotel || cancel.hotel || [];
        makeChart('chartCancelHotel', {
            type: 'bar',
            data: {
                labels: byHotel.map(r => r.hotel),
                datasets: [
                    { label: 'Canceled', data: byHotel.map(r => r.canceled || r.cancellations), backgroundColor: COLORS.red, borderRadius: 6 },
                    { label: 'Not Canceled', data: byHotel.map(r => r.not_canceled || r.total - (r.canceled || r.cancellations)), backgroundColor: COLORS.green, borderRadius: 6 },
                ],
            },
        });

        // By Deposit Type
        const byDeposit = cancel.by_deposit_type || cancel.deposit || [];
        makeChart('chartCancelDeposit', {
            type: 'bar',
            data: {
                labels: byDeposit.map(r => r.deposit_type),
                datasets: [
                    { label: 'Canceled', data: byDeposit.map(r => r.canceled || r.cancellations), backgroundColor: COLORS.red, borderRadius: 6 },
                    { label: 'Not Canceled', data: byDeposit.map(r => r.not_canceled || r.total - (r.canceled || r.cancellations)), backgroundColor: COLORS.green, borderRadius: 6 },
                ],
            },
        });

        // By Customer Type
        const byCust = cancel.by_customer_type || cancel.customer || [];
        makeChart('chartCancelCustomer', {
            type: 'bar',
            data: {
                labels: byCust.map(r => r.customer_type),
                datasets: [
                    { label: 'Canceled', data: byCust.map(r => r.canceled || r.cancellations), backgroundColor: COLORS.red, borderRadius: 6 },
                    { label: 'Not Canceled', data: byCust.map(r => r.not_canceled || r.total - (r.canceled || r.cancellations)), backgroundColor: COLORS.green, borderRadius: 6 },
                ],
            },
        });

        // Lead Time vs Cancel Rate
        makeChart('chartLeadTimeCancel', {
            type: 'bar',
            data: {
                labels: leadTime.map(r => r.bucket || r.lead_time_bucket),
                datasets: [{
                    label: 'Cancel Rate %',
                    data: leadTime.map(r => r.cancel_rate),
                    backgroundColor: COLORS.amber,
                    borderRadius: 6,
                }],
            },
            options: {
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' } } },
            },
        });
    } catch (e) { console.error('Cancellation charts error:', e); }
}

// ======================================================
// CUSTOMERS Charts
// ======================================================
async function loadCustomerCharts() {
    try {
        const [nations, segments] = await Promise.all([
            api('/api/nationalities'),
            api('/api/segments'),
        ]);

        // Top Nationalities (horizontal bar)
        makeChart('chartNationalities', {
            type: 'bar',
            data: {
                labels: nations.map(r => r.country),
                datasets: [{
                    label: 'Guests',
                    data: nations.map(r => r.guest_count || r.count),
                    backgroundColor: PALETTE.slice(0, nations.length),
                    borderRadius: 4,
                }],
            },
            options: { indexAxis: 'y', plugins: { legend: { display: false } } },
        });

        // Customer Segments (doughnut)
        makeChart('chartSegments', {
            type: 'doughnut',
            data: {
                labels: segments.map(r => r.customer_type || r.segment),
                datasets: [{
                    data: segments.map(r => r.count),
                    backgroundColor: PALETTE.slice(0, segments.length),
                    borderWidth: 2,
                }],
            },
            options: { plugins: { legend: { position: 'bottom' } } },
        });

        // Segment Revenue (bar)
        makeChart('chartSegmentRevenue', {
            type: 'bar',
            data: {
                labels: segments.map(r => r.customer_type || r.segment),
                datasets: [{
                    label: 'Revenue',
                    data: segments.map(r => r.revenue || r.total_revenue),
                    backgroundColor: PALETTE.slice(0, segments.length),
                    borderRadius: 6,
                }],
            },
            options: { plugins: { legend: { display: false } } },
        });
    } catch (e) { console.error('Customer charts error:', e); }
}

// ======================================================
// SEASONAL Charts
// ======================================================
async function loadSeasonalCharts() {
    try {
        const data = await api('/api/seasonal');

        const labels = data.map(r => r.month_name || r.month);

        // Seasonal Bookings (line)
        makeChart('chartSeasonalBookings', {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Bookings',
                    data: data.map(r => r.bookings || r.total_bookings),
                    borderColor: COLORS.teal,
                    backgroundColor: 'rgba(15,118,110,.1)',
                    fill: true,
                    tension: .35,
                    pointRadius: 4,
                }],
            },
        });

        // Seasonal ADR (line)
        makeChart('chartSeasonalADR', {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Avg Daily Rate',
                    data: data.map(r => r.avg_adr || r.adr),
                    borderColor: COLORS.amber,
                    backgroundColor: 'rgba(217,119,6,.1)',
                    fill: true,
                    tension: .35,
                    pointRadius: 4,
                }],
            },
        });

        // Seasonal Revenue (bar)
        makeChart('chartSeasonalRevenue', {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Revenue',
                    data: data.map(r => r.revenue || r.total_revenue),
                    backgroundColor: COLORS.blue,
                    borderRadius: 6,
                }],
            },
            options: { plugins: { legend: { display: false } } },
        });
    } catch (e) { console.error('Seasonal charts error:', e); }
}

// ======================================================
// Tab / Page Switching
// ======================================================
const pageLoaders = {
    overview:      () => { loadKPIs(); loadOverviewCharts(); },
    revenue:       loadRevenueCharts,
    occupancy:     loadOccupancyCharts,
    cancellations: loadCancellationCharts,
    customers:     loadCustomerCharts,
    seasonal:      loadSeasonalCharts,
    powerbi:       loadPbiCanvas,
};

let currentPage = 'overview';

function switchPage(page) {
    currentPage = page;
    // Toggle active nav
    document.querySelectorAll('.nav-item').forEach(a => a.classList.remove('active'));
    document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');
    // Toggle page visibility
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const target = document.getElementById('page-' + page);
    if (target) target.classList.add('active');
    // Load data for page
    if (pageLoaders[page]) pageLoaders[page]();
    // Close mobile sidebar
    document.getElementById('sidebar')?.classList.remove('open');
}

document.querySelectorAll('.nav-item').forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        switchPage(link.dataset.page);
    });
});

// Mobile menu toggle
document.getElementById('menuToggle')?.addEventListener('click', () => {
    document.getElementById('sidebar')?.classList.toggle('open');
});

// ======================================================
// Auto-Refresh Timer (30 s)
// ======================================================
let countdown = 30;
const countdownEl = document.getElementById('countdown');

function refreshCurrentPage() {
    checkConnection();
    if (pageLoaders[currentPage]) pageLoaders[currentPage]();
    document.getElementById('lastUpdated').textContent =
        'Last updated: ' + new Date().toLocaleTimeString();
}

setInterval(() => {
    countdown--;
    if (countdownEl) countdownEl.textContent = countdown + 's';
    if (countdown <= 0) {
        countdown = 30;
        refreshCurrentPage();
    }
}, 1000);

// ======================================================
// Power BI Visual Hub & Interactive Canvas
// ======================================================
const pbiFilter = {
    hotel: 'all',
    year: 0,
};

async function loadPbiCanvas() {
    try {
        // Query params for live slicers
        const qParts = [];
        if (pbiFilter.hotel !== 'all') qParts.push(`hotel=${encodeURIComponent(pbiFilter.hotel)}`);
        if (pbiFilter.year !== 0) qParts.push(`year=${pbiFilter.year}`);
        const qs = qParts.length ? '?' + qParts.join('&') : '';

        const [kpis, trends, rooms, channels, nats] = await Promise.all([
            api(`/api/kpis${qs}`),
            api(`/api/trends/monthly${qs}`),
            api('/api/rooms'),
            api('/api/channels'),
            api('/api/nationalities'),
        ]);

        // 1. Update Power BI KPI Tiles
        const setTile = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setTile('pbi-kpi-bookings', fmt.num(kpis.total_bookings));
        setTile('pbi-kpi-occupancy', fmt.pct(kpis.occupancy_rate));
        setTile('pbi-kpi-revenue', fmt.curr(kpis.total_revenue));
        setTile('pbi-kpi-duration', fmt.dec(kpis.avg_stay_duration) + ' n');
        setTile('pbi-kpi-cancellation', fmt.pct(kpis.cancellation_rate));
        setTile('pbi-kpi-adr', fmt.curr(kpis.avg_room_price));

        // 2. Visual 1: Monthly Trend & Cancellations
        const trendLabels = trends.map(t => `${t.month.slice(0, 3)} '${String(t.year).slice(2)}`);
        makeChart('chartPbiTrends', {
            type: 'line',
            data: {
                labels: trendLabels,
                datasets: [
                    {
                        label: 'Total Bookings',
                        data: trends.map(t => t.total_bookings),
                        borderColor: COLORS.blue,
                        backgroundColor: 'rgba(2, 132, 199, 0.1)',
                        fill: true,
                        tension: 0.3,
                        yAxisID: 'y',
                    },
                    {
                        label: 'Cancellations',
                        data: trends.map(t => t.cancellations),
                        borderColor: COLORS.red,
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        tension: 0.3,
                        yAxisID: 'y',
                    },
                    {
                        label: 'Avg ADR ($)',
                        data: trends.map(t => t.avg_adr),
                        borderColor: COLORS.amber,
                        backgroundColor: 'transparent',
                        tension: 0.3,
                        yAxisID: 'y1',
                    }
                ]
            },
            options: {
                scales: {
                    y: { position: 'left', title: { display: true, text: 'Bookings' } },
                    y1: { position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'ADR ($)' } },
                }
            }
        });

        // 3. Visual 2: Room Types Volume
        const topRooms = rooms.slice(0, 8);
        makeChart('chartPbiRooms', {
            type: 'bar',
            data: {
                labels: topRooms.map(r => 'Room ' + r.room_type),
                datasets: [{
                    label: 'Bookings',
                    data: topRooms.map(r => r.total_bookings),
                    backgroundColor: COLORS.teal,
                    borderRadius: 4,
                }]
            },
            options: {
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });

        // 4. Visual 3: Distribution Channels (Donut)
        makeChart('chartPbiChannels', {
            type: 'doughnut',
            data: {
                labels: channels.map(c => c.channel),
                datasets: [{
                    data: channels.map(c => c.total_bookings),
                    backgroundColor: PALETTE,
                    borderWidth: 2,
                }]
            },
            options: {
                plugins: {
                    legend: { position: 'right' }
                }
            }
        });

        // 5. Visual 4: Customer Nationalities (Top 8)
        const topNats = nats.slice(0, 8);
        makeChart('chartPbiCountries', {
            type: 'bar',
            data: {
                labels: topNats.map(n => n.country),
                datasets: [{
                    label: 'Guests',
                    data: topNats.map(n => n.guest_count),
                    backgroundColor: COLORS.purple,
                    borderRadius: 4,
                }]
            },
            options: {
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true } }
            }
        });

    } catch (e) {
        console.error('PBI Canvas load failed:', e);
    }
}

// Power BI Hub Init (Slicers, Modes, and Cloud Embed)
(function initPowerBIHub() {
    // 1. Mode Switcher
    document.querySelectorAll('.pbi-mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.pbi-mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const mode = btn.dataset.pbiMode;
            document.querySelectorAll('.pbi-view').forEach(v => v.classList.add('hidden'));
            document.getElementById(`pbi-view-${mode}`)?.classList.remove('hidden');

            if (mode === 'canvas') {
                loadPbiCanvas();
            }
        });
    });

    // 2. Hotel Slicer
    document.querySelectorAll('#slicerHotel .slicer-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#slicerHotel .slicer-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            pbiFilter.hotel = btn.dataset.value;
            loadPbiCanvas();
        });
    });

    // 3. Year Slicer
    document.querySelectorAll('#slicerYear .slicer-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#slicerYear .slicer-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            pbiFilter.year = parseInt(btn.dataset.value) || 0;
            loadPbiCanvas();
        });
    });

    // 4. Cloud Embed (Optional)
    const urlInput  = document.getElementById('powerbiUrl');
    const loadBtn   = document.getElementById('loadPowerBI');
    const iframe    = document.getElementById('powerbi-embed');
    const placeholder = document.getElementById('powerbiPlaceholder');

    const saved = localStorage.getItem('powerbi_url');
    if (saved && urlInput) {
        urlInput.value = saved;
        loadPBIReport(saved);
    }

    loadBtn?.addEventListener('click', () => {
        const url = urlInput?.value.trim();
        if (url) {
            localStorage.setItem('powerbi_url', url);
            loadPBIReport(url);
        }
    });

    function loadPBIReport(url) {
        if (iframe) {
            iframe.src = url;
            iframe.classList.add('visible');
        }
        placeholder?.classList.add('hidden');
    }
})();

// ======================================================
// Initial Load
// ======================================================
checkConnection();
switchPage('overview');
