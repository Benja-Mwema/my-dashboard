'use strict';
const pairStem = document.body.dataset.fxPair;
const symbol = pairStem.toUpperCase() + '.pro';
const $ = id => document.getElementById(id);
const price = v => v == null ? '—' : Number(v).toFixed(5);
let data = null, snapshot = null, sequence = 0;

function records() { return data?.entries || []; }
function rows() {
  return records().filter(r =>
    window.AurumUI?.accept(r) !== false &&
    ($('side').value === 'all' || r.direction === $('side').value) &&
    ($('month').value === 'all' || r.signal_available_at.startsWith($('month').value)) &&
    ($('phase').value === 'all' || r.phase === $('phase').value)
  );
}
function inspect() {
  const r = records().find(e => e.id === $('selected').value);
  $('chartTitle').textContent = r ? r.direction + ' · ' + r.signal_available_at : 'Formation inspection';
  $('chart').textContent = r ? 'Confirmation at ' + r.signal_available_at + ' · next-open price ' + price(r.entry_price) : 'No confirmation selected.';
  $('detail').textContent = r ? 'Cluster start ' + r.cluster_start + ' · EMA10/20 cross on the bar opening ' + r.cross_bar_open + ' · ' + r.N + ' converged H1 bars.' : '';
}
function render() {
  const selected = $('selected').value;
  const filtered = rows().reverse();
  $('selected').replaceChildren(...filtered.map(r => new Option(r.direction+' · '+r.signal_available_at,r.id)));
  if (filtered.some(r => r.id===selected)) $('selected').value=selected;
  const body=$('entries'); body.replaceChildren();
  for (const r of filtered) {
    const tr=body.insertRow();
    for (const val of [r.direction,r.signal_bar_open,r.signal_available_at,r.phase+' / '+r.N,price(r.entry_price),r.execution_status,r.net_pips==null?'—':r.net_pips.toFixed(1)]) tr.insertCell().textContent=val;
    tr.cells[0].className=r.direction.toLowerCase();
    const button=document.createElement('button'); button.textContent='Inspect ↗'; button.dataset.id=r.id;
    button.onclick=()=>{window.AurumUI.pick(r.id);$('acFocus').value='entry';$('acFocus').dispatchEvent(new Event('change'));};
    tr.insertCell().append(button);
  }
  if (!filtered.length) {const cell=body.insertRow().insertCell();cell.colSpan=8;cell.textContent='No confirmations match these filters.';}
  inspect();
}
function applyRule() {
  if(!snapshot) return;
  const role=$('exitMode').value;
  const model=snapshot.models[role], rule=model.rule;
  const status=role===snapshot.primary?snapshot.research_status:pairStem==='usdchf'?'Historical comparison · rejected currency':'Alternative research comparison';
  const entries=model.entries.map(e=>{
    const buy=e.direction==='BUY', sign=buy?1:-1;
    const tests=[
      ['Crossing bar open',e.cross_bar_open,'Latest in-episode EMA10/20 cross agrees with '+e.direction,e.cross_bar_open>=e.cluster_start&&e.cross_bar_open<=e.signal_bar_open],
      ['Converged H1 bars',e.N,buy?'2–'+rule.max_buy:'4–'+rule.max_sell,e.N>=(buy?2:4)&&e.N<=(buy?rule.max_buy:rule.max_sell)],
      ['Tightest width in episode',e.min_depth,'≤ '+rule.width+' current ATR',e.min_depth<=rule.width],
      ['EMA10 / EMA20 / EMA50',[e.ema10,e.ema20,e.ema50].map(price).join(' / '),buy?'Descending order':'Ascending order',sign*(e.ema10-e.ema20)>0&&sign*(e.ema20-e.ema50)>0],
      ['EMA slopes',[e.slope10,e.slope20,e.slope50].map(x=>x.toFixed(6)).join(' / '),'EMA10/20 directional; EMA50 may be flat',sign*e.slope10>0&&sign*e.slope20>0&&sign*e.slope50>=0],
      ['Band expansion',e.width_growth,'Width increased',e.width_growth>0],
      ['Close beyond EMA10',e.close_minus_ema10,'In signal direction',sign*e.close_minus_ema10>0],
      ['Directional candle',e.body,'In signal direction',sign*e.body>0],
      ['Candle close location',e.close_location,buy?'≥ 0.50':'≤ 0.50',buy?e.close_location>=.5:e.close_location<=.5],
      ['Directional closes',e.directional_closes3,'At least 2 of 3',e.directional_closes3>=2]
    ];
    if(!buy)tests.push(['Lower highs and lows',e.lower_pairs3,'At least 2 of 3',e.lower_pairs3>=2]);
    return {...e,rule:role==='original'?'H1 original':rule.profile,predicates:tests.map(([label,value,condition,passed])=>({label,value,condition,passed}))};
  });
  const b=snapshot.candles.at(-1),converged=b.depth<=rule.width;
  data={...snapshot,entries,rule,current:{state:converged?'EMA10/20/50 converged':'Outside EMA convergence',reason:'Width '+b.depth.toFixed(3)+' ATR'}};
  $('researchStatus').textContent=status;
  $('contract').textContent='Width ≤ '+rule.width.toFixed(2)+' × H1 ATR14. BUY 2–'+rule.max_buy+' converged bars. '+(rule.side==='BUY'?'SELL disabled.':'SELL 4–'+rule.max_sell+' converged bars.')+' Outcome at H1 close '+rule.horizon+'.';
  $('notice').textContent=status+' · '+model.verified_archive_count+' historical confirmations reconciled through 17 November 2026.';
  $('current').textContent=data.current.state+' · '+data.current.reason;
  $('asof').textContent=data.latest_completed_h1;
  $('quality').textContent=$('dataset').value.includes('replay')?'Saved replay':Date.now()-Date.parse(data.generated_at)>35*60000?'Stale publication':'Published';
  const old=$('month').value;
  $('month').replaceChildren(new Option('All months','all'),...[...new Set(entries.map(e=>e.signal_available_at.slice(0,7)))].sort().reverse().map(x=>new Option(x,x)));
  if([...$('month').options].some(o=>o.value===old))$('month').value=old;
  render();
}
async function load(){
  const seq=++sequence, name=$('dataset').value; $('reload').disabled=true;
  try {
    const response=await fetch(name,{cache:'no-cache'});
    if(!response.ok)throw Error('Snapshot unavailable');
    const payload=await response.json(); if(seq!==sequence)return;
    if(payload.symbol!==symbol||payload.version!=='FX_H1_EMA_CROSS_V0_2'||payload.meta.timeframe!=='H1'||payload.meta.broker_orders_enabled!==false)throw Error('Snapshot identity mismatch');
    if(!snapshot)$('exitMode').value=payload.primary;
    snapshot=payload;$('download').href=name;applyRule();
  } catch(e){if(seq===sequence){$('quality').textContent='Refresh unavailable';$('notice').textContent=e.message;}}
  finally{if(seq===sequence)$('reload').disabled=false;}
}
$('exitMode').onchange=applyRule;
for(const id of ['side','month','phase'])$(id).onchange=()=>{if(data)render();};
$('selected').onchange=inspect;$('reload').onclick=$('dataset').onchange=load;
fetch('assets.json').then(r=>r.json()).then(r=>{$('instrument').replaceChildren(...r.assets.filter(a=>a.status==='published').map(a=>new Option(a.name+' · '+a.symbol,a.module_page||'index.html')));$('instrument').value=pairStem+'.html';$('instrument').onchange=()=>location.assign($('instrument').value);});
setInterval(()=>{if(!document.hidden&&!$('dataset').value.includes('replay'))load();},15*60000);
load();
