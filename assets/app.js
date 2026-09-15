const $ = (id) => document.getElementById(id);
const state = { meta:null, overview:null, health:null, weekly:[], outcomes:[] };

const LIVE_API_HOSTS = new Set(['127.0.0.1','localhost']);
const USE_STATIC_SNAPSHOT = !LIVE_API_HOSTS.has(location.hostname);
let snapshotPromise = null;

async function dashboardSnapshot(){
  if(!snapshotPromise){
    snapshotPromise = fetch('/data/dashboard_snapshot.json',{cache:'no-store'}).then(async r=>{
      if(!r.ok) throw new Error(`Static dashboard snapshot unavailable: HTTP ${r.status}`);
      return r.json();
    });
  }
  return snapshotPromise;
}
function staticApiRoute(snapshot,path){
  const u = new URL(path,location.origin), q=u.searchParams, route=u.pathname;
  const view=(q.get('view')||'current').toLowerCase(), cutoff=q.get('cutoff_date')||q.get('week')||snapshot.default_week;
  if(route==='/api/meta') return snapshot.meta||{};
  if(route==='/api/system-health') return snapshot.system_health||{};
  if(route==='/api/overview') return (snapshot.overview_by_week||{})[cutoff]||{};
  if(route==='/api/week-analysis') return (snapshot.week_analysis_by_week||{})[cutoff]||{};
  if(route==='/api/engine-entries') return (((snapshot.engine_entries_by_week||{})[view]||{})[cutoff])||[];
  if(route==='/api/blocked-setups') return ((snapshot.blocked_by_week||{})[cutoff])||[];
  if(route==='/api/analytics-summary') return snapshot.analytics_summary||{};
  if(route==='/api/weekly-analytics') return ((snapshot.weekly_analytics_by_week||{})[cutoff])||{};
  if(route==='/api/weekly-report-map') return ((snapshot.weekly_report_map_by_week||{})[cutoff])||{};
  if(route==='/api/weekly'){
    const data=snapshot.weekly_all||[];
    if(q.get('cutoff_date')) return data.filter(r=>String(r.cutoff_date)===String(q.get('cutoff_date')));
    return data.slice(0,Number(q.get('limit')||52));
  }
  if(route==='/api/daily-forecast') return (snapshot.daily_forecast_by_date||{})[q.get('date')||'']||{};
  if(route==='/api/research-rc1'){ const d=q.get('date')||''; return d?((snapshot.research_rc1_by_date||{})[d]||{}):(snapshot.research_rc1_latest||{}); }
  if(route==='/api/research-regimes') return (snapshot.research_regimes||[]).slice(0,Number(q.get('limit')||120));
  if(route==='/api/journey'){
    let data=((((snapshot.journey_by_date||{})[view]||{})[q.get('date')||''])||[]).slice();
    const grade=(q.get('grade')||'').toUpperCase();
    if(grade) data=data.filter(r=>String(r.grade||'').toUpperCase()===grade);
    return data.slice(0,Number(q.get('limit')||2000));
  }
  if(route==='/api/outcomes') return ((snapshot.outcomes||{})[view])||[];
  if(route==='/api/optimizer') return ((snapshot.optimizer||{})[view])||{};
  if(route==='/api/forensics'){
    const id=q.get('evaluation_id')||'';
    const store=((snapshot.forensics||{})[view])||{};
    if(id) return ((store.by_id||{})[id])||store.latest||{};
    return store.latest||{};
  }
  throw new Error(`Static snapshot route not available: ${route}`);
}
async function api(path){
  if(USE_STATIC_SNAPSHOT) return staticApiRoute(await dashboardSnapshot(),path);
  const r = await fetch(path,{cache:'no-store'});
  if(!r.ok){ const e=await r.json().catch(()=>({})); throw new Error(e.message||`HTTP ${r.status}`); }
  return r.json();
}
function n(v,d=2){ if(v===null||v===undefined||v==='') return 'â€”'; const x=Number(v); return Number.isFinite(x)?x.toLocaleString(undefined,{maximumFractionDigits:d}):String(v); }
function t(v){ if(!v) return 'â€”'; return String(v).replace('T',' ').replace('+03:00',' EAT').replace('.000',''); }
function shortT(v){ if(!v) return 'â€”'; const s=t(v); return s.length>16?s.slice(5,16):s; }
function esc(v){ return String(v??'â€”').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function clsSide(v){ return v==='BUY'?'buy':v==='SELL'?'sell':v==='WAIT'?'wait':'info'; }
function badge(v,kind){ return `<span class="badge ${kind||clsSide(v)}">${esc(v)}</span>`; }
function metric(label,value,sub='',kind=''){ return `<div class="metric ${kind}"><small>${esc(label)}</small><strong>${esc(value)}</strong>${sub?`<span>${esc(sub)}</span>`:''}</div>`; }
function detail(label,value){ return `<div class="detail"><small>${esc(label)}</small><strong>${value??'â€”'}</strong></div>`; }
function pct(v){ return v===null||v===undefined?'â€”':`${n(v,1)}%`; }
function bool(v){ return Number(v)===1?'YES':'NO'; }
function weekLabel(w){
  if(!w) return 'â€”';
  return `${w.forecast_week_start||'?'} â†’ ${w.forecast_week_end||'?'} Â· freeze ${w.cutoff_date||'?'}`;
}
function entryTime(r){ return r.evaluation_time||r.entry_allowed_time||''; }
function entrySide(r){ return r.side||r.direction||''; }
function entryPrice(r){ return r.entry_price??r.decision_price??r.candidate_entry_price; }
function entryObjective(r){ return r.objective_price??r.next_opposing_level; }
function entryRule(r){ return r.rule_source||'ORIGINAL'; }
function entryCols(){ return [
  {key:'evaluation_time',label:'Time',fmt:(v,r)=>shortT(entryTime(r))},
  {key:'side',label:'Side',fmt:(v,r)=>badge(entrySide(r))},
  {key:'entry_price',label:'Entry',fmt:(v,r)=>n(entryPrice(r),2),className:'num'},
  {key:'grade',label:'Grade',fmt:v=>badge(v,v==='A_PLUS'||v==='A'?'good':'wait')},
  {key:'sqs',label:'SQS',fmt:v=>n(v,1),className:'num'},
  {key:'objective_price',label:'Objective',fmt:(v,r)=>n(entryObjective(r),2),className:'num'},
  {key:'room_m15_atr',label:'Room ATR',fmt:v=>n(v,2),className:'num'},
  {key:'leg_consumed_pct',label:'Consumed',fmt:v=>pct(v),className:'num'},
  {key:'rule_source',label:'Rule Source',fmt:(v,r)=>badge(entryRule(r),'info')},
  {key:'outcome',label:'Outcome',fmt:v=>v?badge(v,v==='TARGET_FIRST'?'good':'wait'):'â€”'}
]; }
function renderTable(el,rows,cols,{click}={}){
  if(!rows?.length){ el.innerHTML='<tbody><tr><td class="muted">No records</td></tr></tbody>'; return; }
  const head=cols.map(c=>`<th>${esc(c.label)}</th>`).join('');
  const body=rows.map((r,i)=>`<tr class="${click?'clickable':''}" data-row="${i}">`+cols.map(c=>{
    const raw=r[c.key]; const val=c.fmt?c.fmt(raw,r):esc(raw);
    return `<td class="${c.className||''}">${val}</td>`;
  }).join('')+'</tr>').join('');
  el.innerHTML=`<thead><tr>${head}</tr></thead><tbody>${body}</tbody>`;
  if(click) el.querySelectorAll('tbody tr').forEach(tr=>tr.addEventListener('click',()=>click(rows[Number(tr.dataset.row)])));
}
function showTab(name){
  document.querySelectorAll('.tab-page').forEach(x=>x.classList.toggle('active',x.id===`tab-${name}`));
  document.querySelectorAll('#tabs button').forEach(x=>x.classList.toggle('active',x.dataset.tab===name));
}
function stateBar(label,value,max){
  const w=max?Math.max(2,(value/max)*100):0;
  return `<div class="state-row"><span>${esc(label)}</span><div class="bar-track"><div class="bar-fill" style="width:${w}%"></div></div><b>${n(value,0)}</b></div>`;
}
async function loadHealth(){
  const h=await api('/api/system-health'); state.health=h;
  const f=h.source_freshness||{}, d=h.database||{}, s=h.scheduler||{}, g=h.safety_guard||{}, p=h.processing||{};
  const stale=f.status==='SOURCE_STALE';
  const processingLag=Number(p.lag_minutes||0);
  const processing=!stale && processingLag>0;
  const banner=$('staleBanner');
  banner.classList.toggle('hidden',!(stale||processing));
  banner.classList.toggle('processing',processing);
  if(stale) banner.textContent='SOURCE STALE â€” DO NOT USE CURRENT SIGNALS';
  else if(processing) banner.textContent=`ENGINE PROCESSING â€” JOURNEY LAGS SOURCE BY ${n(processingLag,0)} MIN`;
  $('sourceStatus').textContent=f.status||'â€”'; $('sourceStatus').className=stale?'negative':'positive';
  $('dataAsOf').textContent=t(f.actual_latest_m15_close);
  $('dbAsOf').textContent=t(d.phase3_as_of||d.db_m15_as_of);
  $('schedulerStatus').textContent=s.display_status||(s.status==='OK'?`${s.State} / ${s.LastTaskResult}`:'UNAVAILABLE');
  $('healthCards').innerHTML=[
    metric('Source Freshness',f.status||'â€”',f.reason||'',stale?'bad':'good'),
    metric('Engine Processing',p.status||'â€”',processing?`Journey lag ${n(processingLag,0)} min`:'Source and engine aligned',processing?'warn':'good'),
    metric('Expected M15',shortT(f.expected_latest_completed_m15_close),`Source lag ${n(f.wallclock_lag_minutes,0)} min`,stale?'bad':'info'),
    metric('DB M15',shortT(d.db_m15_as_of),'Closed bars ingested','info'),
    metric('Schema',g.schema_version??'â€”','Dashboard views '+(g.dashboard_views_valid?'valid':'invalid'),g.dashboard_views_valid?'good':'bad'),
    metric('Executions',d.execution_count??0,`${d.resolved_outcome_count??0} resolved`,'info')
  ].join('');
  $('checkpointGrid').innerHTML=[
    detail('Phase 3',esc(t(d.phase3_as_of))), detail('Phase 4',esc(t(d.phase4_as_of))),
    detail('Phase 5',esc(t(d.phase5_as_of))), detail('Phase 6 Observation',esc(t(d.phase6_observation_as_of))),
    detail('Phase 6 Lineage',esc(t(d.phase6_lineage_as_of))), detail('Failed Engine Runs',esc(d.failed_engine_run_count??0))
  ].join('');
  $('schedulerGrid').innerHTML=[
    detail('State',esc(s.State||s.status||'â€”')), detail('Enabled',esc(s.Enabled===true?'YES':s.Enabled===false?'NO':'â€”')),
    detail('Last Run',esc(t(s.LastRunTime))), detail('Last Result',esc(s.LastTaskResult??'â€”')),
    detail('Next Run',esc(t(s.NextRunTime))), detail('Missed Runs',esc(s.MissedRuns??'â€”'))
  ].join('');
  $('schedulerLog').textContent=(h.scheduler_log_tail||[]).join('\n');
}

async function loadOverview(){
  const week=$('overviewWeek')?.value||'', view=$('overviewView')?.value||'current';
  const [o,analysis,entries,aggregate]=await Promise.all([
    api(`/api/overview${week?`?cutoff_date=${encodeURIComponent(week)}`:''}`),
    week?api(`/api/week-analysis?cutoff_date=${encodeURIComponent(week)}`):Promise.resolve({}),
    api(`/api/engine-entries?cutoff_date=${encodeURIComponent(week)}&view=${encodeURIComponent(view)}`),
    api('/api/analytics-summary')
  ]); state.overview=o;
  const research=o.forecast_week_start?await api(`/api/research-rc1?date=${encodeURIComponent(o.forecast_week_start)}`):{};
  const rr=research.regime||{}, rf=research.forward||{}, rm=research.meta||{};
  const ref=aggregate.report_reference||{};
  $('aggregateAnalyticsCards').innerHTML=[
    metric('Completed Weeks',aggregate.completed_weeks??0,'SQLite analytical coverage','info'),
    metric('Machine Avg',aggregate.machine_average_score==null?'â€”':`${n(aggregate.machine_average_score,2)}/10`,'Deterministic report-style score','info'),
    metric('Machine Median',aggregate.machine_median_score==null?'â€”':`${n(aggregate.machine_median_score,2)}/10`,'Completed DB weeks','info'),
    metric('Upper-Zone Hit',aggregate.upper_zone_hit_rate==null?'â€”':pct(aggregate.upper_zone_hit_rate),'Completed DB weeks',Number(aggregate.upper_zone_hit_rate)>=50?'good':'warn'),
    metric('Lower-Zone Hit',aggregate.lower_zone_hit_rate==null?'â€”':pct(aggregate.lower_zone_hit_rate),'Completed DB weeks',Number(aggregate.lower_zone_hit_rate)>=50?'good':'warn'),
    metric('Sequence Match',aggregate.sequence_match_rate==null?'â€”':pct(aggregate.sequence_match_rate),'Expected extreme order',Number(aggregate.sequence_match_rate)>=50?'good':'warn')
  ].join('');
  $('reportBenchmarkGrid').innerHTML=[
    detail('Completed Weeks',esc(ref.completed_weeks??'â€”')), detail('Average Score',esc(ref.average_score==null?'â€”':`${n(ref.average_score,2)} / 10`)),
    detail('Median Score',esc(ref.median_score==null?'â€”':`${n(ref.median_score,2)} / 10`)), detail('Best / Lowest',esc(`${n(ref.best_score,1)} / ${n(ref.lowest_score,1)}`)),
    detail('Prospective Weeks',esc(ref.completed_prospective_weeks??'â€”')), detail('Prospective Average',esc(ref.prospective_average==null?'â€”':`${n(ref.prospective_average,1)} / 10`))
  ].join('');
  renderTable($('aggregateHistoryTable'),aggregate.weekly_history||[],[
    {key:'forecast_week_start',label:'Week'}, {key:'side',label:'Side',fmt:v=>badge(v)},
    {key:'score',label:'Score',fmt:v=>`${n(v,1)}/10`,className:'num'},
    {key:'upper_zone_hit',label:'Upper',fmt:v=>badge(v?'HIT':'MISS',v?'good':'bad')},
    {key:'lower_zone_hit',label:'Lower',fmt:v=>badge(v?'HIT':'MISS',v?'good':'bad')},
    {key:'sequence_match',label:'Sequence',fmt:v=>badge(v?'MATCH':'MISS',v?'good':'bad')}
  ]);
  const sm=analysis.summary||{};
  $('engineSummaryCards').innerHTML=[
    metric('Current Engine',sm.current_engine_entries??0,'Selected week','good'),
    metric('Original',sm.original_entries??0,'Historical emitted','info'),
    metric('Recovered',sm.recovered_entries??0,'Current rules','warn'),
    metric('A+',sm.a_plus_entries??0,'Current engine','good'),
    metric('A',sm.a_entries??0,'Current engine','info'),
    metric('Correctly Blocked',sm.correctly_blocked??0,'Adverse-first','good')
  ].join('');
  $('overviewEntryLabel').textContent=view==='current'?'Current Engine Replay':'Original Historical';
  renderTable($('overviewEntryTable'),entries,entryCols());
  $('overviewCards').innerHTML=[
    metric('RC1 Master Regime',rr.regime||'â€”',rr.phase||`Week start ${o.forecast_week_start||'â€”'}`,'info'),
    metric('Weekly Map Bias',o.final_weekly_side||'â€”',`Context only · freeze ${o.weekly_cutoff_date||'â€”'}`,o.final_weekly_side==='SELL'?'bad':'good'),
    metric('RC1 Execution',rr.regime==='TREND_CONTINUATION'?'NO_SIGNAL':'VALIDATED TRIGGER REQUIRED',rm.execution_mode||'SHADOW',rr.regime==='TREND_CONTINUATION'?'warn':'good'),
    metric('Legacy Daily Bias',o.current_daily_direction||'â€”',`Context only · DBS ${n(o.dbs,2)}`,'warn'),
    metric('Forward RC1',rf.resolved??0,rf.win_rate==null?'0/100 fresh trades':`${pct(100*rf.win_rate)} · ${rf.resolved}/100`,'info'),
    metric('Market Price',n(o.market_price,2),t(o.market_as_of),'info')
  ].join('');
  $('weeklyRangeLabel').textContent=`${o.forecast_week_start||'â€”'} â†’ ${o.forecast_week_end||'â€”'}`;
  $('controlGrid').innerHTML=[
    detail('Resistance Control',esc(n(o.resistance_control,2))), detail('Resistance Zone',esc(`${n(o.resistance_lower,2)} â€“ ${n(o.resistance_upper,2)}`)),
    detail('Support Control',esc(n(o.support_control,2))), detail('Support Zone',esc(`${n(o.support_lower,2)} â€“ ${n(o.support_upper,2)}`)),
    detail('Daily Pivot',esc(n(o.daily_pivot,2))), detail('Weekly Route',esc(o.final_weekly_side||'â€”'))
  ].join('');
  const counts={ACTIVE:o.active_entry_legs||0,REACTION_ACTIVE:o.reaction_active_entry_legs||0,ENTRY_TRIGGERED:o.entry_triggered_entry_legs||0,MISSED:o.missed_entry_legs||0,INVALIDATED:o.invalidated_entry_legs||0};
  const max=Math.max(...Object.values(counts),1); $('entryStateBars').innerHTML=Object.entries(counts).map(([k,v])=>stateBar(k,v,max)).join('');
  $('entryStateAsOfLabel').textContent=`Immutable projection as-of ${t(o.selected_as_of||o.market_as_of)}`;
  $('mondaySummary').innerHTML=[
    detail('Week Start',esc(o.monday_week_start_date)),detail('Branch',badge(o.active_branch,'info')),
    detail('Bias Relation',esc(o.branch_bias_relation)),detail('Confidence',esc(n(o.branch_confidence,0))),
    detail('Activation Method',esc(o.activation_method)),detail('Confirmed At',esc(t(o.branch_confirmed_at)))
  ].join('');
  $('dailySummary').innerHTML=[
    detail('Trading Date',esc(o.daily_trading_date)),detail('Evaluation',esc(t(o.daily_evaluation_time))),
    detail('Legacy Direction',badge(o.current_daily_direction)),detail('Legacy State',badge(o.current_daily_state)),
    detail('DBS',esc(n(o.dbs,2))),detail('Pivot',esc(n(o.daily_pivot,2)))
  ].join('');
}
async function loadWeekly(){
  const week=$('weeklyWeek')?.value||'', view=$('weeklyView')?.value||'current';
  const [selectedRows,data,analysis,entries,weeklyAnalytics,reportMap]=await Promise.all([
    api(`/api/weekly${week?`?cutoff_date=${encodeURIComponent(week)}`:'?limit=1'}`),
    api('/api/weekly?limit=52'),
    week?api(`/api/week-analysis?cutoff_date=${encodeURIComponent(week)}`):Promise.resolve({}),
    api(`/api/engine-entries?cutoff_date=${encodeURIComponent(week)}&view=${encodeURIComponent(view)}`),
    week?api(`/api/weekly-analytics?cutoff_date=${encodeURIComponent(week)}`):Promise.resolve({}),
    week?api(`/api/weekly-report-map?cutoff_date=${encodeURIComponent(week)}`):Promise.resolve({})
  ]);
  state.weekly=data;
  const completed=selectedRows[0]||data[0]||{};
  const researchDate=completed.forecast_week_start||week;
  const researchWeek=researchDate?await api(`/api/research-rc1?date=${encodeURIComponent(researchDate)}`):{};
  const rr=researchWeek.regime||{}, rm=researchWeek.meta||{};
  $('weeklyResearchCards').innerHTML=[metric('RC1 Master Regime',rr.regime||'â€”',`week-start freeze ${researchDate||'â€”'}`,'info'),metric('Regime Phase',rr.phase||'â€”',rr.last_struct_type?`${rr.last_struct_type} ${rr.last_struct_dir||''}`:'','info'),metric('Weekly Side',completed.final_weekly_side||'â€”','Bias only Â· not execution authority',completed.final_weekly_side==='SELL'?'bad':'good'),metric('Execution Authority',rr.regime==='TREND_CONTINUATION'?'NO_SIGNAL':'RC1 TRIGGER REQUIRED','Validated intraday only',rr.regime==='TREND_CONTINUATION'?'warn':'good'),metric('Research Version',rm.research_version||'â€”',rm.research_status||'â€”','info'),metric('Legacy Route Confidence',n(completed.route_confidence,0),'Context only Â· not probability','warn')].join('');
  const aligned=completed.side_aligned===null||completed.side_aligned===undefined?'PENDING':bool(completed.side_aligned);
  $('weeklyHero').innerHTML=[
    metric('Forecast Side',completed.final_weekly_side||'â€”',`${completed.forecast_week_start||'â€”'} â†’ ${completed.forecast_week_end||'â€”'}`,completed.final_weekly_side==='SELL'?'bad':'good'),
    metric('Actual High',n(completed.actual_high,2),t(completed.actual_high_time),'info'),
    metric('Actual Low',n(completed.actual_low,2),t(completed.actual_low_time),'info'),
    metric('Actual Close',n(completed.actual_close,2),`Side aligned: ${aligned}`,aligned==='YES'?'good':aligned==='NO'?'bad':'warn')
  ].join('');
  const wa=weeklyAnalytics||{}, finalComp=wa.components||{}, liveComp=wa.provisional_components||{}, acc=wa.accuracy||{}, fc=wa.forecast||{};
  const comp=wa.completed?finalComp:liveComp;
  const displayScore=wa.completed?wa.total_score:wa.provisional_total_score;
  const scoreLabel=wa.completed?'Report-Style Score':'LIVE Provisional Score';
  const scoreSub=wa.completed?(wa.score_type||'Final'):'Partial week Â· final score freezes after Friday close';
  $('weeklyAnalyticsCards').innerHTML=[
    metric(scoreLabel,displayScore===null||displayScore===undefined?'Pending':`${n(displayScore,1)}/10`,scoreSub,wa.completed?'info':'warn'),
    metric('Upper Zone',`${n((fc.upper_zone||[])[0],2)} â€“ ${n((fc.upper_zone||[])[1],2)}`,'Resistance / turning map','info'),
    metric('Lower Zone',`${n((fc.lower_zone||[])[0],2)} â€“ ${n((fc.lower_zone||[])[1],2)}`,'Support / target map','info'),
    metric('H4 ATR',n(fc.h4_atr,2),'Normalization basis','info'),
    metric('Expected First',acc.expected_extreme_first||'â€”','Forecast sequence','warn'),
    metric('Actual First',acc.actual_extreme_first||'â€”',acc.sequence_match===true?'Sequence matched':acc.sequence_match===false?'Sequence missed':'Pending',acc.sequence_match===true?'good':acc.sequence_match===false?'bad':'warn')
  ].join('');
  $('weeklyScoreGrid').innerHTML=[
    detail('Directional Thesis',`${n(comp.direction,1)} / 2`), detail('High / Resistance Zone',`${n(comp.upper_zone,1)} / 2`),
    detail('Low / Support Zone',`${n(comp.lower_zone,1)} / 2`), detail('Movement Sequence',`${n(comp.sequence,1)} / 2`),
    detail('Calibration Proxy',`${n(comp.calibration,1)} / 2${wa.completed?'':' Â· LIVE'}`), detail(wa.completed?'Total':'Live Provisional Total',displayScore===null||displayScore===undefined?'Pending':`${n(displayScore,1)} / 10${wa.completed?'':' Â· NOT FROZEN'}`)
  ].join('');
  $('weeklyAccuracyGrid').innerHTML=[
    detail('High-Zone Miss',`${n(acc.upper_zone_miss_points,2)} pts Â· ${n(acc.upper_zone_miss_h4_atr,2)} H4 ATR`),
    detail('Low-Zone Miss',`${n(acc.lower_zone_miss_points,2)} pts Â· ${n(acc.lower_zone_miss_h4_atr,2)} H4 ATR`),
    detail('High Miss / Weekly Range',acc.upper_zone_miss_weekly_range_pct===null||acc.upper_zone_miss_weekly_range_pct===undefined?'â€”':pct(acc.upper_zone_miss_weekly_range_pct)),
    detail('Low Miss / Weekly Range',acc.lower_zone_miss_weekly_range_pct===null||acc.lower_zone_miss_weekly_range_pct===undefined?'â€”':pct(acc.lower_zone_miss_weekly_range_pct)),
    detail('Upper Zone Hit',acc.upper_zone_hit===null||acc.upper_zone_hit===undefined?'Pending':badge(acc.upper_zone_hit?'YES':'NO',acc.upper_zone_hit?'good':'bad')),
    detail('Lower Zone Hit',acc.lower_zone_hit===null||acc.lower_zone_hit===undefined?'Pending':badge(acc.lower_zone_hit?'YES':'NO',acc.lower_zone_hit?'good':'bad'))
  ].join('');
  const smap=reportMap.scenario_map||{};
  const scenarios=[smap.primary,smap.direct_continuation,smap.failure_route].filter(Boolean);
  $('weeklyScenarioMap').innerHTML=scenarios.map((s,i)=>`<div class="scenario-card ${i===0?'primary-scenario':''}"><strong>${esc(s.name||'SCENARIO')}</strong><span>${(s.steps||[]).map(esc).join(' â†’ ')}</span></div>`).join('')||'<span class="muted">No scenario map</span>';
  const levelRows=(reportMap.level_roles||[]).slice().sort((a,b)=>(a.distance_from_cutoff??999999)-(b.distance_from_cutoff??999999)).slice(0,12);
  renderTable($('weeklyLevelTable'),levelRows,[
    {key:'center',label:'Level',fmt:v=>n(v,2),className:'num'},
    {key:'report_role',label:'Role',fmt:v=>badge(v,v==='STRATEGIC_TARGET'?'good':v==='CONTROL_BREAKOUT'?'warn':'info')},
    {key:'original_role',label:'Market Role'},
    {key:'lower',label:'Lower',fmt:v=>n(v,2),className:'num'},
    {key:'upper',label:'Upper',fmt:v=>n(v,2),className:'num'},
    {key:'is_regime_control',label:'Control',fmt:v=>Number(v)===1?badge('YES','warn'):'â€”'}
  ]);
  const sm=analysis.summary||{};
  $('weeklyEngineCards').innerHTML=[
    metric('Current Engine',sm.current_engine_entries??0,'Selected week','good'), metric('Original',sm.original_entries??0,'Historical','info'),
    metric('Recovered',sm.recovered_entries??0,'Rule improvements','warn'), metric('A+',sm.a_plus_entries??0,'Current engine','good'),
    metric('A',sm.a_entries??0,'Current engine','info'), metric('Target First',sm.target_first??0,'Recovered outcomes','good')
  ].join('');
  renderTable($('weeklyEntryTable'),entries,entryCols());
  const cols=[
    {key:'cutoff_date',label:'Freeze'}, {key:'forecast_week_start',label:'Week Start'},
    {key:'final_weekly_side',label:'Side',fmt:v=>badge(v)}, {key:'structural_state',label:'State'},
    {key:'route_confidence',label:'Route',fmt:v=>n(v,0),className:'num'},
    {key:'resistance_control',label:'Resistance',fmt:v=>n(v,2),className:'num'},
    {key:'support_control',label:'Support',fmt:v=>n(v,2),className:'num'},
    {key:'actual_high',label:'Actual High',fmt:v=>n(v,2),className:'num'},
    {key:'actual_high_time',label:'High Time',fmt:v=>shortT(v)},
    {key:'actual_low',label:'Actual Low',fmt:v=>n(v,2),className:'num'},
    {key:'actual_low_time',label:'Low Time',fmt:v=>shortT(v)},
    {key:'actual_close',label:'Close',fmt:v=>n(v,2),className:'num'},
    {key:'side_aligned',label:'Aligned',fmt:v=>v===null||v===undefined?'â€”':badge(bool(v),v?'good':'bad')}
  ];
  renderTable($('weeklyTable'),data,cols);
}
async function loadMeta(){
  state.meta=await api('/api/meta');
  const weeks=state.meta.weeks||[];
  const weekOptions=weeks.map(w=>`<option value="${esc(w.cutoff_date)}">${esc(weekLabel(w))}</option>`).join('');
  $('overviewWeek').innerHTML=weekOptions;
  $('weeklyWeek').innerHTML=weekOptions;
  $('blockedWeek').innerHTML=weekOptions;
  const latest=state.meta.latest_daily_date||'';
  const defaultWeek=weeks.find(w=>latest && String(w.forecast_week_start||'')<=latest)||weeks[0];
  if(defaultWeek){ $('overviewWeek').value=defaultWeek.cutoff_date; $('weeklyWeek').value=defaultWeek.cutoff_date; $('blockedWeek').value=defaultWeek.cutoff_date; }
  const sel=$('journeyDate');
  const journeyDates=[...new Set([...(state.meta.journey_dates||[]),...(state.meta.forecast_dates||[])])].sort().reverse();
  sel.innerHTML=journeyDates.map(d=>`<option value="${esc(d)}">${esc(d)}</option>`).join('');
  const preferredJourneyDate=(state.meta.forecast_dates||[])[0]||state.meta.latest_daily_date||'';
  if(preferredJourneyDate && [...sel.options].some(o=>o.value===preferredJourneyDate)) sel.value=preferredJourneyDate;
  if($('researchDate')){ $('researchDate').innerHTML=journeyDates.map(d=>`<option value="${esc(d)}">${esc(d)}</option>`).join(''); if(preferredJourneyDate) $('researchDate').value=preferredJourneyDate; }
}

function forecastStatusKind(v){
  const x=String(v||'');
  if(x==='CONFIRMED'||x==='CONFIRMING') return 'good';
  if(x.includes('FAILED')||x.includes('CONTRADICTED')) return 'bad';
  return 'warn';
}
function regimeScenario(regime,phase=''){
  if(regime==='SWEEP_REJECT_BALANCE') return ['Upper sweep + rejection â†’ SELL toward equilibrium','Lower sweep + reclaim â†’ BUY toward equilibrium','Accepted edge break â†’ TRANSITION / expansion ignition'];
  if(regime==='ACCEPTANCE_EXPANSION') return ['Accepted break holds â†’ continuation / retest','Failed acceptance â†’ TRANSITION','Execute only when an RC1 validated trigger qualifies'];
  if(regime==='TRANSITION') return [phase==='BALANCE_FORMING'?'Balance forming â†’ WAIT for edge evidence':'Old regime losing authority â†’ no unconditional direction','Validated transition trigger â†’ shadow execution','Acceptance/rejection decides next master regime'];
  if(regime==='TREND_CONTINUATION') return ['Inherited trend remains intact','RC1 has no >90% validated execution rule for this regime','Execution authority = NO_SIGNAL'];
  return ['No research regime available'];
}
function scenarioHtml(regime,phase=''){
  return regimeScenario(regime,phase).map((x,i)=>`<div class="scenario-card ${i===0?'primary-scenario':''}"><strong>${i===0?'PRIMARY':'BRANCH '+(i+1)}</strong><span>${esc(x)}</span></div>`).join('');
}
async function loadResearch(){
  const date=$('researchDate')?.value||'';
  const [p,history]=await Promise.all([api(`/api/research-rc1${date?`?date=${encodeURIComponent(date)}`:''}`),api('/api/research-regimes?limit=120')]);
  const r=p.regime||{}, m=p.meta||{}, f=p.forward||{}, mon=p.monitor||[], bt=p.backtest||[], sh=p.shadow_signals||[];
  $('researchState').className='forecast-state '+(r.regime==='TRANSITION'?'warn':'good');
  $('researchState').innerHTML=`<strong>${esc(r.regime||'â€”')}</strong><span>${esc(r.phase||'')} Â· ${esc(m.research_status||'â€”')} Â· ${esc(m.execution_mode||'SHADOW')}</span>`;
  $('researchHero').innerHTML=[metric('Master Regime',r.regime||'â€”',`as of ${r.trading_date||'â€”'}`,'info'),metric('Structural Event',r.last_struct_type||'â€”',`${r.last_struct_dir||'â€”'} Â· age ${n(r.days_since_struct,0)}`,'info'),metric('RC1 Version',m.research_version||'â€”',m.research_status||'â€”','good'),metric('Forward Trades',f.resolved??0,`${f.wins??0}W / ${f.losses??0}L of ${f.target??100}`,'info'),metric('Forward WR',f.win_rate==null?'Pending':pct(100*f.win_rate),'Fresh trades only',f.win_rate==null?'warn':f.win_rate>=.90?'good':'bad'),metric('Parity',m.parity_status||'—',`${m.parity_trades||'—'} trades · ${m.parity_regime_days||'—'} regimes`,m.parity_status==='PASS'?'good':'bad')].join('');
  $('researchScenario').innerHTML=scenarioHtml(r.regime,r.phase);
  $('researchForward').innerHTML=[detail('Forward Start',esc(m.forward_start||'â€”')),detail('Execution Mode',badge(m.execution_mode||'SHADOW','warn')),detail('Target Trades',esc(f.target??100)),detail('Resolved',esc(f.resolved??0)),detail('Wins / Losses',esc(`${f.wins??0} / ${f.losses??0}`)),detail('Trend Continuation',esc(m.trend_continuation_policy||'NO_VALIDATED_SIGNAL'))].join('');
  renderTable($('researchMonitorTable'),mon,[{key:'grade',label:'Grade',fmt:v=>badge(v,v==='A'?'good':'warn')},{key:'risk',label:'Risk',fmt:(v,r)=>r.grade==='B'?'0.5x':'1.0x'},{key:'rule_id',label:'Rule'},{key:'required_regime',label:'Required Regime'},{key:'side',label:'Side',fmt:v=>badge(v)},{key:'status',label:'State',fmt:v=>badge(v,v==='QUALIFIED'?'good':v==='CONTEXT_BLOCKED'?'bad':'info')},{key:'validation_rate',label:'Val WR',fmt:v=>pct(100*v),className:'num'},{key:'validation_support',label:'Val N',fmt:v=>n(v,0),className:'num'},{key:'config',label:'TP/SL/Hold'},{key:'stability_margin',label:'Stability',fmt:v=>pct(100*v),className:'num'}]);
  renderTable($('researchBacktestTable'),bt,[{key:'period',label:'Period'},{key:'trades',label:'Trades',fmt:v=>n(v,0),className:'num'},{key:'win_rate',label:'WR',fmt:v=>pct(100*v),className:'num'},{key:'trades_per_week',label:'Trades/Wk',fmt:v=>n(v,2),className:'num'},{key:'net_r',label:'Net R',fmt:v=>n(v,2),className:'num'}]);
  renderTable($('researchShadowTable'),sh,[{key:'signal_time',label:'Signal',fmt:v=>shortT(v)},{key:'grade',label:'Grade',fmt:v=>badge(v,v==='A'?'good':'warn')},{key:'rule_id',label:'Rule'},{key:'side',label:'Side',fmt:v=>badge(v)},{key:'status',label:'Status',fmt:v=>badge(v,v==='CLOSED_WIN'?'good':v==='CLOSED_LOSS'||v==='EXPIRED_LOSS'?'bad':'wait')},{key:'entry_price',label:'Entry',fmt:v=>n(v,2),className:'num'},{key:'tp_price',label:'TP',fmt:v=>n(v,2),className:'num'},{key:'sl_price',label:'SL',fmt:v=>n(v,2),className:'num'},{key:'result',label:'Result',fmt:v=>v?badge(v,v==='WIN'?'good':'bad'):'â€”'}]);
  renderTable($('researchRegimeTable'),history,[{key:'trading_date',label:'Date'},{key:'regime',label:'Regime',fmt:v=>badge(v,'info')},{key:'phase',label:'Phase'},{key:'last_struct_type',label:'Last Event'},{key:'last_struct_dir',label:'Dir'},{key:'days_since_struct',label:'Age',fmt:v=>n(v,0),className:'num'},{key:'d1_eff10',label:'D1 Eff10',fmt:v=>n(v,3),className:'num'}]);
}

function renderJourneyResearch(p){
  const r=p.regime||{}, m=p.meta||{}, mon=p.monitor||[]; const qualified=mon.filter(x=>x.status==='QUALIFIED');
  $('journeyResearchState').className='forecast-state '+(qualified.length?'good':r.regime==='TRANSITION'?'warn':'info');
  $('journeyResearchState').innerHTML=`<strong>${esc(r.regime||'â€”')}</strong><span>${qualified.length?qualified.length+' RC1 setup(s) QUALIFIED':'Validated execution: WAIT / NO SIGNAL'} Â· ${esc(m.research_version||'RC1')}</span>`;
  $('journeyResearchCards').innerHTML=[metric('Master Regime',r.regime||'â€”',r.phase||'','info'),metric('Last Structural Event',r.last_struct_type||'â€”',`${r.last_struct_dir||'â€”'} Â· age ${n(r.days_since_struct,0)}`,'info'),metric('Validated Setups',qualified.length,qualified.length?'Execution authority active':'Wait for trigger',qualified.length?'good':'warn'),metric('Execution Mode',m.execution_mode||'SHADOW','Forward validation only','warn'),metric('Legacy Forecast','COMPARISON ONLY','No execution authority','info'),metric('Trend Continuation',r.regime==='TREND_CONTINUATION'?'NO_SIGNAL':'N/A','No >90% validated rule','warn')].join('');
  $('journeyResearchScenario').innerHTML=scenarioHtml(r.regime,r.phase);
  $('journeyResearchExecution').innerHTML=[detail('Research Version',esc(m.research_version||'â€”')),detail('Status',esc(m.research_status||'â€”')),detail('Qualified Rules',esc(qualified.map(x=>x.rule_id).join(', ')||'NONE')),detail('Execution Authority',qualified.length?badge('RC1 QUALIFIED','good'):badge('WAIT','warn')),detail('Forward Start',esc(m.forward_start||'â€”')),detail('Rule Changes',esc((p.forward||{}).rules_changed??0)),detail('Parity',badge(m.parity_status||'—',m.parity_status==='PASS'?'good':'bad')),detail('Grade B Risk',esc(m.grade_b_risk||'0.5x_research_unit'))].join('');
}

function renderJourneyForecast(payload){
  const f=payload.forecast||{}, a=payload.actual||{}, v=payload.validation||{}, b=payload.daily_bias||{}, hits=payload.rule_hits||[];
  if(!f.forecast_date){
    $('journeyForecastState').innerHTML='<span class="muted">No frozen daily prediction is available for this date.</span>';
    $('journeyForecastCards').innerHTML=''; $('journeyForecastGrid').innerHTML=''; $('journeyValidationGrid').innerHTML='';
    renderTable($('journeyForecastRuleTable'),[],[]); $('journeyRuleCount').textContent='0 rules'; return;
  }
  const status=v.forecast_state||'FROZEN_UNTESTED', kind=forecastStatusKind(status);
  $('journeyForecastState').className=`forecast-state ${kind}`;
  $('journeyForecastState').innerHTML=`<strong>${esc(f.statistical_direction||'â€”')} ${esc(f.direction_grade||'')}</strong><span>${esc(f.route_prediction||'â€”')} â†’ ${esc(f.path_prediction||'â€”')} Â· ${esc(f.forecast_relationship||'â€”')} Â· ${esc(status)}</span>`;
  $('journeyForecastCards').innerHTML=[
    metric('Frozen Direction',f.statistical_direction||'â€”',`${f.direction_grade||'â€”'} Â· ${f.buy_votes??0}/${f.sell_votes??0} BUY/SELL`,f.statistical_direction==='BUY'?'good':f.statistical_direction==='SELL'?'bad':'warn'),
    metric('Frozen Route',f.route_prediction||'â€”',f.path_prediction||'â€”','info'),
    metric('Weekly Bias',f.weekly_side||'â€”',f.forecast_relationship||'â€”',f.weekly_side==='SELL'?'bad':'good'),
    metric('Preferred Turn',`${n(f.preferred_turn_low,2)} â€“ ${n(f.preferred_turn_high,2)}`,'Frozen zone','info'),
    metric('Recovery Target 1',`${n(f.recovery_target1_low,2)} â€“ ${n(f.recovery_target1_high,2)}`,'Frozen objective','info'),
    metric('Forecast State',status,v.direction_result||'â€”',kind)
  ].join('');
  $('journeyForecastGrid').innerHTML=[
    detail('Forecast Date',esc(f.forecast_date)),detail('Freeze Time',esc(t(f.freeze_time))),
    detail('Source Completed Day',esc(f.source_completed_date)),detail('Freeze Mode',esc(f.freeze_mode)),
    detail('Rule Version',esc(f.rule_version)),detail('Daily Pivot',esc(n(f.daily_pivot,2))),
    detail('S1 / S2',esc(`${n(f.s1,2)} / ${n(f.s2,2)}`)),detail('Extension Zone',esc(`${n(f.extension_low,2)} â€“ ${n(f.extension_high,2)}`)),
    detail('Recovery Target 2',esc(n(f.recovery_target2,2))),detail('Stretch Recovery',esc(`${n(f.stretch_target_low,2)} â€“ ${n(f.stretch_target_high,2)}`)),
    detail('Invalidation 1',esc(n(f.invalidation_level1,2))),detail('Invalidation 2',esc(n(f.invalidation_level2,2)))
  ].join('');
  $('journeyValidationGrid').innerHTML=[
    detail('Forecast State',badge(status,kind)),detail('Direction Result',esc(v.direction_result||'â€”')),
    detail('Route State',esc(v.route_state||'â€”')),detail('Route Result',esc(v.route_result||'â€”')),
    detail('Path Result',esc(v.path_result||'â€”')),detail('Weekly Result',esc(v.weekly_direction_result||'â€”')),
    detail('Actual / Current Direction',badge(a.direction||'â€”')),detail('Actual / Current Route',esc(a.route||'â€”')),
    detail('Open / Close',esc(`${n(a.open,2)} / ${n(a.close,2)}`)),detail('High / Low',esc(`${n(a.high,2)} / ${n(a.low,2)}`)),
    detail('Daily Bias',badge(b.current_daily_direction||'â€”')),detail('Daily State / DBS',esc(`${b.current_daily_state||'â€”'} / ${n(b.dbs,1)}`))
  ].join('');
  $('journeyRuleCount').textContent=`${hits.length} activated rules`;
  renderTable($('journeyForecastRuleTable'),hits,[
    {key:'rule_category',label:'Category',fmt:v=>badge(v,'info')},{key:'rule_id',label:'Rule'},
    {key:'formation',label:'Frozen Formation'},{key:'prediction',label:'Prediction',fmt:v=>badge(v,v==='BUY'?'good':v==='SELL'?'bad':'info')},
    {key:'historical_accuracy',label:'3M %',fmt:v=>pct(v),className:'num'},{key:'historical_support',label:'N',fmt:v=>n(v,0),className:'num'},
    {key:'holdout_accuracy',label:'Holdout %',fmt:v=>pct(v),className:'num'}
  ]);
}

async function loadJourney(){
  const date=$('journeyDate').value, grade=$('journeyGrade').value, view=$('journeyView')?.value||'current';
  const [data,forecastPayload,researchPayload]=await Promise.all([
    api(`/api/journey?date=${encodeURIComponent(date)}&grade=${encodeURIComponent(grade)}&view=${encodeURIComponent(view)}&limit=1000`),
    api(`/api/daily-forecast?date=${encodeURIComponent(date)}`),
    api(`/api/research-rc1?date=${encodeURIComponent(date)}`)
  ]);
  renderJourneyResearch(researchPayload);
  renderJourneyForecast(forecastPayload);
  const f=forecastPayload.forecast||{}, v=forecastPayload.validation||{};
  const annotated=data.map(r=>({...r,
    forecast_relation:(f.statistical_direction==='BUY'||f.statistical_direction==='SELL')?(r.side===f.statistical_direction?'WITH_FORECAST':'COUNTER_FORECAST'):'NO_FORECAST',
    forecast_route_state:v.route_state||'UNRESOLVED'}));
  $('journeyCount').textContent=`${annotated.length} evaluations`;
  const cols=[
    {key:'time',label:'Time',fmt:v=>shortT(v)}, {key:'status',label:'Status',fmt:v=>badge(v,'info')},
    {key:'price',label:'Price',fmt:v=>n(v,2),className:'num'}, {key:'side',label:'Side',fmt:v=>badge(v)},
    {key:'forecast_relation',label:'Forecast Relation',fmt:v=>badge(v,v==='WITH_FORECAST'?'good':v==='COUNTER_FORECAST'?'bad':'info')},
    {key:'forecast_route_state',label:'Route State',fmt:v=>badge(v,String(v).includes('HIGH')?'warn':'info')},
    {key:'grade',label:'Grade',fmt:v=>badge(v,v==='A_PLUS'||v==='A'?'good':'wait')},
    {key:'objective_distance_price',label:'Obj Dist',fmt:v=>n(v,2),className:'num'},
    {key:'objective_distance_m15_atr',label:'Obj ATR',fmt:v=>n(v,2),className:'num'},
    {key:'progress_pct',label:'Progress',fmt:v=>pct(v),className:'num'}, {key:'room_m15_atr',label:'Room ATR',fmt:v=>n(v,2),className:'num'},
    {key:'m15_score',label:'M15',fmt:v=>n(v,1),className:'num'}, {key:'m30_score',label:'M30',fmt:v=>n(v,1),className:'num'},
    {key:'h1_score',label:'H1',fmt:v=>n(v,1),className:'num'}, {key:'h4_score',label:'H4',fmt:v=>n(v,1),className:'num'},
    {key:'current_daily_direction',label:'Daily',fmt:v=>badge(v)}, {key:'dbs',label:'DBS',fmt:v=>n(v,1),className:'num'},
    {key:'verdict',label:'Verdict',fmt:v=>badge(v,v==='ENTRY_ALLOWED'?'good':v==='HARD_BLOCK'?'bad':'wait')},
    {key:'rule_source',label:'Rule Source',fmt:v=>v?badge(v,'info'):'â€”'}
  ];
  renderTable($('journeyTable'),annotated,cols,{click:r=>{ $('forensicsId').value=r.evaluation_id; showTab('forensics'); loadForensics(); }});
}

async function loadBlocked(){
  const week=$('blockedWeek')?.value||'';
  const data=await api(`/api/blocked-setups?cutoff_date=${encodeURIComponent(week)}`);
  const recovered=data.filter(x=>x.current_rule==='RECOVERED').length;
  const adverse=data.filter(x=>x.current_rule==='STILL_BLOCKED'&&x.outcome==='ADVERSE_1R_FIRST').length;
  $('blockedCards').innerHTML=[metric('Reviewed',data.length,'Selected week','info'),metric('Recovered',recovered,'Current rules','good'),metric('Still Blocked',data.length-recovered,'Protection retained','warn'),metric('Correct Blocks',adverse,'Adverse-first','good'),metric('Target First',data.filter(x=>x.outcome==='TARGET_FIRST').length,'Observed','info'),metric('Ambiguous',data.filter(x=>x.outcome==='SAME_BAR_AMBIGUOUS').length,'Needs caution','warn')].join('');
  renderTable($('blockedTable'),data,[
    {key:'evaluation_time',label:'Time',fmt:v=>shortT(v)},{key:'side',label:'Side',fmt:v=>badge(v)},{key:'price',label:'Price',fmt:v=>n(v,2),className:'num'},
    {key:'sqs',label:'SQS',fmt:v=>n(v,1),className:'num'},{key:'blocking_gate',label:'Blocking Gate'},{key:'objective_price',label:'Objective',fmt:v=>n(v,2),className:'num'},
    {key:'outcome',label:'Outcome',fmt:v=>badge(v,v==='TARGET_FIRST'?'good':v==='ADVERSE_1R_FIRST'?'bad':'wait')},{key:'mae_r',label:'MAE R',fmt:v=>n(v,2),className:'num'},
    {key:'mfe_r',label:'MFE R',fmt:v=>n(v,2),className:'num'},{key:'current_rule',label:'Current Rule',fmt:v=>badge(v,v==='RECOVERED'?'good':'wait')},{key:'rule_source',label:'Rule Source',fmt:v=>badge(v,'info')}
  ]);
}

async function loadForensics(){
  const id=$('forensicsId').value.trim(), view=$('forensicsView')?.value||'current';
  const qs=new URLSearchParams(); if(id) qs.set('evaluation_id',id); qs.set('view',view);
  const r=await api(`/api/forensics?${qs.toString()}`);
  if(!r.evaluation_id){ $('forensicsHeadline').innerHTML=metric('Forensics','No evaluation found','','bad'); return; }
  $('forensicsId').value=r.evaluation_id;
  $('forensicsHeadline').innerHTML=[
    metric('Evaluation',shortT(r.evaluation_time),r.evaluation_id,'info'),
    metric('Direction',r.direction||'â€”',r.logical_entry_leg_id||'',r.direction==='SELL'?'bad':'good'),
    metric('Grade',r.grade||'â€”',`SQS ${n(r.sqs,1)}`,r.grade==='A'||r.grade==='A_PLUS'?'good':'warn'),
    metric('Verdict',r.verdict||'â€”','',r.verdict==='ENTRY_ALLOWED'?'good':r.verdict==='HARD_BLOCK'?'bad':'warn'),
    metric('Rule Source',r.rule_source||'ORIGINAL',r.engine_view||view,'info'),
    metric('Room',`${n(r.room_m15_atr,2)} ATR`,'M15 room remaining','info'),
    metric('Leg Consumed',pct(r.leg_consumed_pct),'No-chase context',Number(r.leg_consumed_pct)<65?'good':'warn')
  ].join('');
  const chain=r.execution_chain||[];
  $('executionChain').innerHTML=chain.map((step,i)=>`<div class="chain-step"><small>${esc(step.stage||'STAGE')}</small><strong>${esc(step.status||'â€”')}</strong><span>${step.score===null||step.score===undefined?'':`Score ${n(step.score,1)}`}${step.room_m15_atr===null||step.room_m15_atr===undefined?'':` Â· Room ${n(step.room_m15_atr,2)} ATR`}${step.leg_consumed_pct===null||step.leg_consumed_pct===undefined?'':` Â· Consumed ${pct(step.leg_consumed_pct)}`}</span></div>${i<chain.length-1?'<div class="chain-arrow">â†’</div>':''}`).join('')||'<span class="muted">No execution chain available</span>';
  $('stageScores').innerHTML=[
    detail('Stage 1 First Contact',esc(n(r.stage1_first_contact_score,1))),detail('Stage 1 Current',esc(n(r.stage1_current_score,1))),
    detail('Stage 2',esc(n(r.stage2_score,1))),detail('H4 / Stage 3',esc(`${n(r.h4_score,1)} Â· ${r.h4_pass?'PASS':'WAIT'}`)),
    detail('H1 / Stage 4',esc(`${n(r.h1_score,1)} Â· ${r.h1_pass?'PASS':'WAIT'}`)),detail('M30',esc(n(r.m30_score,1))),
    detail('M15',esc(n(r.m15_score,1))),detail('Stage 5',esc(n(r.stage5_score,1))),
    detail('Stage 6',esc(n(r.stage6_score,1))),detail('SQS',esc(n(r.sqs,1)))
  ].join('');
  $('objectiveContext').innerHTML=[
    detail('Objective Price',esc(n(r.objective_price,2))),detail('Objective Type',esc(r.objective_type||'â€”')),
    detail('Objective TF',esc(r.objective_timeframe||'â€”')),detail('Objective Distance',esc(n(r.objective_distance_price,2))),
    detail('Objective ATR',esc(n(r.objective_distance_m15_atr,2))),detail('Daily Direction',badge(r.current_daily_direction)),
    detail('Daily State',badge(r.current_daily_state)),detail('DBS',esc(n(r.dbs,2))),
    detail('Pivot',esc(n(r.daily_pivot,2))),detail('R1 / S1',esc(`${n(r.r1,2)} / ${n(r.s1,2)}`))
  ].join('');
  const tfRows=['m15','m30','h1','h4'].map(tf=>({
    tf:tf.toUpperCase(), close_time:r[`${tf}_close_time`], open:r[`${tf}_open`], high:r[`${tf}_high`], low:r[`${tf}_low`], close:r[`${tf}_close`],
    atr:r[`${tf}_atr14`], e10:r[`${tf}_ema10`], e20:r[`${tf}_ema20`], e50:r[`${tf}_ema50`], e200:r[`${tf}_ema200`], macd:r[`${tf}_macd`], hist:r[`${tf}_macd_hist`]
  }));
  renderTable($('mtfTable'),tfRows,[
    {key:'tf',label:'TF'}, {key:'close_time',label:'Close Time',fmt:v=>shortT(v)},
    {key:'open',label:'Open',fmt:v=>n(v,2),className:'num'}, {key:'high',label:'High',fmt:v=>n(v,2),className:'num'},
    {key:'low',label:'Low',fmt:v=>n(v,2),className:'num'}, {key:'close',label:'Close',fmt:v=>n(v,2),className:'num'},
    {key:'atr',label:'ATR14',fmt:v=>n(v,2),className:'num'}, {key:'e10',label:'EMA10',fmt:v=>n(v,2),className:'num'},
    {key:'e20',label:'EMA20',fmt:v=>n(v,2),className:'num'}, {key:'e50',label:'EMA50',fmt:v=>n(v,2),className:'num'},
    {key:'e200',label:'EMA200',fmt:v=>n(v,2),className:'num'}, {key:'macd',label:'MACD',fmt:v=>n(v,2),className:'num'}, {key:'hist',label:'Hist',fmt:v=>n(v,2),className:'num'}
  ]);
  $('h4Evidence').textContent=JSON.stringify(r.h4_evidence||{},null,2); $('h1Evidence').textContent=JSON.stringify(r.h1_evidence||{},null,2);
}
async function loadOutcomes(){
  const view=$('outcomesView')?.value||'current';
  const data=await api(`/api/outcomes?view=${encodeURIComponent(view)}`); state.outcomes=data;
  const hit=data.filter(x=>x.status==='OBJECTIVE_HIT').length, unresolved=data.filter(x=>x.status==='UNRESOLVED').length;
  const ambiguous=data.filter(x=>x.status==='AMBIGUOUS').length, roots=new Set(data.map(x=>x.root_entry_leg_record_id)).size;
  $('outcomeCards').innerHTML=[
    metric('Executions',data.length,'Phase 6','info'), metric('Objective Hit',hit,'Terminal outcomes','good'),
    metric('Unresolved',unresolved,'Open observation',unresolved?'warn':'good'), metric('Ambiguous',ambiguous,'Same-bar ambiguity',ambiguous?'warn':'good'),
    metric('Distinct Roots',roots,'Lineage roots','info')
  ].join('');
  renderTable($('outcomeTable'),data,[
    {key:'entry_time',label:'Entry Time',fmt:v=>shortT(v)}, {key:'side',label:'Side',fmt:v=>badge(v)},
    {key:'grade',label:'Grade',fmt:v=>badge(v,'good')}, {key:'entry_price',label:'Entry',fmt:v=>n(v,2),className:'num'},
    {key:'objective_price',label:'Objective',fmt:v=>n(v,2),className:'num'}, {key:'objective_type',label:'Objective Type'},
    {key:'generation',label:'Gen',fmt:v=>n(v,0),className:'num'}, {key:'entry_family',label:'Entry Family'},
    {key:'status',label:'Outcome',fmt:v=>badge(v,v==='OBJECTIVE_HIT'?'good':v==='UNRESOLVED'?'wait':'bad')},
    {key:'objective_event_time',label:'Objective Time',fmt:v=>shortT(v)}, {key:'observation_cutoff',label:'Observed To',fmt:v=>shortT(v)},
    {key:'rule_source',label:'Rule Source',fmt:v=>v?badge(v,'info'):'â€”'},
    {key:'logical_thesis_id',label:'Thesis'}, {key:'logical_entry_leg_id',label:'EntryLeg'}
  ]);
}

async function loadOptimizer(){
  const view=$('optimizerView')?.value||'current';
  const o=await api(`/api/optimizer?view=${encodeURIComponent(view)}`);
  $('optimizerCards').innerHTML=[
    metric('Executions',o.execution_count??0,'Current observation set','info'), metric('Resolved',o.resolved_count??0,'Terminal','good'),
    metric('Unresolved',o.unresolved_count??0,'Pending','warn'), metric('Objective Hit',o.objective_hit_count??0,'Observed outcomes','good'),
    metric('Distinct Theses',o.distinct_theses??0,'Sample diversity','info'), metric('Recommendation',o.recommendation_status||'â€”','Advisory only','warn')
  ].join('');
  $('optimizerNote').textContent=o.recommendation_note||'No optimizer recommendation is persisted.';
}
async function safe(name,fn){
  try{ await fn(); }
  catch(err){ console.error(name,err); if(name==='health'){ $('sourceStatus').textContent='ERROR'; $('sourceStatus').className='negative'; } }
}

async function boot(){
  document.querySelectorAll('#tabs button').forEach(b=>b.addEventListener('click',()=>showTab(b.dataset.tab)));
  $('overviewLoad').addEventListener('click',()=>safe('overview',loadOverview));
  $('weeklyLoad').addEventListener('click',()=>safe('weekly',loadWeekly));
  $('outcomesLoad')?.addEventListener('click',()=>safe('outcomes',loadOutcomes));
  $('optimizerLoad')?.addEventListener('click',()=>safe('optimizer',loadOptimizer));
  $('outcomesLoad')?.addEventListener('click',()=>safe('outcomes',loadOutcomes));
  $('optimizerLoad')?.addEventListener('click',()=>safe('optimizer',loadOptimizer));
  $('blockedLoad').addEventListener('click',()=>safe('blocked',loadBlocked));
  $('researchLoad')?.addEventListener('click',()=>safe('research',loadResearch));
  $('overviewWeek').addEventListener('change',()=>{ if($('weeklyWeek')) $('weeklyWeek').value=$('overviewWeek').value; if($('blockedWeek')) $('blockedWeek').value=$('overviewWeek').value; });
  $('weeklyWeek').addEventListener('change',()=>{ if($('overviewWeek')) $('overviewWeek').value=$('weeklyWeek').value; if($('blockedWeek')) $('blockedWeek').value=$('weeklyWeek').value; });
  $('journeyLoad').addEventListener('click',()=>{ if($('researchDate')) $('researchDate').value=$('journeyDate').value; safe('journey',loadJourney); });
  $('journeyView')?.addEventListener('change',()=>safe('journey',loadJourney));
  $('forensicsLoad').addEventListener('click',()=>safe('forensics',loadForensics));
  $('forensicsView')?.addEventListener('change',()=>safe('forensics',loadForensics));
  $('outcomesView')?.addEventListener('change',()=>safe('outcomes',loadOutcomes));
  $('optimizerView')?.addEventListener('change',()=>safe('optimizer',loadOptimizer));
  document.querySelectorAll('[data-refresh="overview"]').forEach(b=>b.addEventListener('click',()=>safe('overview',loadOverview)));
  document.querySelectorAll('[data-refresh="health"]').forEach(b=>b.addEventListener('click',()=>safe('health',loadHealth)));

  await safe('meta',loadMeta);
  await Promise.all([
    safe('health',loadHealth), safe('overview',loadOverview), safe('weekly',loadWeekly), safe('blocked',loadBlocked), safe('research',loadResearch),
    safe('outcomes',loadOutcomes), safe('optimizer',loadOptimizer)
  ]);
  await safe('journey',loadJourney);
  await safe('forensics',loadForensics);
  setInterval(()=>{ safe('health',loadHealth); safe('overview',loadOverview); },60000);
}

document.addEventListener('DOMContentLoaded',boot);
