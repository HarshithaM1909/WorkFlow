(function () {
    var headcountChart = null;
    var attendanceTrendChart = null;

    var TEXT_COLOR = '#8b93a7';
    var GRID_COLOR = 'rgba(139, 147, 167, 0.15)';
    var ACCENT = '#3b82f6';
    var SUCCESS = '#22c55e';
    var DANGER = '#ef4444';

    if (window.Chart) {
        Chart.defaults.color = TEXT_COLOR;
        Chart.defaults.borderColor = GRID_COLOR;
        Chart.defaults.font.family = "'Inter', 'Segoe UI', system-ui, sans-serif";
    }

    function renderCharts() {
        var dataEl = document.getElementById('chart-data');
        if (!dataEl) return;
        var chartData = JSON.parse(dataEl.textContent);

        if (headcountChart) {
            headcountChart.destroy();
            headcountChart = null;
        }
        if (attendanceTrendChart) {
            attendanceTrendChart.destroy();
            attendanceTrendChart = null;
        }

        var headcountCanvas = document.getElementById('headcountChart');
        var trendCanvas = document.getElementById('attendanceTrendChart');
        if (!headcountCanvas || !trendCanvas) return;

        headcountChart = new Chart(headcountCanvas, {
            type: 'bar',
            data: {
                labels: chartData.headcount.labels,
                datasets: [{
                    label: 'Employees',
                    data: chartData.headcount.data,
                    backgroundColor: ACCENT,
                    borderRadius: 4,
                    maxBarThickness: 42,
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0, color: TEXT_COLOR }, grid: { color: GRID_COLOR } },
                    x: { ticks: { color: TEXT_COLOR }, grid: { display: false } },
                },
            },
        });

        attendanceTrendChart = new Chart(trendCanvas, {
            type: 'line',
            data: {
                labels: chartData.attendance_trend.labels,
                datasets: [
                    { label: 'Present', data: chartData.attendance_trend.present, borderColor: SUCCESS, backgroundColor: SUCCESS, tension: 0.3, fill: false },
                    { label: 'Absent', data: chartData.attendance_trend.absent, borderColor: DANGER, backgroundColor: DANGER, tension: 0.3, fill: false },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: TEXT_COLOR } } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0, color: TEXT_COLOR }, grid: { color: GRID_COLOR } },
                    x: { ticks: { color: TEXT_COLOR }, grid: { display: false } },
                },
            },
        });
    }

    document.addEventListener('DOMContentLoaded', renderCharts);
    document.body.addEventListener('htmx:afterSwap', function (evt) {
        if (evt.detail && evt.detail.target && evt.detail.target.id === 'dashboard-content') {
            renderCharts();
        }
    });
})();
