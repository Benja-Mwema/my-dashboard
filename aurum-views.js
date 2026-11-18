'use strict';
(() => {
  const byId = id => document.getElementById(id);
  const getData = () => window.AurumUI.getData();
  const views = ['monitor', 'research', 'audit'];
  const indices = ['nas100', 'cac40', 'jpn225', 'aus200'];
  let area, chart, home, workspace, tabs, slot;
  let lastSnapshot, lastRecord, lastRows, view, timer;
  const el = (tag, text) => Object.assign(document.createElement(tag), {textContent: text || ''});
  const isReplay = () => /saved|replay/i.test(byId('dataset')?.value || '');
  const kind = () => window.AurumUI.kind;
  function setText(id, value) {
    const node = byId(id);
    if (node && node.textContent !== value) node.textContent = value;
  }
  function choose(id, value) {
    const input = byId(id);
    if (input && input.value !== value) {
      input.value = value;
      input.dispatchEvent(new Event('change', {bubbles:true}));
    }
  }
  function kv(parent, id, label) {
    const box = el('div');
    box.append(el('dt', label));
    const val = el('dd', 'Loading…');
    val.id = id;
    box.append(val);
    parent.append(box);
  }
  function latestRecord(data) {
    const time = r => r.signal_available_at || r.signal_time || r.decision_time || r.confirmation_available || r.entry_time;
    const records = data.entries || data.signals || [];
    return records.reduce((latest, r) => time(r) && (!latest || time(r) > time(latest)) ? r : latest, null);
  }
  function timestamp(value) {
    if (typeof value !== 'number') return value || 'Unavailable';
    return new Date(value * 1000).toISOString().slice(0,19).replace('T',' ');
  }
  function modelText(d) {
    const stage = kind() === 'gbpjpy' ? d.candidate : d.current;
    if(kind()==='usdjpy')return (stage?.converged?'EMA10/20/50 converged':'Outside EMA convergence')+' · '+(stage?.ema_order||'ordering unavailable')+' · confirmation requires all E1 gates';
    if (stage?.state) return [stage.direction, stage.state, stage.reason].filter(Boolean).join(' · ');
    if (d.market?.formation?.formation) return 'Daily market context · ' + d.market.formation.formation + ' · ' + d.market.formation.sequence + ' · ' + d.market.candle_date;
    if (kind() === 'ws30' && d.health?.no_accepted_prospective_observations) return 'Paper observer · no accepted forward entries in this snapshot';
    if (stage?.converged === true) return 'EMA convergence present · confirmation stage unavailable';
    return 'Pending formation stage unavailable';
  }
  function renderStatus() {
    const d = getData();
    const state = window.AurumCharts.getState();
    const source = window.AurumCharts.getSource();
    if (d !== lastSnapshot) {
      lastSnapshot = d;
      lastRecord = d && latestRecord(d);
      lastRows = undefined;
    }
    const tf = ['eurjpy','eurusd','gbpusd'].includes(kind()) ? 'M30' : 'H1';
    const chartTime = source?.forming_open_label;
    const chartAge = (Date.now() - Date.parse(source?.observed_at_utc)) / 60000;
    const chartLabel = source?.state === 'VERIFIED_NATIVE_CONTEXT' && state.currentContext ?
      [chartTime, 'broker', source.timeframe+' forming', source.forming_origin?.includes('TICK') ? 'from ticks' : '', chartAge > 25 ? 'stale' : '', state.refreshFailed ? 'refresh failed' : ''].filter(Boolean).join(' · ') :
      (source?.reason ? 'Unavailable · ' + source.reason : 'Awaiting verified chart data');
    setText('avChartTime', chartLabel);
    const end = d?.latest_completed_h1 || d?.latest_completed_m30 || d?.data_asof ||
      d?.health?.last_confirmed_broker_H1 || (d?.meta?.source_last?.H1 ? timestamp(d.meta.source_last.H1 + 3600) : d?.candles?.at(-1)?.close_time);
    const pub = d?.health?.refreshed_at || d?.health?.snapshot_generated_utc || d?.generated_at || d?.meta?.generated_at_utc;
    const stale = pub && Date.now() - Date.parse(pub) > 35*60000;
    const sourceState = d?.health?.state || d?.data_quality_state;
    const signalReference = source?.source_forming_open_label || chartTime;
    const lag = signalReference && end && String(end).slice(0,19).replace('T',' ') < signalReference;
    setText('avSignalTime', d ? [end || 'Time unavailable', 'broker', tf + ' close', stale ? 'stale publication' : '', sourceState && sourceState !== 'OK' ? sourceState.replaceAll('_',' ').toLowerCase() : lag ? 'behind chart' : ''].filter(Boolean).join(' · ') : 'Signal data unavailable');
    const staleGold = ['gold','xaueur'].includes(kind()) && d && Date.now()-Date.parse(d.quote_observed_at || d.generated_at)>90*60000;
    let stageText = d ? modelText(d) : 'Awaiting model data';
    if(staleGold) stageText='Current projection withheld · source stale';
    const r = lastRecord;
    let side = r?.side || r?.direction || (r?.sgn === 1 ? 'BUY' : r?.sgn === -1 ? 'SELL' : '');
    if (typeof side === 'number') side = side > 0 ? 'BUY' : 'SELL';
    const clock = r?.confirmation_available && typeof r.confirmation_available === 'number' ? 'UTC' : 'broker';
    const moment = r && timestamp(r.signal_available_at || r.signal_time || r.decision_time || r.confirmation_available || r.entry_time);
    setText('avLast', r ? [side,moment,clock].filter(Boolean).join(' · ') : 'No confirmation available');
    if(r && !stale && !staleGold && !lag && !r.confirmation_available && moment === end && (r.signal_available_at || r.signal_time || r.decision_time)) stageText=side+' confirmed on latest closed '+tf+' bar';
    setText('avStage',stageText);
    const levels = [];
    const level = (name, n) => {
      if (Number.isFinite(n)) levels.push(name + ' ' + n.toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:d.digits ?? (kind().endsWith('jpy') ? 3 : ['audcad','eurusd','gbpusd'].includes(kind()) ? 5 : 2)}));
    };
    if (r) {
      level('Entry', r.entry_price ?? r.entry_reference ?? r.entry);
      level('SL', r.SL ?? r.initial_stop ?? r.sl_price ?? r.stop);
      level('TP2',r.TP2); level('TP3',r.TP3);
      if (!r.TP2) level('Target',r.tp_price ?? r.target);
    }
    setText('avLevels',levels.join(' · '));
    byId('avInspectLast').hidden=!r;
    const note = byId('researchStatus')?.textContent || '';
    setText('avModel',indices.includes(kind()) ? 'Research candidate · independent validation pending' : note);
    byId('avModel').hidden = !byId('avModel').textContent;
    setText('avClockText',state.clock || 'Broker clock');
    if (view === 'research' && d) {
      const visible = window.AurumUI.visible();
      const dates = visible.map(n=>String(n.time || '').slice(0,10)).filter(Boolean).sort();
      const range = dates.length ? dates[0] + ' to ' + dates.at(-1) : 'No matching observations';
      const basis = 'Selected observations · ' + range;
      if (lastRows !== basis) {setText('avMetricRange',basis);lastRows=basis;}
    }
  }
  function go(next, updateHash = true) {
    if (!views.includes(next)) next='monitor';
    // A saved research dataset must never supply the current monitor.
    if (next === 'monitor' && isReplay()) {
      history.pushState(null,'','#monitor');
      location.reload();
      return;
    }
    const old = view;
    for(const skip of document.querySelectorAll('.skip'))skip.href=next==='monitor'?'#avMonitor':next==='audit'?'#avAudit':'#auWorkspace';
    view = next;
    document.body.dataset.aurumView = next;
    for (const link of tabs.querySelectorAll('a')) {
      if (link.hash === '#'+next) link.setAttribute('aria-current','page');
      else link.removeAttribute('aria-current');
    }
    area.hidden = next !== 'monitor';
    byId('avAudit').hidden = next !== 'audit';
    if (next === 'monitor') {
      slot.append(chart);
      choose('acMode','formation');choose('acFocus','current');
    } else {
      home.after(chart);
      if (next === 'research' && old !== 'research') {
        choose('acFocus','entry');
        if (!old || old === 'monitor') choose('acAfter','24');
      }
    }
    if (updateHash && location.hash !== '#'+next) history.pushState(null,'','#'+next);
    window.AurumCharts.refresh();
    renderStatus();
    if (updateHash) window.scrollTo(0,0);
  }
  function mount() {
    if (!window.AurumCharts || !window.AurumUI || !byId('acPlot')) return;
    const main = document.querySelector('main');
    workspace = byId('auWorkspace');
    chart = main.querySelector('.ac-workbench');
    home = document.createComment('Entry chart');
    chart.before(home);
    const originals = Array.from(main.children);
    originals.forEach(n=>n.classList.add('av-research-piece'));
    tabs = el('nav'); tabs.className = 'av-tabs'; tabs.setAttribute('aria-label','Dashboard views');
    views.forEach(v=>{const a=el('a',v[0].toUpperCase()+v.slice(1));a.href='#'+v;tabs.append(a);});
    area = el('section');area.className='av-monitor';area.id='avMonitor';
    const title = el('h1',(kind()==='gold' ? 'Gold' : kind().toUpperCase())+' monitor');
    const model = el('span');model.id='avModel';
    const heading = el('div');heading.className='av-heading';heading.append(title,model);
    const status = el('dl');status.className='av-strip';
    kv(status,'avChartTime','Chart bar');kv(status,'avSignalTime','Signal data through');kv(status,'avStage','Model status');
    slot = el('div');slot.className='av-chart-slot';
    const record = el('section');record.className='av-last';record.append(el('h2','Latest recorded confirmation'));
    const time=el('p');time.id='avLast';const levels=el('p');levels.id='avLevels';
    const inspectLast = el('button','Inspect confirmation');inspectLast.id='avInspectLast';
    inspectLast.onclick=()=>{
      if(!lastRecord)return;
      go('research');byId('auReset')?.click();
      for(const id of ['cohort','phase','side','sideFilter','ruleFilter','formation','outcomeFilter','monthFilter','year','month']){
        const field=byId(id);if(field?.options && Array.from(field.options).some(o=>o.value==='all'))choose(id,'all');
      }
      const id=lastRecord.id || lastRecord.case;
      const rows=window.AurumUI.visible();
      if(rows.some(n=>n.id===id))window.AurumUI.pick(id);
      else {byId('auSearch').value=id;byId('auSearch').dispatchEvent(new Event('input'));byId('auEntriesSection').scrollIntoView();return;}
      choose('acFocus','entry');byId('acWhy').open=true;byId('acPlot').scrollIntoView({block:'center'});
    };
    record.append(time,levels,inspectLast);
    const refresh = el('button','Refresh');refresh.className='av-refresh';refresh.onclick=()=>byId('reload').click();heading.append(refresh);
    area.append(heading,status,slot,record);
    const audit=el('section');audit.id='avAudit';audit.append(el('h1','Audit'));
    const evidence=byId('auDataDetails');
    if(evidence) audit.append(evidence);
    const provenance=byId('acUnified')?.querySelector('details');
    if(provenance) audit.append(provenance);
    const technical=/contract|governance|audit|fixed, and what updates|one fresh cross|trend and pullback|sell confirmation|frozen logic|two closes\. one decision|converged bars|frozen baseline|journey display and ws30 exit rules/i;
    for (const head of originals.flatMap(n=>Array.from(n.querySelectorAll('h2')))) {
      const section=head.closest('article,section');
      if(technical.test(head.textContent) && section && !section.querySelector('select,tbody#entries,#chart,#riskGraphic') && !section.contains(home)) {
        section.classList.remove('av-research-piece');audit.append(section);
      }
    }
    for (const foot of document.querySelectorAll('footer')) {foot.classList.remove('av-research-piece');audit.append(foot);}
    main.prepend(tabs,area,audit);
    const range=el('p');range.id='avMetricRange';byId('auSummary').before(range);range.className='av-research-piece av-range';
    const clock=el('span'); clock.id='avClockText';clock.className='av-clock';byId('acClock').closest('label').after(clock);
    const why=byId('acWhy');why.open=false;
    const inspect = () => { choose('acFocus','entry');why.open=true;window.AurumCharts.refresh(); };
    main.addEventListener('click',e=>{
      if(view==='research' && e.target.closest('#auEntriesSection ~ *,#auSaved,#auPrevious,#auNext,#auLatest') && e.target.closest('button,[data-id],tr[data-id]')) {
        if(e.target.closest('#auEntriesSection ~ *') && !e.target.closest('tbody')) return;
        setTimeout(inspect,0);
      }
      if(e.target.closest('a[href="#auDataDetails"]')) {e.preventDefault();go('audit');evidence.open=true;}
    });
    for(const id of ['signal','selected']) byId(id)?.addEventListener('change',inspect);
    tabs.onclick=e=>{const a=e.target.closest('a');if(a){e.preventDefault();go(a.hash.slice(1));}};
    const routeHash=()=>{const hash=location.hash.slice(1); if(views.includes(hash)||!hash)go(hash||'monitor',false);else if(hash==='avMonitor')go('monitor',false);else if(hash==='avAudit')go('audit',false);else if(hash==='auDataDetails'){go('audit',false);evidence.open=true;}else if(byId(hash)){go('research',false);byId(hash).scrollIntoView();}};
    window.addEventListener('hashchange',routeHash);
    window.addEventListener('popstate',routeHash);
    document.querySelector('.skip')?.setAttribute('href','#avMonitor');
    if(location.hash)routeHash();else go('monitor',false);
    if(!view)go('monitor',false);
    new MutationObserver(renderStatus).observe(byId('acLiveStatus'),{childList:true});
    timer = setInterval(renderStatus,1500);
    window.addEventListener('pagehide',()=>clearInterval(timer),{once:true});
    window.addEventListener('pageshow',e=>{if(e.persisted)timer=setInterval(renderStatus,1500);});
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',mount,{once:true});
  else mount();
})();
