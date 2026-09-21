/* v2 Project Monitoring — chart + selector wiring + 30s polling. CSP-safe (served from /static). */
(function () {
  var el = document.getElementById('mon-data');
  if (!el) return;
  var snap; try { snap = JSON.parse(el.textContent || '{}'); } catch (e) { return; }

  var path = window.location.pathname.replace(/\/$/, ''); // /projects/{id}/monitoring
  var chart = null;

  function seriesFor(s) {
    var key = s.selected_key;
    return (key && s.series && s.series[key]) ? s.series[key] : [];
  }

  function drawChart(s) {
    var cv = document.getElementById('monChart');
    if (!cv || !window.Chart) return;
    var pts = seriesFor(s);
    var labels = pts.map(function (p) { return p.t; });
    var data = pts.map(function (p) { return p.v; });
    if (chart) {
      chart.data.labels = labels;
      chart.data.datasets[0].data = data;
      chart.data.datasets[0].label = s.selected_key || '';
      chart.update();
      return;
    }
    chart = new Chart(cv, {
      type: 'line',
      data: { labels: labels, datasets: [{
        label: s.selected_key || '', data: data,
        borderColor: '#F26B33', backgroundColor: 'rgba(242,107,51,.08)',
        tension: .35, fill: true, pointRadius: 0, borderWidth: 2
      }] },
      options: { responsive: true, maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: { legend: { labels: { boxWidth: 12 } } },
        scales: { x: { ticks: { maxTicksLimit: 8, autoSkip: true }, grid: { display: false } } } }
    });
  }

  function updateKpis(s) {
    var d = document.getElementById('kpi-devices');
    if (d) d.innerHTML = s.device_count + (s.max_devices ? '<span class="kpi__sub">/' + s.max_devices + '</span>' : '');
    var o = document.getElementById('kpi-online');
    if (o) o.innerHTML = s.online_count + '<span class="kpi__sub">/' + s.device_count + '</span>';
    var a = document.getElementById('kpi-alarms');
    if (a) a.textContent = s.alarm_active_count;
    var u = document.getElementById('mon-updated');
    if (u && s.generated_at) u.textContent = s.generated_at;
  }

  // selectors: submit the GET form on change (server re-renders the full view)
  ['mon-device', 'mon-key', 'mon-range'].forEach(function (id) {
    var sel = document.getElementById(id);
    if (sel) sel.addEventListener('change', function () {
      var f = document.getElementById('mon-controls'); if (f) f.submit();
    });
  });

  function poll() {
    if (document.hidden) return;
    var q = '?range=' + encodeURIComponent(snap.range || '24h') +
            '&device=' + encodeURIComponent(snap.selected_device || '') +
            '&key=' + encodeURIComponent(snap.selected_key || '');
    fetch(path + '/data' + q, { credentials: 'same-origin', cache: 'no-store', headers: { 'X-Requested-With': 'fetch' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (s) { if (s) { snap = s; updateKpis(s); drawChart(s); } })
      .catch(function () {});
  }

  drawChart(snap);
  setInterval(poll, 30000);
})();
