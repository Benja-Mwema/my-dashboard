'use strict';
(() => {
  const {key, symbol} = document.body.dataset;
  const get = id => document.getElementById(id);
  const picker = get('instrument');
  const requested = new URLSearchParams(location.search).get('asset');
  const option = [...picker.options].find(o => o.dataset.symbol === requested);
  if (option && option.dataset.symbol !== symbol) {
    location.replace(option.value + location.hash);
    return;
  }
  if (location.hash) {
    // Existing bookmarks target the original interactive dashboard sections.
    location.replace(document.querySelector('.full-link').href + location.hash);
    return;
  }
  picker.onchange = () => location.assign(picker.value);
  const delivery = window.AurumDelivery;
  let version, current, lastCheck = 0, busy = false;
  function display(data, observed) {
    const bars = data.candles;
    const valid = data.state === 'VERIFIED_NATIVE_CONTEXT' && bars.length > 0;
    const stale = !observed || Date.now() - Date.parse(observed) > 25 * 60000;
    get('status').textContent = (stale ? 'Stale publication · ' : '') +
      (valid ? bars.length + ' completed ' + data.timeframe + ' bars' : 'Current candles unavailable') +
      (observed ? ' · Observed ' + observed.replace('T', ' ').replace(/\.\d+\+00:00$/, ' UTC') : '');
    get('warning').textContent = data.reason || data.source_warning || '';
    get('quote').textContent = '';
    const canvas = get('chart');
    canvas.hidden = !valid;
    if (!valid) return;
    const ctx = canvas.getContext('2d');
    const high = Math.max(...bars.map(b => b.high)), low = Math.min(...bars.map(b => b.low));
    const y = price => 12 + (high - price) * (canvas.height - 24) / (high - low || 1);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const step = (canvas.width - 88) / bars.length;
    bars.forEach((bar, i) => {
      const x = (i + 0.5) * step;
      ctx.fillStyle = ctx.strokeStyle = bar.close >= bar.open ? '#65c6ab' : '#ed928c';
      ctx.beginPath(); ctx.moveTo(x, y(bar.high)); ctx.lineTo(x, y(bar.low)); ctx.stroke();
      ctx.fillRect(x - step * 0.31, y(Math.max(bar.open, bar.close)), step * 0.62,
        Math.max(1, Math.abs(y(bar.open) - y(bar.close))));
    });
    ctx.fillStyle = '#b7c7c5'; ctx.font = '16px sans-serif';
    for (const price of new Set([high, low])) ctx.fillText(String(price), canvas.width - 80, y(price) + 5);
    const bar = bars.at(-1);
    const brokerLabel = new Date(bar.time * 1000).toISOString().slice(0, 16).replace('T', ' ');
    get('quote').textContent = 'Last bar opened ' + brokerLabel + ' broker time · Open ' + bar.open +
      ' · High ' + bar.high + ' · Low ' + bar.low + ' · Close ' + bar.close;
  }
  async function check(force = false) {
    if (busy || document.hidden || (!force && Date.now() - lastCheck < delivery.interval)) return;
    busy = true;
    lastCheck = Date.now();
    try {
      const revision = await delivery.revision(key);
      if (revision.recent !== version) {
        const next = await delivery.read(revision.recent);
        if (next.symbol !== symbol) throw Error('Instrument mismatch');
        current = next;
        version = revision.recent;
      }
      display(current, revision.observed);
    } catch (error) {
      get('status').textContent = (current ? 'Refresh failed · Showing the last loaded chart. ' : '') + error.message;
    } finally { busy = false; }
  }
  get('refresh').onclick = () => check(true);
  document.addEventListener('visibilitychange', () => check());
  setInterval(() => check(), delivery.interval);
  check();
})();
