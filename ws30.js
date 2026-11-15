'use strict';
/* AURUM WS30 v1.0 — read-only visualization of sealed historical research. */
let data=null,chosen=null,intrabar=null;
const RULES=['H01','C1','Combined','D04'];
const $=id=>document.getElementById(id);
const format=(n,p=1)=>Number.isFinite(Number(n))&&n!==null&&n!==''?Number(n).toLocaleString('en-US',{minimumFractionDigits:p,maximumFractionDigits:p}):'—';
const text=v=>v===null||v===undefined||v===''?'—':String(v);
function el(tag,content,cl){const x=document.createElement(tag);if(content!==undefined)x.textContent=text(content);if(cl)x.className=cl;return x;}
function set(id,v){$(id).textContent=text(v);}
function pct(a,n){return n?(100*a/n).toFixed(1)+'%':'—';}
function color(d){return d==='BUY'?'#79d9b7':'#e78c86';}
function cohort(){return $('cohort').value;}
function filtered(){return data.signals.filter(x=>x.cohort===cohort()&&
 ($('ruleFilter').value==='all'||x.rule===$('ruleFilter').value)&&
 ($('sideFilter').value==='all'||x.direction===$('sideFilter').value)&&
 ($('outcomeFilter').value==='all'||x.status===$('outcomeFilter').value)&&
 ($('monthFilter').value==='all'||x.entry_time.startsWith($('monthFilter').value)));}
function setupTop(){
 set('numEntries',data.signals.length+' admissions');
 const count=data.economic_entry_accounting.EARLIER_HISTORICAL_2024_2025;
 set('numDistinct',count.distinct_exact_economic_entries+' (2024–25)');
 const h=data.health;set('latestH1',h.last_confirmed_broker_H1||'—');
 set('pubState',h.session_or_observer_state||h.state||'SOURCE UNAVAILABLE');
 set('scopeStatus','Historical and prospective are separate');
 set('pubTime','Last quote: '+text(h.broker_tick_time)+ ' · Snapshot: '+text(h.snapshot_generated_utc).slice(0,19));
}
function summary(){
 const by=data.performance[cohort()]||{};
 const cards=$('ruleCards');cards.replaceChildren();
 const body=$('summaryRows');body.replaceChildren();
 for(const rule of RULES){
  const p=by[rule]||{admissions:0,WIN:0,LOSS:0,BE:0,TIMEOUT:0};
  const c=el('article');
  c.append(el('strong',rule),el('span',p.admissions+' historical admissions'),
           el('span',p.WIN+' WIN · '+p.LOSS+' LOSS · '+p.BE+' BE · '+p.TIMEOUT+' TIMEOUT'),
           el('span',pct(p.WIN,p.admissions)+' target-hit rate · all final','chip'));
  cards.append(c);
  const tr=el('tr');
  const costs=p.cost_proxy_coverage?p.cost_proxy_coverage+'/'+p.admissions+' · '+format(p.spread_proxy_R,3)+'R':'Not available';
  for(const val of [rule,p.admissions,p.WIN,p.LOSS,p.BE,p.TIMEOUT,pct(p.WIN,p.admissions),format(p.gross_R,3)+'R',costs]){
   tr.append(el('td',val));
  }
  body.append(tr);
 }
}
function register(){
 const records=filtered().sort((a,b)=>a.entry_time.localeCompare(b.entry_time)).reverse();
 const body=$('signalRows');body.replaceChildren();
 set('filterCount',records.length+' of '+data.signals.filter(x=>x.cohort===cohort()).length+
  ' archived admissions in selected cohort · failures and exact-entry duplicates retained');
 if(!records.length){const tr=el('tr');const td=el('td','No matching research records.');td.colSpan=9;tr.append(td);body.append(tr);return;}
 for(const r of records){
  const tr=el('tr');
  const cols=[r.signal_time,r.rule+' / '+r.branch,r.direction,r.entry_time,
       format(r.entry_reference,1),r.ATR_anchor,r.status,format(r.score_R_min,3)+'R'];
  cols.forEach((v,i)=>tr.append(el('td',v,i===2?(r.direction==='BUY'?'buy':'sell'):undefined)));
  const btn=el('button','Inspect');btn.type='button';btn.setAttribute('aria-label','Inspect '+r.rule+' '+r.entry_time);
  btn.onclick=()=>{chosen=r.id;detail();$('detail').scrollIntoView({behavior:'smooth',block:'start'});};
  const td=el('td');td.append(btn);tr.append(td);body.append(tr);
 }
}
function evidenceBox(d,name,val){const z=el('div');z.append(el('span',name));z.append(el('strong',val));d.append(z);}
function pathSvg(r){
 const root=$('riskGraphic');root.replaceChildren();
 const tf=$('chartTf').value;
 const c=tf==='H1'?data.candles||[]:(intrabar?.cases?.[r.id]?.[tf]||[]);
 if(!c.length){
  root.append(el('div',tf==='H1'?'No observed H1 candles.':
   'Detailed '+tf+' archived market evidence is not loaded or unavailable.','muted'));
  return;
 }
 const when=r.entry_time||r.signal_time;
 let hi=c.findIndex(x=>x.time>=when);if(hi<0)hi=c.length-1;
 const look=Math.max(12,Math.min(192,Number($('chartRange').value)||96));
 const scale=tf==='M15'?4:1;
 const start=tf==='M1'?0:Math.max(0,hi-Math.round(look*.67)*scale);
 const last=tf==='M1'?c.length-1:Math.min(c.length-1,hi+Math.round(look*.4)*scale);
 const bars=c.slice(start,last+1);if(!bars.length)return;
 const stopAt=r.exit_time||r.horizon_end;
 const lastObserved=bars.findLastIndex(x=>x.close_time<=stopAt);
 const W=960,H=390,L=20,R=120,T=24,B=48;
 const levels=[r.initial_stop,r.target,r.entry_reference,r.BE_threshold].filter(Number.isFinite);
 const prices=bars.flatMap(x=>[x.low,x.high]).concat(levels);
 let lo=Math.min(...prices),up=Math.max(...prices),pad=(up-lo)*.08||20;lo-=pad;up+=pad;
 const xp=j=>L+(j/Math.max(1,bars.length-1))*(W-L-R);
 const yp=p=>T+(up-p)/(up-lo)*(H-T-B);
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
 svg.setAttribute('viewBox','0 0 '+W+' '+H);
 svg.setAttribute('role','img');svg.setAttribute('aria-label','Historical observed completed H1 close path and original ATR barriers');
 const item=(tag,attrs,value)=>{const z=document.createElementNS('http://www.w3.org/2000/svg',tag);
  for(const [k,v] of Object.entries(attrs))z.setAttribute(k,String(v));
  if(value!==undefined)z.textContent=String(value);svg.append(z);return z;};
 for(let i=0;i<=5;i++){
  const p=lo+(up-lo)*i/5;
  item('line',{x1:L,x2:W-R,y1:yp(p),y2:yp(p),stroke:'#294044','stroke-width':1});
  item('text',{x:W-R+10,y:yp(p)+4,fill:'#a7b8bb','font-size':11},format(p,1));
 }
 const nativeMinute=s=>Date.parse(String(s).replace(' ','T')+'Z')/60000;
 const maxGap=tf==='H1'?120:tf==='M15'?30:5;
 const d=bars.map((v,i)=>{
  const disconnect=i===0||nativeMinute(v.time)-nativeMinute(bars[i-1].time)>maxGap;
  return (disconnect?'M':'L')+xp(i)+','+yp(v.close);
 }).join(' ');
 item('path',{d:d,stroke:'#889d9f','stroke-width':1.8,fill:'none'});
 const offset=Math.max(0,hi-start),endIdx=Math.min(lastObserved,bars.length-1);
 if(endIdx>=offset){
  const active=bars.slice(offset,endIdx+1).map((v,j)=>{
   const index=offset+j;
   const disconnect=j===0||nativeMinute(v.time)-nativeMinute(bars[index-1].time)>maxGap;
   return (disconnect?'M':'L')+xp(index)+','+yp(v.close);
  }).join(' ');
  item('path',{d:active,stroke:color(r.direction),'stroke-width':3,fill:'none'});
 }
 const research=[
  ['TP +2ATR',r.target,'#6bcbb2','7 4'],['BE threshold',r.BE_threshold,'#c9b1ec','2 5'],
  ['Entry reference',r.entry_reference,'#e5d3ab','0'],['SL −3ATR',r.initial_stop,'#df8e89','7 4']
 ];
 for(const [label,v,col,dash] of research){
  const yy=yp(v);
  item('line',{x1:L,x2:W-R,y1:yy,y2:yy,stroke:col,'stroke-width':1.5,'stroke-dasharray':dash});
  item('text',{x:W-R+5,y:yy-5,fill:col,'font-size':10},label);
 }
 item('circle',{cx:xp(offset),cy:yp(r.entry_reference),r:4.5,fill:color(r.direction)});
 item('text',{x:L,y:13,fill:'#b4c4c4','font-size':12},
  'Observed completed H1 prices · broker labels · reference only, not a trade');
 for(let tick=0;tick<5;tick++){
  const j=Math.min(bars.length-1,Math.round((bars.length-1)*tick/4));
  item('text',{x:xp(j),y:H-19,fill:'#a4b5b6','font-size':11,'text-anchor':tick?'middle':'start'},bars[j].time.slice(5,16));
 }
 if(r.BE_armed_at){
  const i=bars.findIndex(z=>z.time>=r.BE_armed_at);
  if(i>=0){
   const until=Math.min(Math.max(i,lastObserved),bars.length-1);
   item('line',{x1:xp(i),x2:xp(until),y1:yp(r.entry_reference),y2:yp(r.entry_reference),
     stroke:'#c9b1ec','stroke-width':3.5});
   item('text',{x:xp(i),y:H-34,fill:'#c9b1ec','font-size':11},'BE armed '+r.BE_armed_at.slice(5,16));
  }
 }
 root.append(svg);
}
function detail(){
 const r=data.signals.find(z=>z.id===chosen)||filtered()[0];
 if(!r){set('caseTitle','No selected admission');$('riskGraphic').replaceChildren();$('caseFacts').replaceChildren();return;}
 chosen=r.id;set('caseTitle',r.rule+' · '+r.direction+' · '+r.status);
 set('caseSubtitle',r.entry_time+' broker · '+r.branch+' · '+r.cohort+' · '+r.origin);
 const box=$('caseFacts');box.replaceChildren();
 const fields=[
 ['Signal completed H1',r.signal_time],['First M15 opening',r.entry_time],
 ['First observed M1 quote',r.first_M1_quote_time],['Entry reference E',format(r.entry_reference,1)],
 ['Frozen ATR / anchor',format(r.ATR,5)+' · '+r.ATR_anchor],
 ['Initial SL (−3ATR)',format(r.initial_stop,1)],['TP2 (+2ATR)',format(r.target,1)],
 ['BE threshold (+1ATR)',format(r.BE_threshold,1)],
 ['BE actually armed',r.BE_armed_at||'Not armed'],
 ['Horizon, native 24 H1',r.horizon_end],['Archived outcome',r.status],
 ['Fully scorable',r.score_final?'Yes':'No / pending'],['Gross R',format(r.score_R_min,4)],
 ['Gap-adjusted R',format(r.gap_adjusted_R_min,4)],
 ['Spread-proxy R',format(r.spread_proxy_net_R_min,4)],
 ['Economic grouping',r.economic_key],['Source case ID',r.source_case_id],
 ['Cohort classification',r.cohort],['Origin',r.origin]];
 fields.forEach(([k,v])=>evidenceBox(box,k,v));
 pathSvg(r);
}
function paperJournal(){
 const p=data.prospective_paper||{signal_intents:0,completed_scores:0,censored_count:0,missed_candidates:[],observations:[]};
 set('paperIntents',p.signal_intents||0);
 set('paperFinal',p.completed_scores||0);
 set('paperCensored',p.censored_count||0);
 set('paperMissed',Array.isArray(p.missed_candidates)?p.missed_candidates.length:0);
 const body=$('paperRows');body.replaceChildren();
 const rows=Array.isArray(p.observations)?p.observations.slice().reverse():[];
 if(!rows.length){
  const tr=el('tr');const td=el('td','No new accepted pre-outcome WS30.paper observations.');td.colSpan=7;
  tr.append(td);body.append(tr);return;
 }
 for(const x of rows){
  const tr=el('tr');
  for(const z of [x.detected_at_utc,x.rule,x.direction,x.signal_time,
   x.entry_reference==null?'Not accepted':format(x.entry_reference,1),
   x.quote_state||x.lifecycle,x.score_final?x.status:(x.status||'PENDING — not scored')]){
   tr.append(el('td',z));
  }
  body.append(tr);
 }
}
function health(){
 const root=$('provenance');root.replaceChildren();
 const m=data.meta,h=data.health;
 const list=[
 ['Market symbol / broker labels',m.symbol+' · '+m.market_clock],
 ['Research source',m.scope+' · '+m.source_url],
 ['Latest completed H1',h.last_confirmed_broker_H1],
 ['Latest native broker tick',h.broker_tick_time||'No fresh quote'],
 ['Snapshot generation',h.snapshot_generated_utc],
 ['Prospective paper observer',h.prospective_worker_armed?'ARMED — no executed orders':'Not armed / awaiting acceptance'],
 ['Health state',h.state],
 ['Study periods','2026 development ≠ earlier 2024–2025 history ≠ future pre-outcome paper journal'],
 ['Paper status',h.warning||'No live trading'],
 ['Reference SHA256',m.source_reference_inventory_sha256],
 ['Snapshot sequence',m.snapshot_sequence],
 ['Primary profile',data.primary_profile.id+' · TP2/SL3/BE_H1_2C'],
 ['Execution','No broker orders or verified fills; retrospective barrier scores']];
 list.forEach(([a,b])=>root.append(el('dt',a),el('dd',b)));
 for(const [r,hsh] of Object.entries(m.rule_manifest_hashes||{}))root.append(el('dt',r+' frozen manifest'),el('dd',hsh));
}
function months(){
 const list=Object.keys(data.monthly_performance||{}).filter(x=>data.monthly_performance[x].cohort===cohort()).sort().reverse();
 const root=$('monthFilter');root.replaceChildren();
 const all=el('option','All months');all.value='all';root.append(all);
 list.forEach(x=>{const o=el('option',x);o.value=x;root.append(o);});
}
async function loadIntrabar(){
 if(intrabar)return;
 const r=await fetch('ws30-intrabar.json?t='+Date.now(),{cache:'no-store'});
 if(!r.ok)throw Error('Intrabar evidence unavailable HTTP '+r.status);
 const v=await r.json();
 if(v.symbol!=='WS30.pro'||v.total_cases!==189||
 v.scope!=='ARCHIVED_HISTORICAL_INTRABAR_CHART_DATA_NOT_PROSPECTIVE'||
 v.model_input_hash!==data.meta.source_reference_inventory_sha256)
  throw Error('M1/M15 historical source provenance mismatch');
 intrabar=v;
}
async function load(){
 const q=await fetch('ws30-data.json?t='+Date.now(),{cache:'no-store'});
 if(!q.ok)throw Error('WS30 data missing HTTP '+q.status);
 data=await q.json();
 if(data.meta?.symbol!=='WS30.pro'||data.meta?.market_clock!=='NATIVE_BROKER_LABELS_NO_CONVERSION'
  ||!['HISTORICAL_REPLAY','MIXED_LABELLED','PROSPECTIVE_PAPER'].includes(data.meta?.scope)
  ||RULES.some(x=>!data.meta.rule_manifest_hashes[x])||!Array.isArray(data.signals)
  ||!data.health||!Array.isArray(data.candles))throw Error('Instrument, model or provenance mismatch');
 setupTop();summary();months();register();chosen=filtered()[0]?.id||null;detail();paperJournal();health();
 for(const id of ['cohort','ruleFilter','sideFilter','outcomeFilter','monthFilter']){
  $(id).onchange=()=>{if(id==='cohort'){months();summary();}chosen=null;register();detail();};
 }
 $('chartRange').onchange=()=>detail();
 $('chartTf').onchange=async()=>{
  if($('chartTf').value!=='H1'){
   try{await loadIntrabar();}
   catch(e){$('riskGraphic').replaceChildren(el('p','M1/M15 source unavailable: '+e.message,'muted'));return;}
  }
  detail();
 };
}
load().catch(e=>{set('pubState','INCOMPLETE EVIDENCE');set('pubTime','No paper direction published');
 $('ruleCards').replaceChildren(el('p','WS30 source rejected: '+e.message,'muted'));});
