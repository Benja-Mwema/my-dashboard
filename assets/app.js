const $=id=>document.getElementById(id);
const state={meta:null};
const FORCE_STATIC=new URLSearchParams(location.search).get('static')==='1';
const LIVE_API_HOSTS=new Set(['127.0.0.1','localhost']);
const USE_STATIC_SNAPSHOT=FORCE_STATIC||!LIVE_API_HOSTS.has(location.hostname);
let snapshotPromise=null;

async function dashboardSnapshot(){
  if(!snapshotPromise){
    snapshotPromise=fetch('/data/dashboard_snapshot.json',{cache:'no-store'}).then(async r=>{
      if(!r.ok) throw new Error(`Static snapshot unavailable: HTTP ${r.status}`);
      return r.json();
    });
  }
  return snapshotPromise;
}

function staticApiRoute(s,path){
  const u=new URL(path,location.origin),q=u.searchParams,route=u.pathname;
  if(route==='/api/meta') return s.meta||{};
  if(route==='/api/overview') return s.overview||{};
  if(route==='/api/opportunities') return s.opportunities||{};
  if(route==='/api/opportunity') return (s.opportunity||{})[q.get('id')||'']||{};
  if(route==='/api/weekly'){
    let cutoff=q.get('cutoff_date')||'';
    if(!cutoff){const weeks=(s.meta||{}).weeks||[]; cutoff=weeks[0]?.cutoff_date||'';}
    return (s.weekly||{})[cutoff]||{};
  }
  if(route==='/api/validation') return s.validation||{};
  if(route==='/api/health') return s.health||{};
  throw new Error(`Static route unavailable: ${route}`);
}

async function api(path){
  if(USE_STATIC_SNAPSHOT) return staticApiRoute(await dashboardSnapshot(),path);
  const r=await fetch(path,{cache:'no-store'});
  if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e.message||`HTTP ${r.status}`)}
  return r.json();
}
function esc(v){return String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function n(v,d=2){if(v===null||v===undefined||v==='')return'—';const x=Number(v);return Number.isFinite(x)?x.toLocaleString(undefined,{maximumFractionDigits:d}):String(v)}
function pct(v){return v===null||v===undefined?'—':`${n(v,1)}%`}
function t(v){if(!v)return'—';return String(v).replace('T',' ').replace('+03:00',' EAT').replace('.000','')}
function shortT(v){const s=t(v);return s==='—'?s:(s.length>16?s.slice(5,16):s)}
function kind(v){const s=String(v||'').toUpperCase();if(['CURRENT','PASS','FROZEN','ATR1_REACHED','EXPANDING','QUALIFIED','QUALIFIED_ONCE','SUCCESS','CLOSED_WIN'].includes(s))return'good';if(['ERROR','FAIL','FAILED','STALE','CLOSED_LOSS'].includes(s))return'bad';if(['LAGGING','PROCESSING','DEVELOPING','CANDIDATE','WATCHING','PENDING'].includes(s))return'warn';return'info'}
function badge(v,k){return`<span class="badge ${k||kind(v)}">${esc(v||'—')}</span>`}
function sideBadge(v){return badge(v,v==='BUY'?'good':v==='SELL'?'bad':'info')}
function metric(label,value,sub='',k='info'){return`<div class="metric ${k}"><small>${esc(label)}</small><strong>${esc(value)}</strong>${sub?`<span>${esc(sub)}</span>`:''}</div>`}
function detail(label,value){return`<div class="detail"><small>${esc(label)}</small><strong>${value??'—'}</strong></div>`}
function renderTable(el,rows,cols){if(!el)return;if(!rows?.length){el.innerHTML='<tbody><tr><td class="muted">No records for this selection.</td></tr></tbody>';return}const h=cols.map(c=>`<th>${esc(c.label)}</th>`).join('');const b=rows.map(r=>'<tr>'+cols.map(c=>`<td class="${c.cls||''}">${c.fmt?c.fmt(r[c.key],r):esc(r[c.key])}</td>`).join('')+'</tr>').join('');el.innerHTML=`<thead><tr>${h}</tr></thead><tbody>${b}</tbody>`}
function showTab(name){document.querySelectorAll('.tab-page').forEach(x=>x.classList.toggle('active',x.id===`tab-${name}`));document.querySelectorAll('#tabs button').forEach(x=>x.classList.toggle('active',x.dataset.tab===name));history.replaceState(null,'',`#${name}`)}
async function loadMeta(){
  state.meta=await api('/api/meta');
  const weeks=state.meta.weeks||[];
  $('weekSelect').innerHTML=weeks.map(w=>`<option value="${esc(w.cutoff_date)}">${esc(`${w.forecast_week_start} → ${w.forecast_week_end}`)}</option>`).join('');
  const live=state.meta.live_opportunities||[], hist=state.meta.historical_opportunities||[];
  const opts=[...live.map(o=>({...o,scope:'LIVE'})),...hist.map(o=>({...o,scope:'HIST'}))];
  $('opportunitySelect').innerHTML=opts.map(o=>`<option value="${esc(o.opportunity_id)}">${esc(`${o.start_time} · ${o.side} · ${o.first_tf} · ${o.timeframes} · ${o.qualification_status||'QUALIFIED_ONCE'} · ${o.outcome_status||'PENDING'}`)}</option>`).join('');
  const jc=state.meta.journey_coverage||{},days=jc.recent_days||[];
  const gap=days.filter(x=>Number(x.qualified||0)===0).slice(0,4);
  const gapText=gap.length?gap.map(x=>`${x.date}: ${x.evaluated} evaluated / 0 qualified`).join(' · '):'No recent qualification gaps.';
  $('journeyCoverage').className='status-band info';
  $('journeyCoverage').innerHTML=`<div><small>LAST QUALIFIED</small><strong>${esc(t(jc.latest_qualified_signal))}</strong></div><div><small>EVALUATED THROUGH</small><strong>${esc(t(jc.latest_evaluated_signal))}</strong></div><p>${esc(gapText)}. The selector lists qualified opportunities only; evaluated-but-unqualified days are not removed data.</p>`;
}
function currentOppHtml(o){
  if(!o?.opportunity_id)return'<div class="opportunity-hero"><div class="big"><small>Current state</small><strong>No active BEN opportunity</strong></div><div class="note">Only Samuel EXIT events are monitored. Official live opportunities currently require an active EXIT-only M30 or H1 forward rule; M15 EXITs are research-only until re-hardened.</div></div>';
  const prog=n(o.progress_atr,2),mfe=n(o.mfe_atr,2),mae=n(o.mae_atr,2);
  return`<div class="opportunity-hero"><div class="big"><small>${esc(o.side)} opportunity · ${esc(o.movement_state||o.status)}</small><strong>${n(o.current_price,2)}</strong></div>${detail('Qualification',badge(o.qualification_status||'QUALIFIED_ONCE','good'))}${detail('Outcome',badge(o.outcome_status||'PENDING',kind(o.outcome_status||'PENDING')))}${detail('Started',esc(t(o.start_time)))}${detail('First timeframe',badge(o.first_tf,'info'))}${detail('Participating TFs',esc(o.timeframes))}${detail('Signals',esc(o.signal_count))}${detail('Progress',esc(`${prog} H1 ATR`))}${detail('MFE / MAE',esc(`${mfe} / ${mae} ATR`))}<div class="note">Qualification is latched permanently once achieved. Later bars can change only the journey/outcome state, never erase the original qualification.</div></div>`;
}
async function loadOverview(){
  const p=await api('/api/overview'),s=p.status||{},o=p.focus||{};
  const st=s.source_lag_status||'UNKNOWN';
  $('overviewStatus').className=`status-band ${kind(st)}`;
  $('overviewStatus').innerHTML=`<div><small>LIVE SOURCE</small><strong>${esc(st)}</strong></div><div><small>OPEN OPPORTUNITIES</small><strong>${esc(s.open_opportunities??0)}</strong></div><p>${o.opportunity_id?'A BEN EXIT opportunity is active. The panels below show how it was qualified and how the move is developing.':'No official EXIT opportunity is currently open. M30/H1 EXIT rules remain active; M15 EXITs are tracked in research only.'}</p>`;
  $('overviewMetrics').innerHTML=[metric('EXIT Events Today',p.ben_events_today??0,'Samuel EXIT buffer hits only'),metric('Qualified Signals Today',p.qualified_signals_today??0,'EXITs that passed an active forward rule',p.qualified_signals_today?'good':'info'),metric('Open Opportunities',s.open_opportunities??0,'Unique live opportunities',s.open_opportunities?'good':'info'),metric('Source Lag',`${n(s.source_lag_bars??0,0)} bars`,`${n(s.source_lag_minutes??0,0)} minutes`,s.source_lag_bars?'bad':'good')].join('');
  $('currentOpportunity').innerHTML=currentOppHtml(o);
  renderTable($('mtfTable'),p.mtf||[],[
    {key:'timeframe',label:'TF',fmt:v=>badge(v,'info')},{key:'close_time',label:'Closed',fmt:v=>shortT(v)},{key:'close',label:'Close',fmt:v=>n(v,2),cls:'num'},
    {key:'jrsx_main',label:'JRSX',fmt:v=>n(v,1),cls:'num'},{key:'jrsx_direction',label:'Direction',fmt:v=>sideBadge(v)},{key:'ben_signal',label:'BEN Signal',fmt:v=>badge(v,v==='NONE'?'info':kind(v))}
  ]);
  renderTable($('constructionTable'),p.construction||[],[
    {key:'sequence_no',label:'#',fmt:v=>n(v,0),cls:'num'},{key:'signal_time',label:'Time',fmt:v=>shortT(v)},{key:'timeframe',label:'TF',fmt:v=>badge(v,'info')},
    {key:'side',label:'Side',fmt:v=>sideBadge(v)},{key:'qualification_status',label:'Qualification',fmt:v=>badge(v||'QUALIFIED_ONCE','good')},
    {key:'outcome_status',label:'Outcome',fmt:v=>badge(v||'PENDING',kind(v||'PENDING'))},{key:'rule_ids',label:'Rule'},{key:'engine_version',label:'Version'},
    {key:'latest_recheck_qualified',label:'Latest Recheck',fmt:(v,r)=>r.latest_rechecked_at?badge(v===1?'PASS':'WOULD FAIL',v===1?'good':'warn'):'—'}
  ]);
  renderTable($('todayTable'),p.today_opportunities||[],[
    {key:'start_time',label:'Start',fmt:v=>shortT(v)},{key:'side',label:'Side',fmt:v=>sideBadge(v)},{key:'first_tf',label:'First TF'},
    {key:'qualification_status',label:'Qualification',fmt:v=>badge(v||'QUALIFIED_ONCE','good')},{key:'outcome_status',label:'Outcome',fmt:v=>badge(v||'PENDING',kind(v||'PENDING'))},
    {key:'timeframes',label:'TFs'},{key:'signal_count',label:'Signals',fmt:v=>n(v,0),cls:'num'},{key:'status',label:'Journey',fmt:v=>badge(v,kind(v))},{key:'close_reason',label:'Close Reason'}
  ]);
  renderTable($('shadowHandoverTable'),p.shadow_handovers||[],[
    {key:'m15_signal_time',label:'M15 EXIT',fmt:v=>shortT(v)},
    {key:'m30_signal_time',label:'M30 EXIT',fmt:v=>shortT(v)},
    {key:'side',label:'Side',fmt:v=>sideBadge(v)},
    {key:'gap_minutes',label:'Gap',fmt:v=>`${n(v,0)}m`,cls:'num'},
    {key:'m15_qualified',label:'M15 V1',fmt:v=>badge(Number(v)===1?'QUALIFIED':'NO','info')},
    {key:'m30_qualified',label:'M30 V1',fmt:v=>badge(Number(v)===1?'QUALIFIED':'NO','info')},
    {key:'m15_progress_at_m30_atr',label:'Progress @ M30',fmt:v=>`${n(v,2)} ATR`,cls:'num'},
    {key:'m15_m30_eff10',label:'M30 Eff @ M15',fmt:v=>n(v,3),cls:'num'},
    {key:'research_flags',label:'Research Flags'},
    {key:'shadow_status',label:'Status',fmt:v=>badge(v||'SHADOW_ONLY','warn')}
  ]);
}
function movementExplanation(h){
  const state=String(h.movement_state||h.status||'QUALIFIED');
  const map={QUALIFIED:'The tested qualification rule has been satisfied and journey tracking begins. This is the start of the opportunity, not a profit target.',DEVELOPING:'Price is moving constructively in the qualified direction, but the move has not yet shown strong expansion.',EXPANDING:'The opportunity is showing stronger directional expansion. Continue to read MFE and MAE as journey measurements rather than entry instructions.',ATR1_REACHED:'Price has travelled at least one starting H1 ATR favorably. This is a live movement milestone; it is not the historical MAJOR label.',CLOSED:'Tracking has ended. Review the close reason together with the full journey and signal sequence.'};
  return map[state]||'The opportunity is being tracked from its first qualified BEN signal through subsequent price development.';
}
async function loadJourney(){
  const id=$('opportunitySelect').value;if(!id)return;
  const p=await api(`/api/opportunity?id=${encodeURIComponent(id)}`),h=p.header||{},j=p.journey||[],last=j[j.length-1]||h;
  $('journeyHeader').className=`status-band ${kind(last.movement_state||h.status)}`;
  $('journeyHeader').innerHTML=`<div><small>QUALIFICATION</small><strong>${esc(h.qualification_status||'QUALIFIED_ONCE')}</strong></div><div><small>OUTCOME</small><strong>${esc(h.outcome_status||'PENDING')}</strong></div><p>Once qualified, the signal remains qualified permanently. Journey state and final outcome are tracked separately.</p>`;
  $('journeyMetrics').innerHTML=[metric('Progress ATR',n(last.progress_atr,2),'Distance from start in qualified direction'),metric('MFE ATR',n(last.mfe_atr,2),'Best favorable excursion','good'),metric('MAE ATR',n(last.mae_atr,2),'Largest adverse excursion',Number(last.mae_atr||0)>1?'bad':'warn'),metric('Signals',h.signal_count??0,`${h.timeframes||'—'} · first ${h.first_tf||'—'}`)].join('');
  $('journeyExplanation').innerHTML=`<p>${esc(movementExplanation({...h,...last}))}</p><p><strong>Progress ATR</strong> shows movement from the opportunity start in the qualified direction. <strong>MFE</strong> is the maximum favorable excursion reached so far; <strong>MAE</strong> is the maximum adverse excursion.</p><p><strong>Historical MAJOR</strong> is evaluated only after the research window completes. Live states therefore never rename ATR1_REACHED as MAJOR.</p>`;
  $('journeyDetails').innerHTML=[detail('Opportunity ID',esc(h.opportunity_id)),detail('Scope',badge(p.scope,'info')),detail('Qualification',badge(h.qualification_status||'QUALIFIED_ONCE','good')),detail('Outcome',badge(h.outcome_status||'PENDING',kind(h.outcome_status||'PENDING'))),detail('Start',esc(t(h.start_time))),detail('End / Last Signal',esc(t(h.end_time||h.last_signal_time))),detail('First TF',badge(h.first_tf,'info')),detail('Timeframes',esc(h.timeframes)),detail('Start Price',esc(n(h.first_price||h.start_price,2))),detail('Close Reason',esc(h.outcome_reason||h.close_reason||'Open / outcome pending'))].join('');
  renderTable($('signalTimeline'),p.signals||[],[
    {key:'sequence_no',label:'#',fmt:v=>n(v,0),cls:'num'},{key:'signal_time',label:'Time',fmt:v=>t(v)},{key:'timeframe',label:'TF',fmt:v=>badge(v,'info')},{key:'side',label:'Side',fmt:v=>sideBadge(v)},
    {key:'qualification_status',label:'Qualification',fmt:v=>badge(v||'QUALIFIED_ONCE','good')},{key:'outcome_status',label:'Outcome',fmt:v=>badge(v||'PENDING',kind(v||'PENDING'))},
    {key:'rule_ids',label:'Original Rule'},{key:'qualification_latched_at',label:'Qualified At',fmt:v=>t(v)},
    {key:'latest_recheck_qualified',label:'Latest Recheck',fmt:(v,r)=>r.latest_rechecked_at?badge(v===1?'PASS':'WOULD FAIL',v===1?'good':'warn'):'—'},
    {key:'price',label:'Price',fmt:v=>n(v,2),cls:'num'}
  ]);
  renderTable($('journeyTable'),j,[
    {key:'snapshot_time',label:'Time',fmt:v=>t(v)},{key:'current_price',label:'Price',fmt:v=>n(v,2),cls:'num'},{key:'progress_atr',label:'Progress ATR',fmt:v=>n(v,2),cls:'num'},
    {key:'mfe_atr',label:'MFE ATR',fmt:v=>n(v,2),cls:'num'},{key:'mae_atr',label:'MAE ATR',fmt:v=>n(v,2),cls:'num'},{key:'movement_state',label:'State',fmt:v=>badge(v,kind(v))},{key:'close_reason',label:'Close Reason'}
  ]);
  renderTable($('contextJourneyTable'),j,[
    {key:'snapshot_time',label:'Time',fmt:v=>t(v)},{key:'m15_jrsx',label:'M15 JRSX',fmt:v=>n(v,1),cls:'num'},{key:'m15_dir',label:'M15',fmt:v=>sideBadge(v)},
    {key:'m30_jrsx',label:'M30 JRSX',fmt:v=>n(v,1),cls:'num'},{key:'m30_dir',label:'M30',fmt:v=>sideBadge(v)},{key:'h1_jrsx',label:'H1 JRSX',fmt:v=>n(v,1),cls:'num'},
    {key:'h1_dir',label:'H1',fmt:v=>sideBadge(v)},{key:'h4_jrsx',label:'H4 JRSX',fmt:v=>n(v,1),cls:'num'},{key:'h4_dir',label:'H4',fmt:v=>sideBadge(v)}
  ]);
}
function pretty(v){return String(v??'—').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase())}
function scenarioCards(map){const xs=[map.primary,map.direct_continuation,map.failure_route].filter(Boolean);return xs.map((x,i)=>`<div class="scenario-card ${i===0?'primary-scenario':''}"><strong>${esc(pretty(x.name||'Scenario'))}</strong><span>${(x.steps||[]).map(v=>esc(pretty(v))).join(' → ')}</span></div>`).join('')||'<span class="muted">No scenario map available.</span>'}
async function loadWeekly(){
  const cutoff=$('weekSelect').value,p=await api(`/api/weekly?cutoff_date=${encodeURIComponent(cutoff)}`),w=p.forecast||{},a=p.analytics||{},acc=a.accuracy||{},pos=p.position||{};
  $('weeklyMetrics').innerHTML=[metric('Weekly Bias',w.final_weekly_side||'—',`${w.forecast_week_start||'—'} → ${w.forecast_week_end||'—'}`,w.final_weekly_side==='BUY'?'good':w.final_weekly_side==='SELL'?'bad':'info'),metric('Upper Zone',`${n(w.resistance_lower,2)} – ${n(w.resistance_upper,2)}`,'Turning / resistance context'),metric('Lower Zone',`${n(w.support_lower,2)} – ${n(w.support_upper,2)}`,'Support / target context'),metric('Current Position',pos.relation||'—',pos.as_of?`as of ${shortT(pos.as_of)}`:'Latest BEN M15 close')].join('');
  $('weeklyForecast').innerHTML=`<p><strong>Frozen side:</strong> ${esc(w.final_weekly_side||'—')} with structural state ${esc(w.structural_state||'—')}.</p><p>The upper context zone is <strong>${n(w.resistance_lower,2)}–${n(w.resistance_upper,2)}</strong> with control ${n(w.resistance_control,2)}. The lower context zone is <strong>${n(w.support_lower,2)}–${n(w.support_upper,2)}</strong> with control ${n(w.support_control,2)}.</p><p>These levels describe location only. A BEN opportunity still requires an independent M15, M30 or H1 qualification.</p>`;
  $('weeklyPosition').innerHTML=[detail('Current Price',esc(n(pos.current_price,2))),detail('Map Relation',badge(pos.relation||'—','info')),detail('Upper Control Distance',esc(pos.distance_upper_control==null?'—':`${n(Math.abs(pos.distance_upper_control),2)} pts ${pos.distance_upper_control<0?'below':'above'}`)),detail('Lower Control Distance',esc(pos.distance_lower_control==null?'—':`${n(Math.abs(pos.distance_lower_control),2)} pts ${pos.distance_lower_control<0?'below':'above'}`))].join('');
  $('scenarioMap').innerHTML=scenarioCards((p.report||{}).scenario_map||{});
  const levels=((p.report||{}).level_roles||[]).slice().sort((x,y)=>(x.distance_from_cutoff??999999)-(y.distance_from_cutoff??999999)).slice(0,16);
  renderTable($('weeklyLevelTable'),levels,[{key:'center',label:'Level',fmt:v=>n(v,2),cls:'num'},{key:'report_role',label:'Role',fmt:v=>badge(v,'info')},{key:'original_role',label:'Market Role'},{key:'lower',label:'Lower',fmt:v=>n(v,2),cls:'num'},{key:'upper',label:'Upper',fmt:v=>n(v,2),cls:'num'}]);
  $('weeklyActual').innerHTML=[metric('Actual High',n(w.actual_high,2),shortT(w.actual_high_time)),metric('Actual Low',n(w.actual_low,2),shortT(w.actual_low_time)),metric('Extreme Sequence',acc.actual_extreme_first||'Pending',`Expected ${acc.expected_extreme_first||'—'}`,acc.sequence_match===true?'good':'info'),metric('Current / Final Close',n(w.actual_close,2),w.actual_last_close_time?shortT(w.actual_last_close_time):'Week still developing')].join('');
  renderTable($('weeklyOppTable'),p.ben_opportunities||[],[
    {key:'start_time',label:'Start',fmt:v=>t(v)},{key:'side',label:'Side',fmt:v=>sideBadge(v)},{key:'first_tf',label:'First TF',fmt:v=>badge(v,'info')},{key:'timeframes',label:'TFs'},
    {key:'signal_count',label:'Signals',fmt:v=>n(v,0),cls:'num'},{key:'any_major',label:'Historical Major',fmt:v=>badge(v?'YES':'NO',v?'good':'bad')},{key:'first_mfe10_atr',label:'First MFE10 ATR',fmt:v=>n(v,2),cls:'num'}
  ]);
  renderTable($('weeklyHistoryTable'),p.history||[],[
    {key:'cutoff_date',label:'Freeze'},{key:'forecast_week_start',label:'Week Start'},{key:'forecast_week_end',label:'Week End'},{key:'final_weekly_side',label:'Bias',fmt:v=>sideBadge(v)},
    {key:'structural_state',label:'Structure'},{key:'resistance_control',label:'Upper Control',fmt:v=>n(v,2),cls:'num'},{key:'support_control',label:'Lower Control',fmt:v=>n(v,2),cls:'num'},
    {key:'actual_high',label:'Actual High',fmt:v=>n(v,2),cls:'num'},{key:'actual_low',label:'Actual Low',fmt:v=>n(v,2),cls:'num'}
  ]);
}
async function loadValidation(){
  const p=await api('/api/validation'),s=p.summary||{};
  $('validationMetrics').innerHTML=[metric('Unique Opportunities',s.unique_opportunities??0,'Merged from qualified BEN signals'),metric('Major Opportunities',s.major_opportunities??0,`${pct(s.major_rate)} of unique opportunities`,'good'),metric('Non-major',s.nonmajor_opportunities??0,'Exception set for further study',s.nonmajor_opportunities?'warn':'good'),metric('Qualified Signals',s.qualified_signals??0,`${s.multi_signal??0} multi-signal · ${s.multi_tf??0} multi-TF`)].join('');
  renderTable($('rulePerformanceTable'),p.rules||[],[
    {key:'timeframe',label:'TF',fmt:v=>badge(v,'info')},{key:'status',label:'Research Status',fmt:v=>badge(v,kind(v))},{key:'engine_version',label:'Version'},
    {key:'qualified',label:'Qualified',fmt:v=>n(v,0),cls:'num'},{key:'true_count',label:'True',fmt:v=>n(v,0),cls:'num'},{key:'false_count',label:'False',fmt:v=>n(v,0),cls:'num'},{key:'major_count',label:'Major Signals',fmt:v=>n(v,0),cls:'num'},
    {key:'description',label:'Meaning',fmt:(v,r)=>esc((r.status==='CANDIDATE'?'Candidate rule: strong in-sample result; forward evidence is still required. ':'Frozen rule definition: thresholds are locked for this research version. ')+(v||''))}
  ]);
  renderTable($('monthlyTable'),p.monthly||[],[
    {key:'month',label:'Month'},{key:'qualified_signals',label:'Signals',fmt:v=>n(v,0),cls:'num'},{key:'unique_opportunities',label:'Opportunities',fmt:v=>n(v,0),cls:'num'},
    {key:'major_opportunities',label:'Major',fmt:v=>n(v,0),cls:'num'},{key:'nonmajor_opportunities',label:'Non-major',fmt:v=>n(v,0),cls:'num'},{key:'first_signal_major',label:'First Signal Major',fmt:v=>n(v,0),cls:'num'},
    {key:'m15_first',label:'M15 First',fmt:v=>n(v,0),cls:'num'},{key:'m30_first',label:'M30 First',fmt:v=>n(v,0),cls:'num'},{key:'h1_first',label:'H1 First',fmt:v=>n(v,0),cls:'num'},{key:'multi_tf',label:'Multi-TF',fmt:v=>n(v,0),cls:'num'}
  ]);
  renderTable($('validationOppTable'),p.opportunities||[],[
    {key:'start_time',label:'Start',fmt:v=>t(v)},{key:'side',label:'Side',fmt:v=>sideBadge(v)},{key:'first_tf',label:'First TF',fmt:v=>badge(v,'info')},{key:'timeframes',label:'TFs'},
    {key:'qualification_status',label:'Qualification',fmt:v=>badge(v||'QUALIFIED_ONCE','good')},{key:'outcome_status',label:'Outcome',fmt:v=>badge(v,kind(v))},
    {key:'signal_count',label:'Signals',fmt:v=>n(v,0),cls:'num'},{key:'any_major',label:'Major',fmt:v=>badge(v?'YES':'NO',v?'good':'bad')},{key:'major_signals',label:'Major Signals',fmt:v=>n(v,0),cls:'num'},
    {key:'first_persistent10',label:'Persistent10',fmt:v=>badge(v?'YES':'NO',v?'good':'bad')},{key:'first_mfe10_atr',label:'First MFE10 ATR',fmt:v=>n(v,2),cls:'num'},{key:'close_reason',label:'Journey Close'}
  ]);
  renderTable($('failureTable'),p.failures||[],[
    {key:'start_time',label:'Start',fmt:v=>t(v)},{key:'side',label:'Side',fmt:v=>sideBadge(v)},{key:'first_tf',label:'First TF'},{key:'timeframes',label:'TFs'},
    {key:'qualification_status',label:'Qualification',fmt:v=>badge(v||'QUALIFIED_ONCE','good')},{key:'outcome_status',label:'Outcome',fmt:v=>badge(v||'FAILED','bad')},
    {key:'signal_count',label:'Signals',fmt:v=>n(v,0),cls:'num'},{key:'false_signals',label:'False Signals',fmt:v=>n(v,0),cls:'num'},{key:'first_persistent10',label:'Persistent10',fmt:v=>badge(v?'YES':'NO',v?'good':'bad')},
    {key:'first_mfe10_atr',label:'First MFE10 ATR',fmt:v=>n(v,2),cls:'num'},{key:'members',label:'Signal Sequence'}
  ]);
}
function healthMessage(s){if(s==='CURRENT')return'Live source, ingestion and BEN computation are aligned. Current opportunity information can be read as synchronized.';if(s==='PROCESSING')return'New closed-bar source data exists and the BEN compute layer is catching up. Live opportunity state should be treated as temporarily behind.';if(s==='LAGGING')return'One or more required timeframe series is behind the source clock. The dashboard must not imply that live opportunity state is current.';if(s==='STALE')return'No sufficiently recent closed-bar source data is available. Current BEN signals should not be used.';return'One or more pipeline integrity checks failed. Review the diagnostics below before trusting live state.'}
async function loadHealth(){
  const p=await api('/api/health'),s=p.overall||'ERROR',l=p.live||{},i=p.ingest||{},c=p.compute||{},w=p.watcher||{},task=p.weekly_scheduler||{},wc=p.weekly_context_status||{};
  $('globalStatus').textContent=s;$('globalStatus').className=s==='CURRENT'?'positive':'negative';$('dataAsOf').textContent=t(l.live_data_as_of||l.expected_data_as_of);$('lastCompute').textContent=t(c.last_computed_at);
  const banner=$('alertBanner');banner.classList.toggle('hidden',s==='CURRENT');banner.className=`alert-banner ${s==='PROCESSING'?'processing':''} ${s==='CURRENT'?'current':''}`;banner.textContent=s==='CURRENT'?'':`${s} — ${healthMessage(s)}`;
  $('healthStatus').className=`status-band ${kind(s)}`;$('healthStatus').innerHTML=`<div><small>OVERALL STATUS</small><strong>${esc(s)}</strong></div><div><small>DATA AS OF</small><strong>${esc(t(l.live_data_as_of))}</strong></div><p>${esc(healthMessage(s))}</p>`;
  $('healthMetrics').innerHTML=[metric('Source Lag',`${n(l.source_lag_bars??0,0)} bars`,`${n(l.source_lag_minutes??0,0)} minutes`,l.source_lag_bars?'bad':'good'),metric('Watcher',w.running?'RUNNING':'STOPPED',w.running?`PID ${w.pid}`:'5-minute ingest unavailable',w.running?'good':'bad'),metric('Last Ingest',shortT(i.last_checked_at),`${i.last_inserted_bars??0} bars · ${i.last_inserted_events??0} BEN events`),metric('Last Compute',shortT(c.last_computed_at),c.status||'—',c.status==='OK'?'good':'bad')].join('');
  renderTable($('freshnessTable'),p.timeframes||[],[
    {key:'timeframe',label:'TF',fmt:v=>badge(v,'info')},{key:'bar_time',label:'Latest Bar'},{key:'bar_close_time',label:'Latest Closed'},{key:'expected_closed_bar_time',label:'Expected Closed'},
    {key:'lag_bars',label:'Lag Bars',fmt:v=>n(v,0),cls:'num'},{key:'lag_minutes',label:'Lag Min',fmt:v=>n(v,0),cls:'num'},{key:'status',label:'Status',fmt:v=>badge(v,kind(v))}
  ]);
  renderTable($('reproductionTable'),p.reproduction||[],[
    {key:'timeframe',label:'TF',fmt:v=>badge(v,'info')},{key:'expected',label:'Expected',fmt:v=>n(v,0),cls:'num'},{key:'reproduced',label:'Reproduced',fmt:v=>n(v,0),cls:'num'},{key:'status',label:'Audit',fmt:v=>badge(v,kind(v))}
  ]);
  $('watcherGrid').innerHTML=[detail('Watcher',badge(w.running?'RUNNING':'STOPPED',w.running?'good':'bad')),detail('PID',esc(w.pid??'—')),detail('Started',esc(t(w.start))),detail('Startup Launcher',badge(p.startup_ingest_present?'PRESENT':'MISSING',p.startup_ingest_present?'good':'bad')),detail('Last Ingest Status',badge(i.last_status||'—',kind(i.last_status))),detail('Last Error',esc(i.last_error||'None'))].join('');
  $('schedulerGrid').innerHTML=[detail('Task',esc('BEN Weekly Context · every 15 min')),detail('Task State',badge(task.state||'—',task.last_result===0?'good':'warn')),detail('Cycle Status',badge(wc.status||'—',kind(wc.status))),detail('Context Cutoff',esc(t(wc.master_after||wc.requested_cutoff))),detail('Last Run',esc(t(task.last_run))),detail('Next Run',esc(t(task.next_run)))].join('');
  $('integrityGrid').innerHTML=[detail('SQLite Integrity',badge(p.integrity==='ok'?'PASS':'FAIL',p.integrity==='ok'?'good':'bad')),detail('Foreign Keys',badge((p.foreign_key_errors||[]).length?'FAIL':'PASS',(p.foreign_key_errors||[]).length?'bad':'good')),detail('Market Bars',esc(n((p.counts||{}).market_bars,0))),detail('BEN Events',esc(n((p.counts||{}).ben_events,0))),detail('Rule Evaluations',esc(n((p.counts||{}).rule_evaluations,0))),detail('Journey Rows',esc(n((p.counts||{}).historical_journey,0)))].join('');
  renderTable($('ingestRunsTable'),p.latest_runs||[],[
    {key:'checked_at',label:'Checked',fmt:v=>t(v)},{key:'inserted_bars',label:'Bars',fmt:v=>n(v,0),cls:'num'},{key:'inserted_events',label:'BEN Events',fmt:v=>n(v,0),cls:'num'},{key:'status',label:'Status',fmt:v=>badge(v,kind(v))},{key:'message',label:'Message'}
  ]);
}
async function safe(name,fn){try{await fn()}catch(e){console.error(name,e);const b=$('alertBanner');b.className='alert-banner';b.textContent=`ERROR — ${name}: ${e.message}`}}
async function boot(){
  document.querySelectorAll('#tabs button').forEach(b=>b.addEventListener('click',()=>showTab(b.dataset.tab)));
  const h=location.hash.replace('#','');if(['overview','journey','weekly','validation','health'].includes(h))showTab(h);
  $('overviewRefresh').onclick=()=>safe('overview',loadOverview);$('journeyLoad').onclick=()=>safe('journey',loadJourney);$('weeklyLoad').onclick=()=>safe('weekly',loadWeekly);$('validationRefresh').onclick=()=>safe('validation',loadValidation);$('healthRefresh').onclick=()=>safe('health',loadHealth);
  await safe('meta',loadMeta);await Promise.all([safe('health',loadHealth),safe('overview',loadOverview),safe('weekly',loadWeekly),safe('validation',loadValidation)]);await safe('journey',loadJourney);
  setInterval(()=>{safe('health',loadHealth);safe('overview',loadOverview)},60000);
}
document.addEventListener('DOMContentLoaded',boot);
