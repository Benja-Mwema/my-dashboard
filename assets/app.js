const $ = id => document.getElementById(id);
const state = { meta:null, latestDate:'', selectedRule:null };
const LIVE_API_HOSTS = new Set(['127.0.0.1','localhost']);
const USE_STATIC_SNAPSHOT = !LIVE_API_HOSTS.has(location.hostname);
let snapshotPromise = null;

async function dashboardSnapshot(){
  if(!snapshotPromise){
    snapshotPromise = fetch('/data/dashboard_snapshot.json',{cache:'no-store'}).then(async r=>{
      if(!r.ok) throw new Error(`Static snapshot unavailable: HTTP ${r.status}`);
      return r.json();
    });
  }
  return snapshotPromise;
}

function staticApiRoute(s,path){
  const u=new URL(path,location.origin), q=u.searchParams, route=u.pathname;
  const cutoff=q.get('cutoff_date')||q.get('week')||s.default_week;
  if(route==='/api/meta') return s.meta||{};
  if(route==='/api/system-health') return s.system_health||{};
  if(route==='/api/research-rc1') return s.research_rc1_latest||{};
  if(route==='/api/research-regimes') return (s.research_regimes||[]).slice(0,Number(q.get('limit')||500));
  if(route==='/api/rc1-day') return (s.rc1_day_by_date||{})[q.get('date')||'']||{};
  if(route==='/api/weekly-analytics') return (s.weekly_analytics_by_week||{})[cutoff]||{};
  if(route==='/api/weekly-report-map') return (s.weekly_report_map_by_week||{})[cutoff]||{};
  if(route==='/api/weekly'){
    const rows=s.weekly_all||[];
    if(q.get('cutoff_date')) return rows.filter(r=>String(r.cutoff_date)===String(q.get('cutoff_date')));
    return rows.slice(0,Number(q.get('limit')||52));
  }
  throw new Error(`Static route unavailable: ${route}`);
}

async function api(path){
  if(USE_STATIC_SNAPSHOT) return staticApiRoute(await dashboardSnapshot(),path);
  const r=await fetch(path,{cache:'no-store'});
  if(!r.ok){ const e=await r.json().catch(()=>({})); throw new Error(e.message||`HTTP ${r.status}`); }
  return r.json();
}
function n(v,d=2){ if(v===null||v===undefined||v==='') return '—'; const x=Number(v); return Number.isFinite(x)?x.toLocaleString(undefined,{maximumFractionDigits:d}):String(v); }
function pct(v){ return v===null||v===undefined?'—':`${n(v,1)}%`; }
function t(v){ if(!v) return '—'; return String(v).replace('T',' ').replace('+03:00',' EAT').replace('.000',''); }
function shortT(v){ if(!v) return '—'; const s=t(v); return s.length>16?s.slice(5,16):s; }
function esc(v){ return String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function sideKind(v){ return v==='BUY'?'buy':v==='SELL'?'sell':'info'; }
function stateKind(v){ const x=String(v||''); if(x==='QUALIFIED'||x==='PASS'||x==='CLOSED_WIN') return 'good'; if(x==='CONTEXT_BLOCKED'||x==='FAILED'||x==='CLOSED_LOSS'||x==='EXPIRED_LOSS') return 'bad'; if(x==='WAIT'||x==='WATCHING') return 'wait'; return 'info'; }
function badge(v,kind){ return `<span class="badge ${kind||sideKind(v)}">${esc(v||'—')}</span>`; }
function metric(label,value,sub='',kind='info'){ return `<div class="metric ${kind}"><small>${esc(label)}</small><strong>${esc(value)}</strong>${sub?`<span>${esc(sub)}</span>`:''}</div>`; }
function detail(label,value){ return `<div class="detail"><small>${esc(label)}</small><strong>${value??'—'}</strong></div>`; }
function showTab(name){ document.querySelectorAll('.tab-page').forEach(x=>x.classList.toggle('active',x.id===`tab-${name}`)); document.querySelectorAll('#tabs button').forEach(x=>x.classList.toggle('active',x.dataset.tab===name)); }

function renderTable(el,rows,cols,{click}={}){
  if(!el) return;
  if(!rows?.length){ el.innerHTML='<tbody><tr><td class="muted">No records</td></tr></tbody>'; return; }
  const head=cols.map(c=>`<th>${esc(c.label)}</th>`).join('');
  const body=rows.map((r,i)=>`<tr class="${click?'clickable':''}" data-row="${i}">`+cols.map(c=>{
    const val=c.fmt?c.fmt(r[c.key],r):esc(r[c.key]); return `<td class="${c.className||''}">${val}</td>`;
  }).join('')+'</tr>').join('');
  el.innerHTML=`<thead><tr>${head}</tr></thead><tbody>${body}</tbody>`;
  if(click) el.querySelectorAll('tbody tr').forEach(tr=>tr.addEventListener('click',()=>click(rows[Number(tr.dataset.row)])));
}

function regimeMeaning(regime,phase=''){
  if(regime==='SWEEP_REJECT_BALANCE') return 'Liquidity sweeps and rejection dominate. RC1 waits for validated edge or breakdown formations; direction is not assumed.';
  if(regime==='ACCEPTANCE_EXPANSION') return 'A structural break has been accepted. Only the selective RC1 expansion rules are allowed; there is no blanket continuation permission.';
  if(regime==='TRANSITION') return phase==='BALANCE_FORMING'?'Old directional authority has weakened and balance is forming. Only the validated transition break can trade.':'The previous regime has lost authority. RC1 waits for the validated transition setup or a new structural regime.';
  if(regime==='TREND_CONTINUATION') return 'Inherited trend structure remains intact, but RC1 has no independently validated >90% execution rule here. Execution state is NO_SIGNAL.';
  return 'No RC1 regime is available for this date.';
}
async function loadMeta(){
  state.meta=await api('/api/meta');
  const weeks=state.meta.weeks||[];
  const weekOptions=weeks.map(w=>`<option value="${esc(w.cutoff_date)}">${esc(`${w.forecast_week_start} → ${w.forecast_week_end}`)}</option>`).join('');
  $('overviewWeek').innerHTML=weekOptions; $('weeklyWeek').innerHTML=weekOptions;
  const dates=[...new Set([...(state.meta.forecast_dates||[]),...(state.meta.journey_dates||[])])].sort().reverse();
  state.latestDate=dates[0]||state.meta.latest_daily_date||'';
  const dateOptions=dates.map(d=>`<option value="${esc(d)}">${esc(d)}</option>`).join('');
  $('overviewDate').innerHTML=dateOptions; $('journeyDate').innerHTML=dateOptions;
  if(state.latestDate){ $('overviewDate').value=state.latestDate; $('journeyDate').value=state.latestDate; }
  const latest=state.latestDate;
  const wk=weeks.find(w=>latest && String(w.forecast_week_start)<=latest && String(w.forecast_week_end)>=latest) || weeks[0];
  if(wk){ $('overviewWeek').value=wk.cutoff_date; $('weeklyWeek').value=wk.cutoff_date; }
}

async function loadHealth(){
  const h=await api('/api/system-health');
  const f=h.source_freshness||{}, d=h.database||{}, s=h.scheduler||{}, g=h.safety_guard||{}, p=h.processing||{};
  const stale=f.status==='SOURCE_STALE', lag=Number(p.lag_minutes||0), processing=!stale&&lag>0;
  const banner=$('staleBanner'); banner.classList.toggle('hidden',!(stale||processing)); banner.classList.toggle('processing',processing);
  banner.textContent=stale?'SOURCE STALE — DO NOT USE CURRENT SIGNALS':`ENGINE PROCESSING — JOURNEY LAGS SOURCE BY ${n(lag,0)} MIN`;
  $('sourceStatus').textContent=f.status||'—'; $('sourceStatus').className=stale?'negative':'positive';
  $('dataAsOf').textContent=t(f.actual_latest_m15_close); $('dbAsOf').textContent=t(d.phase3_as_of||d.db_m15_as_of);
  $('schedulerStatus').textContent=s.display_status||(s.status==='OK'?`${s.State} / ${s.LastTaskResult}`:'UNAVAILABLE');
  $('healthCards').innerHTML=[metric('Source',f.status||'—',f.reason||'',stale?'bad':'good'),metric('Processing',p.status||'—',lag?`${n(lag,0)} min lag`:'Aligned',processing?'warn':'good'),metric('Expected M15',shortT(f.expected_latest_completed_m15_close),`Wall-clock lag ${n(f.wallclock_lag_minutes,0)} min`),metric('DB M15',shortT(d.db_m15_as_of),'Closed bars ingested'),metric('Schema',g.schema_version??'—',g.dashboard_views_valid?'Views valid':'Views invalid',g.dashboard_views_valid?'good':'bad'),metric('Executions',d.execution_count??0,`${d.resolved_outcome_count??0} resolved`)].join('');
  $('checkpointGrid').innerHTML=[detail('Phase 3',esc(t(d.phase3_as_of))),detail('Phase 4',esc(t(d.phase4_as_of))),detail('Phase 5',esc(t(d.phase5_as_of))),detail('Phase 6 Observation',esc(t(d.phase6_observation_as_of))),detail('Phase 6 Lineage',esc(t(d.phase6_lineage_as_of))),detail('Failed Runs',esc(d.failed_engine_run_count??0))].join('');
  $('schedulerGrid').innerHTML=[detail('State',esc(s.State||s.status||'—')),detail('Enabled',esc(s.Enabled===true?'YES':s.Enabled===false?'NO':'—')),detail('Last Run',esc(t(s.LastRunTime))),detail('Last Result',esc(s.LastTaskResult??'—')),detail('Next Run',esc(t(s.NextRunTime))),detail('Missed Runs',esc(s.MissedRuns??'—'))].join('');
  $('schedulerLog').textContent=(h.scheduler_log_tail||[]).join('\n');
}
function ruleCols(){ return [
  {key:'grade',label:'Grade',fmt:v=>badge(v,v==='A'?'good':'wait')},
  {key:'side',label:'Side',fmt:v=>badge(v)},
  {key:'rule_id',label:'Rule'},
  {key:'trigger_label',label:'Trigger'},
  {key:'status',label:'State',fmt:v=>badge(v,stateKind(v))},
  {key:'conditions_passed',label:'Stable Conditions',fmt:(v,r)=>`${v}/${r.conditions_total}`,className:'num'},
  {key:'raw_trigger_count',label:'Raw',fmt:v=>n(v,0),className:'num'},
  {key:'qualified_count',label:'Qualified',fmt:v=>n(v,0),className:'num'},
  {key:'validation_rate',label:'Val WR',fmt:v=>pct(100*v),className:'num'},
  {key:'risk',label:'Risk'},
  {key:'what_to_wait_for',label:'Waiting For'}
]; }
function shadowCols(){ return [
  {key:'signal_time',label:'Signal',fmt:v=>shortT(v)}, {key:'grade',label:'Grade',fmt:v=>badge(v,v==='A'?'good':'wait')},
  {key:'rule_id',label:'Rule'}, {key:'side',label:'Side',fmt:v=>badge(v)},
  {key:'entry_price',label:'Entry',fmt:v=>n(v,2),className:'num'}, {key:'tp_price',label:'TP',fmt:v=>n(v,2),className:'num'},
  {key:'sl_price',label:'SL',fmt:v=>n(v,2),className:'num'}, {key:'status',label:'Status',fmt:v=>badge(v,stateKind(v))},
  {key:'result',label:'Result',fmt:v=>v?badge(v,v==='WIN'?'good':'bad'):'—'}
]; }

async function loadOverview(){
  const date=$('overviewDate').value, week=$('overviewWeek').value;
  const [day,research,weeklyRows]=await Promise.all([
    api(`/api/rc1-day?date=${encodeURIComponent(date)}`), api('/api/research-rc1'),
    api(`/api/weekly?cutoff_date=${encodeURIComponent(week)}`)
  ]);
  const r=day.regime||{}, s=day.summary||{}, m=day.market||{}, l=day.levels||{}, f=research.forward||{}, meta=research.meta||{};
  $('overviewState').className=`status-band ${stateKind(s.execution_state)}`;
  $('overviewState').innerHTML=`<div><small>RC1 EXECUTION STATE</small><strong>${esc(s.execution_state||'—')}</strong></div><div><small>MASTER REGIME</small><strong>${esc(r.regime||'—')}</strong></div><p>${esc(s.explanation||'')}</p>`;
  $('overviewHero').innerHTML=[metric('Master Regime',r.regime||'—',r.phase||'Four-regime authority'),metric('Execution',s.execution_state||'—',s.qualified_rule_count?`${s.qualified_rule_count} qualified`:'No trade authorized',s.execution_state==='QUALIFIED'?'good':'warn'),metric('Active Rules',s.active_rule_count??0,'Current regime only'),metric('Raw Triggers',s.raw_trigger_count??0,'Raw event ≠ trade',s.raw_trigger_count?'warn':'info'),metric('Qualified',s.qualified_rule_count??0,'Complete stable envelope',s.qualified_rule_count?'good':'info'),metric('Market',m.last==null?'Pre-session':n(m.last,2),m.as_of?`as of ${shortT(m.as_of)}`:`${m.bars??0} bars`)].join('');
  $('overviewExplanation').innerHTML=`<p>${esc(regimeMeaning(r.regime,r.phase))}</p><p><strong>Decision:</strong> ${esc(s.explanation||'')}</p><p><strong>Structural event:</strong> ${esc(r.last_struct_type||'—')} ${esc(r.last_struct_dir||'')} · age ${n(r.days_since_struct,0)} day(s).</p>`;
  $('overviewLevels').innerHTML=[detail('R2',esc(n(l.r2,2))),detail('R1',esc(n(l.r1,2))),detail('Pivot',esc(n(l.pivot,2))),detail('S1',esc(n(l.s1,2))),detail('S2',esc(n(l.s2,2))),detail('Previous High / Low',esc(`${n(l.previous_high,2)} / ${n(l.previous_low,2)}`))].join('');
  renderTable($('overviewRulesTable'),day.active_rules||[],ruleCols());
  const w=(weeklyRows||[])[0]||{};
  $('overviewWeeklyGrid').innerHTML=[detail('Weekly Bias',badge(w.final_weekly_side||'—')),detail('Structural State',esc(w.structural_state||'—')),detail('Resistance Zone',esc(`${n(w.resistance_lower,2)} – ${n(w.resistance_upper,2)}`)),detail('Resistance Control',esc(n(w.resistance_control,2))),detail('Support Zone',esc(`${n(w.support_lower,2)} – ${n(w.support_upper,2)}`)),detail('Support Control',esc(n(w.support_control,2)))].join('');
  $('overviewForward').innerHTML=[detail('Forward Start',esc(meta.forward_start||'—')),detail('Target',esc(f.target??100)),detail('Resolved',esc(f.resolved??0)),detail('Wins / Losses',esc(`${f.wins??0} / ${f.losses??0}`)),detail('Forward WR',esc(f.win_rate==null?'Pending':pct(100*f.win_rate))),detail('Rules Changed',esc(f.rules_changed??0))].join('');
  renderTable($('overviewShadowTable'),(research.shadow_signals||[]).slice(0,20),shadowCols());
}

function scenarioCards(map){
  const rows=[map.primary,map.direct_continuation,map.failure_route].filter(Boolean);
  return rows.map((x,i)=>`<div class="scenario-card ${i===0?'primary-scenario':''}"><strong>${esc(x.name||'SCENARIO')}</strong><span>${(x.steps||[]).map(esc).join(' → ')}</span></div>`).join('')||'<span class="muted">No scenario map</span>';
}

async function loadWeekly(){
  const week=$('weeklyWeek').value;
  const [rows,all,analytics,report]=await Promise.all([
    api(`/api/weekly?cutoff_date=${encodeURIComponent(week)}`), api('/api/weekly?limit=52'),
    api(`/api/weekly-analytics?cutoff_date=${encodeURIComponent(week)}`), api(`/api/weekly-report-map?cutoff_date=${encodeURIComponent(week)}`)
  ]);
  const w=(rows||[])[0]||{}, fc=analytics.forecast||{}, acc=analytics.accuracy||{};
  const rc1day=w.forecast_week_start?await api(`/api/rc1-day?date=${encodeURIComponent(w.forecast_week_start)}`):{};
  const rr=rc1day.regime||{};
  $('weeklyHero').innerHTML=[metric('Weekly Bias',w.final_weekly_side||'—',`${w.forecast_week_start||'—'} → ${w.forecast_week_end||'—'}`,w.final_weekly_side==='SELL'?'bad':'good'),metric('Upper Zone',`${n(w.resistance_lower,2)} – ${n(w.resistance_upper,2)}`,'Context only'),metric('Lower Zone',`${n(w.support_lower,2)} – ${n(w.support_upper,2)}`,'Context only'),metric('Actual High',n(w.actual_high,2),shortT(w.actual_high_time)),metric('Actual Low',n(w.actual_low,2),shortT(w.actual_low_time))].join('');
  $('weeklyScenarioMap').innerHTML=scenarioCards(report.scenario_map||{});
  const levels=(report.level_roles||[]).slice().sort((a,b)=>(a.distance_from_cutoff??999999)-(b.distance_from_cutoff??999999)).slice(0,14);
  renderTable($('weeklyLevelTable'),levels,[{key:'center',label:'Level',fmt:v=>n(v,2),className:'num'},{key:'report_role',label:'Role',fmt:v=>badge(v,'info')},{key:'original_role',label:'Market Role'},{key:'lower',label:'Lower',fmt:v=>n(v,2),className:'num'},{key:'upper',label:'Upper',fmt:v=>n(v,2),className:'num'}]);
  $('weeklyAccuracyGrid').innerHTML=[detail('Completed',esc(analytics.completed?'YES':'NO')),detail('Expected Extreme First',esc(acc.expected_extreme_first||'—')),detail('Actual Extreme First',esc(acc.actual_extreme_first||'—')),detail('Sequence Match',esc(acc.sequence_match===true?'YES':acc.sequence_match===false?'NO':'Pending')),detail('Upper-Zone Miss',esc(`${n(acc.upper_zone_miss_points,2)} pts · ${n(acc.upper_zone_miss_h4_atr,2)} H4 ATR`)),detail('Lower-Zone Miss',esc(`${n(acc.lower_zone_miss_points,2)} pts · ${n(acc.lower_zone_miss_h4_atr,2)} H4 ATR`))].join('');
  $('weeklyRc1Grid').innerHTML=[detail('Master Regime',badge(rr.regime||'—','info')),detail('Phase',esc(rr.phase||'—')),detail('Last Structural Event',esc(`${rr.last_struct_type||'—'} ${rr.last_struct_dir||''}`)),detail('Structural Age',esc(`${n(rr.days_since_struct,0)} day(s)`)),detail('D1 Eff10',esc(n(rr.d1_eff10,3))),detail('Execution Authority',esc((rc1day.summary||{}).execution_state||'WAIT'))].join('');
  renderTable($('weeklyTable'),all||[],[
    {key:'cutoff_date',label:'Freeze'}, {key:'forecast_week_start',label:'Week Start'}, {key:'forecast_week_end',label:'Week End'},
    {key:'final_weekly_side',label:'Bias',fmt:v=>badge(v)}, {key:'structural_state',label:'State'},
    {key:'resistance_control',label:'Resistance',fmt:v=>n(v,2),className:'num'}, {key:'support_control',label:'Support',fmt:v=>n(v,2),className:'num'},
    {key:'actual_high',label:'Actual High',fmt:v=>n(v,2),className:'num'}, {key:'actual_low',label:'Actual Low',fmt:v=>n(v,2),className:'num'},
    {key:'actual_close',label:'Close',fmt:v=>n(v,2),className:'num'}
  ]);
}

function renderRuleInspector(rule){
  if(!rule){ $('ruleInspectorTitle').textContent='Rule Inspector'; $('ruleInspectorMeta').textContent=''; $('ruleInspectorText').innerHTML='<span class="muted">Select a rule.</span>'; renderTable($('ruleConditionTable'),[],[]); return; }
  state.selectedRule=rule;
  $('ruleInspectorTitle').textContent=rule.rule_id;
  $('ruleInspectorMeta').textContent=`${rule.grade} · ${rule.side} · ${rule.config} · risk ${rule.risk}`;
  $('ruleInspectorText').innerHTML=`<p>${esc(rule.description||'')}</p><p><strong>Trigger:</strong> ${esc(rule.trigger_label||rule.trigger)}</p><p><strong>State:</strong> ${badge(rule.status,stateKind(rule.status))}</p><p><strong>What RC1 is waiting for:</strong> ${esc(rule.what_to_wait_for||'—')}</p>`;
  renderTable($('ruleConditionTable'),rule.conditions||[],[
    {key:'feature',label:'Feature'}, {key:'operator',label:'Gate'},
    {key:'stable_threshold',label:'Stable Threshold',fmt:v=>n(v,4),className:'num'},
    {key:'actual',label:'Actual',fmt:v=>n(v,4),className:'num'},
    {key:'passed',label:'Result',fmt:v=>badge(v?'PASS':'FAIL',v?'good':'bad')}
  ]);
}
async function loadJourney(){
  const date=$('journeyDate').value;
  const day=await api(`/api/rc1-day?date=${encodeURIComponent(date)}`);
  const r=day.regime||{}, s=day.summary||{}, m=day.market||{}, l=day.levels||{};
  $('journeyState').className=`status-band ${stateKind(s.execution_state)}`;
  $('journeyState').innerHTML=`<div><small>EXECUTION</small><strong>${esc(s.execution_state||'—')}</strong></div><div><small>REGIME</small><strong>${esc(r.regime||'—')}</strong></div><p>${esc(s.explanation||'')}</p>`;
  $('journeyHero').innerHTML=[metric('Master Regime',r.regime||'—',r.phase||'Frozen at day start'),metric('Execution',s.execution_state||'—',s.qualified_rule_count?`${s.qualified_rule_count} qualified`:'No trade authorized',s.execution_state==='QUALIFIED'?'good':'warn'),metric('Raw Triggers',s.raw_trigger_count??0,'Raw event ≠ trade',s.raw_trigger_count?'warn':'info'),metric('Context Blocks',s.blocked_rule_count??0,'Triggered but envelope failed',s.blocked_rule_count?'bad':'info'),metric('Qualified',s.qualified_rule_count??0,'Full RC1 permission',s.qualified_rule_count?'good':'info'),metric('Day Range',m.range==null?'Pre-session':n(m.range,2),`${m.bars??0} M15 bars`)].join('');
  $('journeyExplanation').innerHTML=`<p>${esc(regimeMeaning(r.regime,r.phase))}</p><p><strong>Current decision:</strong> ${esc(s.explanation||'')}</p><p><strong>Last structure:</strong> ${esc(r.last_struct_type||'—')} ${esc(r.last_struct_dir||'')} · age ${n(r.days_since_struct,0)} · days since acceptance ${n(r.days_since_accept,0)}.</p>`;
  $('journeyMarketGrid').innerHTML=[detail('R2',esc(n(l.r2,2))),detail('R1',esc(n(l.r1,2))),detail('Pivot',esc(n(l.pivot,2))),detail('S1',esc(n(l.s1,2))),detail('S2',esc(n(l.s2,2))),detail('Previous High / Low',esc(`${n(l.previous_high,2)} / ${n(l.previous_low,2)}`)),detail('Actual Open / Last',esc(`${n(m.open,2)} / ${n(m.last,2)}`)),detail('Actual High / Low',esc(`${n(m.high,2)} / ${n(m.low,2)}`)),detail('High Time',esc(shortT(m.high_time))),detail('Low Time',esc(shortT(m.low_time)))].join('');
  const rules=(day.active_rules||[]).slice().sort((a,b)=>({QUALIFIED:0,CONTEXT_BLOCKED:1,WATCHING:2}[a.status]??3)-({QUALIFIED:0,CONTEXT_BLOCKED:1,WATCHING:2}[b.status]??3));
  renderTable($('journeyRulesTable'),rules,ruleCols(),{click:renderRuleInspector});
  renderRuleInspector(rules[0]||null);
  renderTable($('journeyTimelineTable'),day.timeline||[],[
    {key:'time',label:'Time',fmt:v=>shortT(v)}, {key:'price',label:'Price',fmt:v=>n(v,2),className:'num'},
    {key:'grade',label:'Grade',fmt:v=>badge(v,v==='A'?'good':'wait')}, {key:'side',label:'Side',fmt:v=>badge(v)},
    {key:'rule_id',label:'Rule'}, {key:'trigger',label:'Raw Event'},
    {key:'state',label:'RC1 State',fmt:v=>badge(v,stateKind(v))},
    {key:'conditions_passed',label:'Stable Conditions',fmt:(v,row)=>`${v}/${row.conditions_total}`,className:'num'},
    {key:'failed_conditions',label:'Failed Conditions'}
  ]);
}
async function loadResearch(){
  const [p,history,day]=await Promise.all([
    api('/api/research-rc1'), api('/api/research-regimes?limit=500'),
    api(`/api/rc1-day?date=${encodeURIComponent(state.latestDate)}`)
  ]);
  const m=p.meta||{}, f=p.forward||{}, bt=p.backtest||[], rules=day.all_rules||[], sh=p.shadow_signals||[];
  const all=bt.find(x=>x.period==='ALL_2020_2026')||{}, val=bt.find(x=>x.period==='VALIDATION_2024_2025')||{};
  $('researchHero').innerHTML=[metric('Research Version',m.research_version||'—',m.research_status||'—','good'),metric('Validated Rules',m.rule_count||rules.length,'8 Grade A · 1 Grade B'),metric('2020–2026',`${n(all.trades,0)} trades`,`${pct(100*(all.win_rate||0))} · ${n(all.net_r,2)}R`,'good'),metric('Independent Validation',`${pct(100*(val.win_rate||0))}`,`${n(val.trades,0)} trades · 2024–2025`,'good'),metric('Forward Sample',`${f.resolved??0}/${f.target??100}`,`${f.wins??0}W / ${f.losses??0}L`,'info'),metric('Parity',m.parity_status||'—',`${m.parity_trades||'—'} trades · ${m.parity_regime_days||'—'} regimes`,m.parity_status==='PASS'?'good':'bad')].join('');
  $('researchExplanation').innerHTML='<p><strong>Execution authority:</strong> the four-regime RC1 model plus the nine locked validated rules.</p><p><strong>Not execution authority:</strong> A–D/T2, MR1–MR4, legacy daily direction, weekly direction and the old optimizer.</p><p><strong>TREND_CONTINUATION:</strong> NO_SIGNAL until an independently validated >90% rule exists.</p><p><strong>Forward discipline:</strong> thresholds remain unchanged through the agreed 100+ trade milestone.</p>';
  $('researchForward').innerHTML=[detail('Forward Start',esc(m.forward_start||'—')),detail('Execution Mode',badge(m.execution_mode||'SHADOW','wait')),detail('Target Trades',esc(f.target??100)),detail('Resolved',esc(f.resolved??0)),detail('Wins / Losses',esc(`${f.wins??0} / ${f.losses??0}`)),detail('Rules Changed',esc(f.rules_changed??0)),detail('Grade A Risk',esc(m.grade_a_risk||'1.0x')),detail('Grade B Risk',esc(m.grade_b_risk||'0.5x'))].join('');
  renderTable($('researchRuleTable'),rules,[{key:'grade',label:'Grade',fmt:v=>badge(v,v==='A'?'good':'wait')},{key:'risk',label:'Risk'},{key:'rule_id',label:'Rule'},{key:'required_regime',label:'Regime'},{key:'side',label:'Side',fmt:v=>badge(v)},{key:'trigger_label',label:'Trigger'},{key:'validation_rate',label:'Validation WR',fmt:v=>pct(100*v),className:'num'},{key:'validation_support',label:'N',fmt:v=>n(v,0),className:'num'},{key:'config',label:'TP / SL / Hold'},{key:'stability_margin',label:'Envelope',fmt:v=>`±${pct(100*v)}`,className:'num'},{key:'description',label:'Purpose'}]);
  renderTable($('researchBacktestTable'),bt,[{key:'period',label:'Period'},{key:'trades',label:'Trades',fmt:v=>n(v,0),className:'num'},{key:'wins',label:'Wins',fmt:v=>n(v,0),className:'num'},{key:'win_rate',label:'WR',fmt:v=>pct(100*v),className:'num'},{key:'trades_per_week',label:'Trades/Wk',fmt:v=>n(v,2),className:'num'},{key:'net_r',label:'Net R',fmt:v=>n(v,2),className:'num'}]);
  let years={}; try{ years=JSON.parse(m.year_stats_json||'{}'); }catch(_e){}
  const yearRows=Object.entries(years).map(([year,v])=>({year,trades:v[0],wins:v[1],win_rate:v[2]}));
  renderTable($('researchYearTable'),yearRows,[{key:'year',label:'Year'},{key:'trades',label:'Trades',fmt:v=>n(v,0),className:'num'},{key:'wins',label:'Wins',fmt:v=>n(v,0),className:'num'},{key:'win_rate',label:'WR',fmt:v=>pct(100*v),className:'num'}]);
  renderTable($('researchShadowTable'),sh,shadowCols());
  renderTable($('researchRegimeTable'),history,[{key:'trading_date',label:'Date'},{key:'regime',label:'Regime',fmt:v=>badge(v,'info')},{key:'phase',label:'Phase'},{key:'last_struct_type',label:'Last Event'},{key:'last_struct_dir',label:'Direction'},{key:'days_since_struct',label:'Age',fmt:v=>n(v,0),className:'num'},{key:'d1_eff10',label:'D1 Eff10',fmt:v=>n(v,3),className:'num'},{key:'d1_rsi14',label:'D1 RSI',fmt:v=>n(v,1),className:'num'}]);
}

async function safe(name,fn){
  try{ await fn(); }
  catch(err){ console.error(name,err); if(name==='health'){ $('sourceStatus').textContent='ERROR'; $('sourceStatus').className='negative'; } }
}

async function boot(){
  document.querySelectorAll('#tabs button').forEach(b=>b.addEventListener('click',()=>showTab(b.dataset.tab)));
  $('overviewLoad').addEventListener('click',()=>safe('overview',loadOverview));
  $('weeklyLoad').addEventListener('click',()=>safe('weekly',loadWeekly));
  $('journeyLoad').addEventListener('click',()=>safe('journey',loadJourney));
  $('researchLoad').addEventListener('click',()=>safe('research',loadResearch));
  $('healthLoad').addEventListener('click',()=>safe('health',loadHealth));
  $('overviewDate').addEventListener('change',()=>{ $('journeyDate').value=$('overviewDate').value; });
  $('journeyDate').addEventListener('change',()=>{ if([...$('overviewDate').options].some(o=>o.value===$('journeyDate').value)) $('overviewDate').value=$('journeyDate').value; });
  $('overviewWeek').addEventListener('change',()=>{ $('weeklyWeek').value=$('overviewWeek').value; });
  $('weeklyWeek').addEventListener('change',()=>{ $('overviewWeek').value=$('weeklyWeek').value; });
  await safe('meta',loadMeta);
  await Promise.all([safe('health',loadHealth),safe('overview',loadOverview),safe('weekly',loadWeekly),safe('research',loadResearch)]);
  await safe('journey',loadJourney);
  setInterval(()=>{ safe('health',loadHealth); safe('overview',loadOverview); },60000);
}

document.addEventListener('DOMContentLoaded',boot);
