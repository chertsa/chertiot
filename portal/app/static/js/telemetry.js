/* v2 Telemetry — trend chart + selector wiring (no polling). CSP-safe (served from /static). */
(function () {
  var el = document.getElementById('tel-data');
  if (!el) return;
  var snap; try { snap = JSON.parse(el.textContent || '{}'); } catch (e) { return; }

  function seriesFor(s) {
    var key = s.selected_key;
    return (key && s.series && s.series[key]) ? s.series[key] : [];
  }

  var cv = document.getElementById('telChart');
  if (cv && window.Chart) {
    var pts = seriesFor(snap);
    new Chart(cv, {
      type: 'line',
      data: {
        labels: pts.map(function (p) { return p.t; }),
        datasets: [{
          label: snap.selected_key || '', data: pts.map(function (p) { return p.v; }),
          borderColor: '#F26B33', backgroundColor: 'rgba(242,107,51,.08)',
          tension: .35, fill: true, pointRadius: 0, borderWidth: 2
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: { legend: { labels: { boxWidth: 12 } } },
        scales: { x: { ticks: { maxTicksLimit: 8, autoSkip: true }, grid: { display: false } } }
      }
    });
  }

  // selectors: submit the GET form on change (server re-renders the full view)
  ['tel-device', 'tel-key', 'tel-range'].forEach(function (id) {
    var sel = document.getElementById(id);
    if (sel) sel.addEventListener('change', function () {
      var f = document.getElementById('tel-controls'); if (f) f.submit();
    });
  });
})();
