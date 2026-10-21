(() => {
  'use strict';

  const palette = ['#1d6b4d', '#83b95a', '#e7bd59', '#7895ca', '#b2d4c0', '#e08c68'];

  const formatNumber = (value, digits = 1) => Number(value || 0).toLocaleString(undefined, {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0
  });

  function buildTrendChart(canvasId, labels, values) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;
    new Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Estimated kg CO₂e',
          data: values,
          borderColor: '#1d6b4d',
          backgroundColor: 'rgba(131, 185, 90, 0.17)',
          pointBackgroundColor: '#1d6b4d',
          pointBorderColor: '#ffffff',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6,
          borderWidth: 2.5,
          fill: true,
          tension: 0.35
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (ctx) => `${formatNumber(ctx.parsed.y, 2)} kg CO₂e` } }
        },
        scales: {
          x: { grid: { display: false }, border: { display: false }, ticks: { color: '#7c8982', maxRotation: 0 } },
          y: { beginAtZero: true, border: { display: false }, grid: { color: 'rgba(30, 70, 50, .08)' }, ticks: { color: '#7c8982', callback: value => formatNumber(value, 0) } }
        }
      }
    });
  }

  function buildDoughnutChart(canvasId, labels, values) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === 'undefined') return;
    const hasData = Array.isArray(values) && values.some(value => Number(value) > 0);
    new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: hasData ? labels : ['No entries yet'],
        datasets: [{
          data: hasData ? values : [1],
          backgroundColor: hasData ? palette : ['#e8eee9'],
          borderColor: '#ffffff',
          borderWidth: 4,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '69%',
        plugins: {
          legend: { position: 'bottom', labels: { usePointStyle: true, pointStyle: 'circle', padding: 18, boxWidth: 7, color: '#5d6d63', font: { family: 'DM Sans', size: 11 } } },
          tooltip: { callbacks: { label: ctx => hasData ? `${ctx.label}: ${formatNumber(ctx.parsed, 2)} kg CO₂e` : 'No emissions have been recorded' } }
        }
      }
    });
  }

  if (window.ecoTrackerCharts) {
    buildTrendChart('trendChart', window.ecoTrackerCharts.trendLabels, window.ecoTrackerCharts.trendValues);
    buildDoughnutChart('typeChart', window.ecoTrackerCharts.typeLabels, window.ecoTrackerCharts.typeValues);
  }
  if (window.ecoAnalyticsCharts) {
    buildTrendChart('analyticsTrendChart', window.ecoAnalyticsCharts.trendLabels, window.ecoAnalyticsCharts.trendValues);
    buildDoughnutChart('analyticsTypeChart', window.ecoAnalyticsCharts.typeLabels, window.ecoAnalyticsCharts.typeValues);
  }

  // Show a confirmation prompt before destructive POST actions.
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirm || 'Are you sure?')) event.preventDefault();
    });
  });

  // Update the estimated impact on the utility entry form before saving.
  const typeSelect = document.getElementById('utility_type');
  const valueInput = document.getElementById('consumption_value');
  const unitHint = document.getElementById('unitHint');
  const previewValue = document.getElementById('previewValue');
  const previewFormula = document.getElementById('previewFormula');
  const buildingGroup = document.getElementById('buildingGroup');
  const buildingSelect = document.getElementById('building_id');

  function refreshUtilityPreview() {
    if (!typeSelect || !valueInput || !previewValue || !window.ecoEmissionFactors) return;
    const kind = typeSelect.value;
    const config = window.ecoEmissionFactors[kind];
    const value = Number(valueInput.value);
    if (buildingGroup && buildingSelect) {
      const isTransport = kind === 'Transport';
      buildingGroup.classList.toggle('transport-optional', isTransport);
      buildingSelect.required = !isTransport && Boolean(kind);
    }
    if (!config) {
      unitHint.textContent = 'Choose a utility type to see its unit.';
      previewValue.textContent = '— kg CO₂e';
      previewFormula.textContent = 'Select a utility type and enter consumption.';
      return;
    }
    unitHint.textContent = `Unit: ${config.unit}`;
    if (value > 0 && Number.isFinite(value)) {
      const estimated = value * Number(config.factor);
      previewValue.textContent = `${formatNumber(estimated, 3)} kg CO₂e`;
      previewFormula.textContent = `${formatNumber(value, 3)} ${config.unit} × ${config.factor} ${config.description}`;
    } else {
      previewValue.textContent = '— kg CO₂e';
      previewFormula.textContent = `Factor: ${config.factor} ${config.description}`;
    }
  }

  if (typeSelect && valueInput) {
    typeSelect.addEventListener('change', refreshUtilityPreview);
    valueInput.addEventListener('input', refreshUtilityPreview);
    refreshUtilityPreview();
  }
})();
