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
function filtered(){return data.signals.filter(x=>window.AurumUI?.accept(x)!==false).filter(x=>x.cohort===cohort()&&
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
 const r=await fetch('ws30-intrabar.json',{cache:'no-cache'});
 if(!r.ok)throw Error('Intrabar evidence unavailable HTTP '+r.status);
 const v=await r.json();
 if(v.symbol!=='WS30.pro'||v.total_cases!==189||
 v.scope!=='ARCHIVED_HISTORICAL_INTRABAR_CHART_DATA_NOT_PROSPECTIVE'||
 v.model_input_hash!==data.meta.source_reference_inventory_sha256)
  throw Error('M1/M15 historical source provenance mismatch');
 intrabar=v;
}
async function load(){
 const q=await fetch('ws30-data.json',{cache:'no-cache'});
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


/* WS30 feature parity v2: presentation only. Frozen rules and scores unchanged. */
const originalPathSvg=pathSvg, originalDetail=detail, originalRegister=register;
let indicators=[], requestSequence=0, lastGood=null;
let moveCache=new Map();
function sampledMove(r){
 if(moveCache.has(r.id))return moveCache.get(r.id);
 const closes=data.candles.filter(b=>b.time>=r.entry_time&&b.close_time<(r.exit_time||r.horizon_end)).map(b=>sign(r)*(b.close-r.entry_reference));
 const ep=exitPrice(r);if(ep!==null)closes.push(sign(r)*(ep-r.entry_reference));
 const value=Math.max(0,...closes);moveCache.set(r.id,value);return value;
}
function overlaps(r){return data.signals.filter(z=>z.id!==r.id&&z.entry_time<=(r.exit_time||r.horizon_end)&&(z.exit_time||z.horizon_end)>=r.entry_time);}
const isNum=v=>typeof v==='number'&&Number.isFinite(v);
const sign=r=>r.direction==='BUY'?1:-1;
const risk=r=>Math.abs(r.entry_reference-r.initial_stop);
const exitPrice=r=>r.score_final&&isNum(r.score_R_min)?r.entry_reference+sign(r)*r.score_R_min*risk(r):null;
function computeIndicators(candles){
 const ns=[10,12,20,26,50,200],state={},main=[];
 return candles.map((b,i)=>{
  const prev={...state};
  for(const n of ns)state[n]=i?state[n]+2/(n+1)*(b.close-state[n]):b.close;
  const macd=state[12]-state[26];main.push(macd);
  const signal=i>=8?main.slice(-9).reduce((a,b)=>a+b,0)/9:null;
  return {...b,e10:state[10],e20:state[20],e50:state[50],e200:state[200],
   d10:i?state[10]-prev[10]:null,d20:i?state[20]-prev[20]:null,d50:i?state[50]-prev[50]:null,
   macd,macdSignal:signal};
 });
}
function selectedMetrics(){
 const rows=filtered(),done=rows.filter(r=>r.score_final&&isNum(r.score_R_min));
 const n=k=>rows.filter(r=>r.status===k).length;
 set('selectedCount',rows.length);
 set('selectedSides',rows.filter(r=>r.direction==='BUY').length+' BUY · '+rows.filter(r=>r.direction==='SELL').length+' SELL · '+new Set(rows.map(r=>r.economic_key)).size+' distinct economic entries');
 set('nonnegativeRate',pct(done.filter(r=>r.score_R_min>=0).length,done.length));
 set('selectedOutcomes',n('WIN')+' TP · '+n('LOSS')+' SL · '+n('BE')+' BE · '+n('TIMEOUT')+' timeout');
 set('selectedGross',done.length?format(done.reduce((a,r)=>a+r.score_R_min,0),3)+' R':'—');
 set('selectedExcluded',(rows.length-done.length)+' not final-scored; BE counts as nonnegative. Admission sums include shared entries.');
 set('selectedTarget',pct(done.filter(r=>r.status==='WIN').length,done.length));
}
register=function(){
 originalRegister();selectedMetrics();
 const tableRecords=filtered().sort((a,b)=>a.entry_time.localeCompare(b.entry_time)).reverse();
 [...$('signalRows').children].forEach((tr,i)=>{
  const r=tableRecords[i];if(!r){tr.firstChild.colSpan=15;return;}
  const unit=r.score_final&&isNum(r.score_R_min)?format(r.score_R_min*risk(r),1):'Unresolved';
  for(const v of [format(r.target,1)+' / '+format(r.initial_stop,1),r.exit_time||'Pending',unit,
   format(sampledMove(r),1)+' units / '+format(sampledMove(r)/r.ATR,2)+' ATR',overlaps(r).length,
   r.observed_at||'Historical replay'])tr.insertBefore(el('td',v),tr.lastChild);
 });
 const records=filtered().slice().sort((a,b)=>b.entry_time.localeCompare(a.entry_time)||a.rule.localeCompare(b.rule));
 if(!records.some(r=>r.id===chosen))chosen=records[0]?.id||null;
 const picker=$('selected');picker.replaceChildren();
 if(!records.length){const o=el('option','No matching entries');o.value='';picker.append(o);}
 for(const r of records){const o=el('option',r.entry_time+' · '+r.rule+' · '+r.direction+' · '+r.status);o.value=r.id;picker.append(o);}
 if(chosen)picker.value=chosen;
 $('latest').disabled=!records.length;$('export').disabled=!records.length;
};
detail=function(){
 if(!filtered().some(r=>r.id===chosen))chosen=filtered().slice().sort((a,b)=>b.entry_time.localeCompare(a.entry_time))[0]?.id||null;
 originalDetail();
 const r=data.signals.find(r=>r.id===chosen);
 $('features').replaceChildren();
 if(!r){set('overlapDetails','No matching entry.');set('journeyLegend','');return;}
 $('selected').value=chosen;
 const i=indicators.findLast(z=>z.close_time<=r.signal_time);
 const tr=el('tr');
 for(const v of i?[i.close_time,i.e10,i.e20,i.e50,i.e200,i.d10,i.d20,i.d50,i.macd,i.macdSignal]:['No completed source candle']){
  tr.append(el('td',typeof v==='number'?format(v,5):v));
 }
 $('features').append(tr);
 const overlap=overlaps(r);
 set('overlapDetails',r.id+' · '+overlap.length+' overlapping admissions. '+overlap.map(z=>z.rule+' '+z.direction+' '+z.entry_time+(z.economic_key===r.economic_key?' [same economic entry]':'')).join('; '));
 evidenceBox($('caseFacts'),'TP / SL price distances',format(Math.abs(r.target-r.entry_reference),1)+' / '+format(risk(r),1)+' index units');
 evidenceBox($('caseFacts'),'TP / SL broker points',format(Math.abs(r.target-r.entry_reference)/r.native_point,0)+' / '+format(risk(r)/r.native_point,0));
 evidenceBox($('caseFacts'),'Exit price reference',exitPrice(r)===null?'Unresolved':format(exitPrice(r),1));
 evidenceBox($('caseFacts'),'Sampled favourable close move',format(sampledMove(r),1)+' index units / '+format(sampledMove(r)/r.ATR,2)+' ATR; not intrabar MFE');
 evidenceBox($('caseFacts'),'Detection',r.observed_at||'Historical replay; not a prospective detection');
};
pathSvg=function(r){
 if($('chartMode').value==='frozen'){
  originalPathSvg(r);set('journeyLegend','Original archived ATR evidence. Chart selection never changes the outcome.');return;
 }
 drawFeatureChart(r);
};
function drawFeatureChart(r){
 const root=$('riskGraphic');root.replaceChildren();
 const tf=$('chartTf').value,technical=$('chartMode').value==='technical';
 const source=tf==='H1'?indicators:(intrabar?.cases?.[r.id]?.[tf]||[]);
 if(!source.length){root.append(el('p','No verified '+tf+' evidence for this admission.','muted'));return;}
 let ei=source.findIndex(b=>b.time>=r.entry_time);if(ei<0){root.append(el('p','Entry is outside published chart coverage.'));return;}
 const end=r.exit_time||r.horizon_end;
 let xi=source.findIndex(b=>b.close_time>=end);if(xi<0)xi=source.length-1;
 const scale=tf==='M15'?4:tf==='M1'?60:1;
 const before=Math.round(Number($('chartRange').value)*.67)*scale;
 let tail=r.status==='WIN'?48*scale:2*scale;
 const finish=r.status==='WIN'&&$('postContext').value==='all'?source.length:Math.min(source.length,xi+tail+1);
 const bars=source.slice(Math.max(0,ei-before),finish);
 const W=1100,H=technical?590:430,L=20,R=115,T=26,B=50,priceBottom=technical?380:H-B;
 const vals=bars.flatMap(b=>[b.low,b.high]).concat([r.entry_reference,r.target,r.initial_stop,r.BE_threshold]);
 let low=Math.min(...vals),high=Math.max(...vals),pad=(high-low)*.06||1;low-=pad;high+=pad;
 const y=p=>T+(high-p)/(high-low)*(priceBottom-T);
 // Equal bar spacing respects observed sessions; missing intervals are disconnected.
 const at=t=>{let n=bars.findIndex(b=>b.close_time>=t);return n<0?bars.length-1:n;};
 const x=i=>L+i/Math.max(1,bars.length-1)*(W-L-R);
 const xt=t=>x(at(t)),entryX=xt(r.entry_time);
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
 svg.setAttribute('viewBox','0 0 '+W+' '+H);svg.setAttribute('role','img');
 svg.setAttribute('aria-label',technical?'WS30 candles, EMA and MACD inspection':'WS30 entry journey, target guide, observed reversal and post-TP context');
 const add=(tag,attrs,value)=>{
  const z=document.createElementNS(svg.namespaceURI,tag);
  Object.entries(attrs).forEach(([k,v])=>z.setAttribute(k,String(v)));
  if(value!==undefined)z.textContent=value;svg.append(z);return z;
 };
 for(let j=0;j<5;j++){const p=low+(high-low)*j/4;add('line',{x1:L,x2:W-R,y1:y(p),y2:y(p),stroke:'#294044'});add('text',{x:W-R+8,y:y(p)+4,fill:'#a4b5b6','font-size':11},format(p,1));}
 for(const [label,p,c] of [['Entry',r.entry_reference,'#b7a988'],['TP +2ATR',r.target,'#75cbb1'],['SL −3ATR',r.initial_stop,'#de918c'],['BE threshold +1ATR',r.BE_threshold,'#b4a0d4']]){
  add('line',{x1:L,x2:W-R,y1:y(p),y2:y(p),stroke:c,'stroke-dasharray':label==='Entry'?'0':'4 5',opacity:.6});
  add('text',{x:L+6,y:y(p)-5,fill:c,'font-size':10},label);
 }
 const seconds=t=>Date.parse(t.replace(' ','T')+'Z')/1000;
 const gapLimit=(tf==='H1'?3600:tf==='M15'?900:60)*1.5;
 const gap=(a,b)=>seconds(b.time)-seconds(a.time)>gapLimit;
 if(technical){
  const stride=Math.max(1,Math.ceil(bars.length/900));
  for(let j=0;j<bars.length;j+=stride){const b=bars[j],c=b.close>=b.open?'#7ccdb2':'#d98e8b',bw=Math.max(.8,Math.min(8,(W-R-L)/bars.length*.65));
   add('line',{x1:x(j),x2:x(j),y1:y(b.high),y2:y(b.low),stroke:c,opacity:.7});
   add('rect',{x:x(j)-bw/2,y:Math.min(y(b.open),y(b.close)),width:bw,height:Math.max(1,Math.abs(y(b.open)-y(b.close))),fill:c});
  }
  if(tf==='H1'){
   for(const [key,c] of [['e10','#d6ba78'],['e20','#79b0d5'],['e50','#af90d6'],['e200','#94ab98']]){
    const d=bars.map((b,j)=>(j===0||gap(bars[j-1],b)?'M':'L')+x(j)+','+y(b[key])).join(' ');
    add('path',{d,stroke:c,'stroke-width':1.5,fill:'none','data-role':key});
   }
   const m=bars.flatMap(b=>[b.macd,b.macdSignal]).filter(isNum),mlo=Math.min(0,...m),mhi=Math.max(0,...m),my=v=>425+(mhi-v)/(mhi-mlo||1)*100;
   add('text',{x:L,y:411,fill:'#b2c3c3','font-size':12},'Display MACD12/26 · SMA9 signal');
   add('line',{x1:L,x2:W-R,y1:my(0),y2:my(0),stroke:'#496065'});
   for(const [key,c] of [['macd','#79b0d5'],['macdSignal','#d6ba78']]){
    let pen=false;const d=bars.map((b,j)=>{if(!isNum(b[key])){pen=false;return '';}const p=(!pen||(j&&gap(bars[j-1],b))?'M':'L')+x(j)+','+my(b[key]);pen=true;return p;}).join(' ');
    add('path',{d,stroke:c,'stroke-width':1.5,fill:'none','data-role':key});
   }
  }else add('text',{x:L,y:420,fill:'#b2c3c3','font-size':12},'EMA/MACD inspection is available on H1. Intrabar evidence retains native OHLC.');
 }else{
  add('path',{d:'M'+entryX+','+y(r.entry_reference)+' L'+(W-R)+','+y(r.target),fill:'none',stroke:'#d6ba78','stroke-width':2,'stroke-dasharray':'1 7','stroke-linecap':'round','data-role':'target-guide'});
  const context=bars.map((b,j)=>(j===0||gap(bars[j-1],b)?'M':'L')+x(j)+','+y(b.close)).join(' ');
  add('path',{d:context,stroke:'#6c858a','stroke-width':1,opacity:.35,fill:'none','data-role':'context'});
  let prior={time:r.entry_time,price:r.entry_reference},peak=0,marked=false;
  const active=bars.filter(b=>b.time>=r.entry_time&&b.close_time<end);
  for(const b of active){
   const profit=sign(r)*(b.close-r.entry_reference),adverse=sign(r)*(b.close-prior.price)<0;
   if(seconds(b.time)-seconds(prior.time)<=gapLimit){
    add('path',{d:'M'+xt(prior.time)+','+y(prior.price)+' L'+xt(b.close_time)+','+y(b.close),stroke:adverse?'#ec9bab':'#79cbb1','stroke-width':2.7,fill:'none','stroke-dasharray':adverse?'3 8':'0','data-role':adverse?'reversal':'observed'});
   }
   if(tf==='H1'&&!marked&&peak>0&&profit<peak/2){
    add('circle',{cx:xt(b.close_time),cy:y(b.close),r:4,fill:'#ec9bab','data-role':'retracement-marker'});
    add('text',{x:xt(b.close_time)+6,y:y(b.close)-9,fill:'#ec9bab','font-size':10},'>50% close retracement (display)');
    marked=true;
   }
   peak=Math.max(peak,profit);prior={time:b.close_time,price:b.close};
  }
  const ep=exitPrice(r);
  if(ep!==null){add('path',{d:'M'+xt(prior.time)+','+y(prior.price)+' L'+xt(end)+','+y(ep),stroke:sign(r)*(ep-prior.price)<0?'#ec9bab':'#79cbb1','stroke-width':2.7,'stroke-dasharray':sign(r)*(ep-prior.price)<0?'3 8':'0',fill:'none','data-role':'exit-segment'});}
  if(r.status==='WIN'){
   const post=bars.filter(b=>b.close_time>end);
   let prev={time:end,price:r.target};
   for(const b of post){if(seconds(b.time)-seconds(prev.time)<=gapLimit)add('path',{d:'M'+xt(prev.time)+','+y(prev.price)+' L'+xt(b.close_time)+','+y(b.close),stroke:'#b59ae4','stroke-width':2,fill:'none','data-role':'post-tp'});prev={time:b.close_time,price:b.close};}
  }
 }
 add('circle',{cx:entryX,cy:y(r.entry_reference),r:5,fill:'#e4c986','data-role':'entry'});
 const ep=exitPrice(r);
 if(ep!==null){
  add('circle',{cx:xt(end),cy:y(ep),r:5,fill:'#eddbc0','data-role':'exit'});
  add('text',{x:Math.min(xt(end)+8,W-R-100),y:y(ep)+18,fill:'#eddbc0','font-size':11},r.status+' '+format(ep,1));
 }
 if(r.BE_armed_at){
  add('line',{x1:xt(r.BE_armed_at),x2:xt(end),y1:y(r.entry_reference),y2:y(r.entry_reference),stroke:'#baa4e2','stroke-width':3,'data-role':'be-armed'});
  add('text',{x:xt(r.BE_armed_at),y:priceBottom+18,fill:'#baa4e2','font-size':10},'Actual BE armed '+r.BE_armed_at.slice(5,16));
 }
 for(let j=0;j<4;j++){const i=Math.round((bars.length-1)*j/3);add('text',{x:x(i),y:H-12,fill:'#a4b5b6','font-size':11,'text-anchor':j===0?'start':j===3?'end':'middle'},bars[i].time.slice(0,16));}
 root.append(svg);
 set('journeyLegend',technical?'Candles and display-only EMA10 gold / EMA20 blue / EMA50 purple / EMA200 grey. MACD uses SMA9. Dense charts sample candle glyphs; lines retain source bars.':
  'Dotted target guide · solid observed closes · spaced pink adverse movement · purple post-TP context (excluded from P/L). Exit marker uses the archived score reference; connecting segments do not reconstruct intrabar prices.');
 set('chartCaution','Source: '+tf+' completed candles. Exit/BE timestamps retain archived M1/H1 evidence. '+(tf==='M1'?'M1 data covers archived entry/exit windows, not a continuous full history. ':tf==='M15'?'Post-TP context is limited by archived M15 coverage. ':'')+'No extra P/L after exit. A chart retracement marker never activates the WS30 stop.');
}
function csvCell(v){let s=v==null?'':String(v);if(/^[=+@\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';}
function exportRows(){
 const fields=['id','cohort','rule','rule_version','branch','direction','signal_time','entry_time','entry_reference','ATR','ATR_anchor','target','initial_stop','BE_threshold','BE_armed_at','status','exit_time','score_final','score_R_min','score_R_max','gap_adjusted_R_min','spread_proxy_net_R_min','economic_key','native_point','observed_at','origin'];
 const rows=filtered().slice().sort((a,b)=>a.entry_time.localeCompare(b.entry_time));
 const csv='\ufeff'+[fields.map(csvCell).join(','),...rows.map(r=>fields.map(k=>csvCell(r[k])).join(','))].join('\r\n');
 const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
 const a=el('a');a.href=url;a.download='WS30_'+cohort()+'_'+$('ruleFilter').value+'_'+$('sideFilter').value+'_'+$('monthFilter').value+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function clearEvidence(message){
 data=null;chosen=null;lastGood=null;indicators=[];
 for(const id of ['ruleCards','summaryRows','signalRows','riskGraphic','caseFacts','features','paperRows','provenance','selected'])$(id).replaceChildren();
 for(const id of ['selectedCount','nonnegativeRate','selectedGross','selectedTarget','numEntries','numDistinct','latestH1','paperIntents','paperFinal','paperMissed','paperCensored'])set(id,'—');
 for(const id of ['selectedSides','selectedOutcomes','selectedExcluded','journeyLegend','overlapDetails','filterCount','caseSubtitle'])set(id,'');
 set('caseTitle','Evidence unavailable');set('pubState','INCOMPLETE EVIDENCE');set('pubTime','No current evidence displayed');
 set('notice',message);$('export').disabled=true;$('latest').disabled=true;$('download').removeAttribute('href');
}
async function refreshFeatures(){
 const seq=++requestSequence,prevMonth=$('monthFilter').value,prevChosen=chosen;
 $('reload').disabled=true;set('notice','Loading verified published evidence…');
 try{
  const [response,cfgResponse]=await Promise.all([fetch($('dataset').value,{cache:'no-cache'}),fetch('ws30-config.json',{cache:'no-cache'})]);
  if(!response.ok||!cfgResponse.ok)throw Error('Snapshot/configuration unavailable');
  const [v,cfg]=await Promise.all([response.json(),cfgResponse.json()]);
  if(seq!==requestSequence)return;
  if(cfg.enabled===false||cfg.paper_only!==true||cfg.broker_orders_enabled!==false)throw Error('WS30 disabled or configuration mismatch');
  if(v.meta?.symbol!=='WS30.pro'||v.meta?.market_clock!=='NATIVE_BROKER_LABELS_NO_CONVERSION'||v.meta?.broker_orders_enabled!==false||
   !['HISTORICAL_REPLAY','MIXED_LABELLED','PROSPECTIVE_PAPER'].includes(v.meta?.scope)||
   !Array.isArray(v.signals)||!Array.isArray(v.candles)||!v.candles.length||!v.health||
   new Set(v.signals.map(r=>r.id)).size!==v.signals.length||
   RULES.some(k=>!v.meta.rule_manifest_hashes?.[k]||v.meta.rule_manifest_hashes[k]!==cfg.rule_manifest_hashes?.[k])||
   v.signals.some(r=>!RULES.includes(r.rule)||!['BUY','SELL'].includes(r.direction)||r.native_point!==.1||!isNum(r.entry_reference)||!isNum(r.ATR)||r.ATR<=0))
    throw Error('Instrument, scale, rule identity or evidence mismatch');
  if(data&&data.meta.source_reference_inventory_sha256!==v.meta.source_reference_inventory_sha256)intrabar=null;
  data=v;lastGood=v;moveCache=new Map();indicators=computeIndicators(v.candles);chosen=prevChosen;
  setupTop();summary();months();
  if([...$('monthFilter').options].some(o=>o.value===prevMonth))$('monthFilter').value=prevMonth;
  register();detail();paperJournal();health();
  const frozen=$('dataset').value==='ws30-replay.json',age=Date.now()-Date.parse(v.health.snapshot_generated_utc);
  const stale=!frozen&&(!Number.isFinite(age)||age>90*60000);
  if(frozen)set('pubState','FROZEN REPLAY');else if(stale)set('pubState','STALE SNAPSHOT');
  set('notice',(frozen?'Frozen deployment replay. ':stale?'Published snapshot is stale. ':'Latest published snapshot. ')+
   'Market/source: '+text(v.health.session_or_observer_state||v.health.state)+'. Last H1: '+text(v.health.last_confirmed_broker_H1)+
   '. Published '+text(v.health.snapshot_generated_utc)+'. Research observations; no executed orders.');
  $('download').href=$('dataset').value;
 }catch(e){if(seq===requestSequence)clearEvidence('WS30 source unavailable: '+e.message);}
 finally{if(seq===requestSequence)$('reload').disabled=false;}
}
async function instrumentPicker(){
 try{
  const q=await fetch('assets.json',{cache:'no-cache'});if(!q.ok)return;
  const registry=await q.json();$('instrument').replaceChildren();
  for(const a of registry.assets||[]){const o=el('option',a.symbol+' · '+a.name+(a.status==='published'?'':' · not published'));o.value=a.symbol;$('instrument').append(o);}
  $('instrument').value='WS30.pro';
  $('instrument').onchange=()=>{const a=registry.assets.find(a=>a.symbol===$('instrument').value);if(!a)return;
   location.href=a.module_page||'index.html?asset='+encodeURIComponent(a.symbol);};
 }catch(e){/* Keep WS30 selected if the navigation registry is unavailable. */}
}
for(const id of ['cohort','ruleFilter','sideFilter','outcomeFilter','monthFilter']){
 $(id).onchange=()=>{if(!data)return;if(id==='cohort'){months();summary();}chosen=null;register();detail();};
}
$('selected').onchange=()=>{if(data){chosen=$('selected').value;detail();}};
$('latest').onclick=()=>{if(!data)return;chosen=filtered().slice().sort((a,b)=>b.entry_time.localeCompare(a.entry_time))[0]?.id;detail();};
$('export').onclick=exportRows;
$('reload').onclick=$('dataset').onchange=refreshFeatures;
for(const id of ['chartMode','chartRange','postContext'])$(id).onchange=()=>{if(data)detail();};
$('chartTf').onchange=async()=>{
 if(!data)return;
 try{if($('chartTf').value!=='H1'){ $('riskGraphic').replaceChildren(el('p','Loading verified intrabar evidence…','muted'));await loadIntrabar();}if(data)detail();}
 catch(e){$('riskGraphic').replaceChildren(el('p','Intrabar source unavailable: '+e.message,'muted'));}
};
setInterval(()=>{if(!document.hidden&&$('dataset').value==='ws30-data.json')refreshFeatures();},15*60*1000);

$('inspectFrozen').onclick=async()=>{
 const button=$('inspectFrozen');button.disabled=true;
 try{
  $('dataset').value='ws30-replay.json';
  // Preserve cohort/model/direction, but reveal entries hidden by outcome/month.
  $('outcomeFilter').value='all';$('monthFilter').value='all';
  $('chartTf').value='H1';chosen=null;
  await refreshFeatures();
  if(!data||$('dataset').value!=='ws30-replay.json')return;
  if(!filtered().length){$('ruleFilter').value='all';$('sideFilter').value='all';register();detail();}
  if(chosen){$('detail').scrollIntoView({behavior:'smooth',block:'start'});$('selected').focus({preventScroll:true});}
 }finally{button.disabled=false;}
};

instrumentPicker();refreshFeatures();
