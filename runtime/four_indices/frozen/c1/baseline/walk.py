"""N01 fixed chronological detector and separate outcome evaluation.
python walk.py --fixture
python walk.py --run       # requires SEAL.json matching code/protocol/config
Native broker timestamps are intentionally timezone-naive labels.
"""
from pathlib import Path
import argparse, json, hashlib, zipfile, importlib.util, copy
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parent
C=json.loads((ROOT/'config.json').read_text())

def hashfile(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp(x):return str(pd.Timestamp(x))
def wilder(s,n=14):
    a=s.to_numpy(float);out=np.full(len(a),np.nan);ids=np.flatnonzero(np.isfinite(a))
    if len(ids)<n:return pd.Series(out,index=s.index)
    k=ids[n-1];out[k]=a[ids[:n]].mean()
    for i in range(k+1,len(a)):out[i]=(out[i-1]*(n-1)+a[i])/n
    return pd.Series(out,index=s.index)

def load(source):
    assert hashfile(source)==C['source_sha256']
    f={}
    with zipfile.ZipFile(source) as z:
        for tf,mins in [('M1',1),('M15',15),('H1',60),('D1',1440)]:
            d=pd.read_csv(z.open(f'data/WS30.pro_{tf}_2026_Jan_Nov.csv'))
            d=d[d.confirmed_by_later_bar.eq(1)].copy()
            d['t']=pd.to_datetime(d.broker_time);d['end']=d.t+pd.Timedelta(minutes=mins)
            assert d.t.is_unique and d.t.is_monotonic_increasing
            f[tf]=d.reset_index(drop=True)
    h=f['H1'];tr=pd.concat([h.high-h.low,(h.high-h.close.shift()).abs(),(h.low-h.close.shift()).abs()],axis=1).max(axis=1)
    h['A']=wilder(tr,C['ATR_period'])
    ref=f['D1'][['t','end','high']].rename(columns={'t':'ref_day','end':'ref_known','high':'R'})
    h=pd.merge_asof(h,ref,left_on='t',right_on='ref_known',direction='backward');h['idx']=np.arange(len(h));f['H1']=h
    g=f['M1'].groupby(f['M1'].t.dt.floor('h')).agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),tick_volume=('tick_volume','sum'))
    q=h.set_index('t').join(g,rsuffix='_m1');assert q.open_m1.notna().all()
    for c in ['open','high','low','close','tick_volume']:assert ((q[c]-q[c+'_m1']).abs()<1e-8).all()
    return f

def detect(h,journal=False):
    episodes=[];active=[];events=[];signals=[];raw=[];first=[];seen=set();day=None;day_lows=[];day_closes=[];bars=[];prev=None
    def emit(e,r,event,**kw):events.append({'episode_id':e.get('id',''),'bar_open':stamp(r.t),'known_at':stamp(r.end),'event':event,**kw})
    for r in h.itertuples(index=False):
        i=r.idx
        for e in list(active):
            if e['state']=='attempt':
                e['peak']=max(e['peak'],r.high)
                if r.close<e['R']:
                    e.update(state='base',failure_idx=i,failure_time=stamp(r.end),Q=e['peak'],pullback_min=float(r.low))
                    emit(e,r,'first_failure',Q=e['Q'],B=e['B'])
                    if r.low<=e['B']:e['veto_floor']=True;emit(e,r,'initial_floor_lost')
                elif i-e['seed_idx']>=C['failure_window_H1']:
                    e['state']='expired_without_failure';emit(e,r,e['state']);active.remove(e)
            elif e['state']=='base':
                e['pullback_min']=min(e['pullback_min'],float(r.low))
                if r.low<=e['B'] and not e['veto_floor']:e['veto_floor']=True;emit(e,r,'initial_floor_lost')
                if 'P' in e and r.low<=e['P'] and not e['veto_base']:e['veto_base']=True;emit(e,r,'base_floor_lost',P=e['P'])
                if r.close>e['Q']:
                    reasons=[]
                    if e['veto_floor']:reasons.append('initial_floor_lost')
                    if 'recovery_idx' not in e:reasons.append('no_recovery_confirmation')
                    if 'defense_idx' not in e:reasons.append('no_shallower_pullback')
                    if e['veto_base']:reasons.append('higher_base_lost')
                    e.update(state='acceptance',raw_idx=i,raw_time=stamp(r.end),base_eligible=not reasons,base_reasons=';'.join(reasons))
                    row={'episode_id':e['id'],'signal_idx':i,'signal_time':stamp(r.end),'seed_time':e['seed_time'],'kind':'RAW_SECOND','R':e['R'],'B':e['B'],'Q':e['Q'],'P':e.get('P',np.nan),'base_eligible':not reasons,'base_reasons':e['base_reasons']}
                    raw.append(row);emit(e,r,'raw_second_break',base_eligible=not reasons,reasons=e['base_reasons'],Q=e['Q'])
                else:
                    if not e['veto_floor'] and 'recovery_idx' not in e and prev is not None and r.close>prev.high:
                        e.update(recovery_idx=i,recovery_time=stamp(r.end),P=e['pullback_min'])
                        emit(e,r,'higher_base_recovered',P=e['P'])
                    elif 'recovery_idx' in e and not e['veto_floor'] and not e['veto_base'] and 'defense_idx' not in e and r.close<prev.close and r.low>e['P']:
                        e.update(defense_idx=i,defense_time=stamp(r.end));emit(e,r,'higher_base_defended',P=e['P'],low=float(r.low))
                    if i-e['failure_idx']>=C['second_break_window_H1']:
                        e['state']='expired_without_second_break';emit(e,r,e['state']);active.remove(e)
            elif e['state']=='acceptance':
                hold=bool(r.low>e['Q']);e.update(accept_idx=i,accept_time=stamp(r.end),acceptance_holds=hold)
                if e['base_eligible'] and hold:
                    e['state']='qualified';row={'episode_id':e['id'],'signal_idx':i,'signal_time':stamp(r.end),'seed_time':e['seed_time'],'kind':'N01','R':e['R'],'B':e['B'],'Q':e['Q'],'P':e['P']}
                    signals.append(row);emit(e,r,'accepted_signal',Q=e['Q'],low=float(r.low))
                else:
                    e['state']='rejected';e['rejection_reasons']=e['base_reasons']+(';' if e['base_reasons'] and not hold else '')+('acceptance_low_not_above_ceiling' if not hold else '')
                    emit(e,r,'second_break_rejected',reasons=e['rejection_reasons'],acceptance_holds=hold)
                active.remove(e)
        current=r.t.date()
        if current!=day:day=current;day_lows=[];day_closes=[]
        if pd.notna(r.ref_day):
            key=stamp(r.ref_day)
            if key not in seen and r.close>r.R:
                seen.add(key)
                if not any(c<=r.R for c in day_closes):
                    emit({},r,'first_break_without_prior_same_day_recovery',ref_day=key,R=float(r.R))
                else:
                    e={'id':f'N01_{len(episodes)+1:03d}','ref_day':key,'R':float(r.R),'B':float(min(day_lows+[r.low])),
                       'seed_idx':i,'seed_time':stamp(r.end),'seed_bar_open':stamp(r.t),'peak':float(r.high),'state':'attempt','veto_floor':False,'veto_base':False}
                    episodes.append(e);active.append(e);emit(e,r,'first_break',R=e['R'],B=e['B'])
                    first.append({'episode_id':e['id'],'signal_idx':i,'signal_time':stamp(r.end),'seed_time':stamp(r.end),'kind':'FIRST_BREAK','R':e['R'],'B':e['B']})
        day_lows.append(float(r.low));day_closes.append(float(r.close));prev=r
        if journal:
            state=[{k:e[k] for k in ['id','state','R','B','Q','P','veto_floor','veto_base'] if k in e} for e in active]
            bars.append({'bar_open':stamp(r.t),'known_at':stamp(r.end),'open':r.open,'high':r.high,'low':r.low,'close':r.close,'A_at_close':r.A,
              'reference_known_at':stamp(r.ref_known) if pd.notna(r.ref_known) else '', 'prior_D1_high':r.R,
              'active_after_close':json.dumps(state,separators=(',',':')),'events_this_close':';'.join(x['event'] for x in events if x['known_at']==stamp(r.end))})
    return {'episodes':episodes,'events':events,'signals':signals,'raw':raw,'first':first,'bars':bars}

def fixture(f):
    h=f['H1'];res=detect(h[(h.t>='2026-11-09')&(h.t<'2026-11-10')])
    assert len(res['signals'])==1
    s=res['signals'][0];e=next(x for x in res['episodes'] if x['id']==s['episode_id'])
    expected={'seed_time':'2026-11-09 06:00:00','failure_time':'2026-11-09 08:00:00','recovery_time':'2026-11-09 11:00:00','defense_time':'2026-11-09 12:00:00','raw_time':'2026-11-09 13:00:00','accept_time':'2026-11-09 14:00:00','R':51669.,'B':51233.5,'Q':51719.5,'P':51411.2}
    for k,v in expected.items():assert e[k]==v,(k,e.get(k),v)
    return {'discovery_fixture':'PASS','expected_anchors':expected,'outcomes_evaluated':False}

def prefix_checks(h,full):
    cuts=list(pd.date_range('2026-02-01','2026-11-01',freq='MS'))+[pd.Timestamp('2026-11-09 13:00'),pd.Timestamp('2026-11-09 14:00')]
    rows=[]
    for cut in cuts:
        p=detect(h[h.end<=cut]);want=[e for e in full['events'] if pd.Timestamp(e['known_at'])<=cut]
        assert p['events']==want,cut
        rows.append({'cutoff':stamp(cut),'events':len(want),'prefix_equal':True})
    changed=h.copy();mask=changed.t>=pd.Timestamp('2026-07-01')
    for c in ['open','high','low','close']:changed.loc[mask,c]+=100000
    alt=detect(changed);old=[x for x in full['events'] if pd.Timestamp(x['known_at'])<pd.Timestamp('2026-07-01')];new=[x for x in alt['events'] if pd.Timestamp(x['known_at'])<pd.Timestamp('2026-07-01')]
    assert old==new
    return {'monthly_and_discovery_prefixes':rows,'future_price_perturbation_before_July_unchanged':True}

def evaluate(row,f,scheduled):
    h=f['H1'];m=f['M1'];m15=f['M15'];si=int(row['signal_idx']);A=float(h.iloc[si].A);when=pd.Timestamp(row['signal_time']);mi=int(m15.t.searchsorted(when))
    base=copy.deepcopy(row);base['A']=A
    if mi>=len(m15) or not np.isfinite(A):
        return [{**base,'status':'CENSORED','reason':'no_entry_or_ATR','target_A':tp,'management':mg} for tp in C['targets_ATR'] for mg in C['management_profiles']]
    entry=m15.iloc[mi];E=float(entry.open);et=entry.t;j=int(h.t.searchsorted(et));last=j+C['horizon_H1']-1;complete=last<len(h)
    hs=h.iloc[j:min(last+1,len(h))];end=h.iloc[last].end if complete else h.end.iloc[-1]
    d=m[(m.t>=et)&(m.t<end)];terminal=float(hs.close.iloc[-1]) if len(hs) else E
    actual=stamp(m.iloc[int(m.t.searchsorted(et))].t) if m.t.searchsorted(et)<len(m) else ''
    disc_start=pd.Timestamp(C['discovery_start']);disc_end=pd.Timestamp(C['discovery_end'])
    overlap=pd.Timestamp(row['seed_time'])<disc_end and end>disc_start
    base.update(entry_time=stamp(et),first_M1_quote_time=actual,entry=E,horizon_end=stamp(end),horizon_complete=bool(complete),
       discovery_overlap=bool(overlap),cohort='discovery_overlap' if overlap else 'outside_discovery',month=et.strftime('%Y-%m'),
       stop_price=E-3*A,target2_price=E+2*A,target3_price=E+3*A,entry_spread_points=int(entry.spread),
       MFE_A=float((d.high.max()-E)/A) if len(d) else np.nan,MAE_A=float(max(0,(E-d.low.min())/A)) if len(d) else np.nan,
       terminal_A=(terminal-E)/A)
    count=0;times=[]
    for rr in hs.itertuples(index=False):
        count=count+1 if rr.close>=E+A else 0
        if count>=2:times.append(stamp(rr.end))
    out=[]
    for mg in C['management_profiles']:
        for tp in C['targets_ATR']:
            score=scheduled(d,E,A,1,tp,times if mg=='BE_H1_2C' else [],terminal,end)
            paths=score.pop('paths');exit_time=pd.Timestamp(score['exit_time_last']);costrow=d[d.t<=exit_time].iloc[-1] if len(d) else entry
            spread_cost=C['point_size']*(float(entry.spread)+float(costrow.spread))/2/(3*A)
            out.append({**base,**score,'provisional_status':score['status'],'status':score['status'] if complete else 'CENSORED',
              'target_A':tp,'management':mg,'BE_qualification_times':';'.join(times) if mg=='BE_H1_2C' else '',
              'score_R_min':score['score_R_min'] if complete else np.nan,'score_R_max':score['score_R_max'] if complete else np.nan,
              'gap_adjusted_R_min':score['gap_adjusted_R_min'] if complete else np.nan,'gap_adjusted_R_max':score['gap_adjusted_R_max'] if complete else np.nan,
              'spread_proxy_cost_R':spread_cost,'spread_proxy_net_R_min':score['gap_adjusted_R_min']-spread_cost if complete else np.nan,
              'paths_json':json.dumps(paths)})
    return out

def summaries(out):
    rows=[]
    for cohort in ['all','outside_discovery','discovery_overlap']:
        d=out if cohort=='all' else out[out.cohort.eq(cohort)]
        for (kind,mg,tp),q in d.groupby(['kind','management','target_A']):
            vc=q.status.value_counts();resolved=q.status.isin(['WIN','LOSS']);sc=q.status.ne('CENSORED')
            row={'cohort':cohort,'kind':kind,'management':mg,'target_A':tp,'signals':len(q)}
            for status in ['WIN','LOSS','BE','TIMEOUT','AMBIGUOUS','CENSORED']:row[status]=int(vc.get(status,0))
            row.update(win_pct_all=100*vc.get('WIN',0)/len(q),win_pct_TP_SL_only=100*vc.get('WIN',0)/resolved.sum() if resolved.sum() else np.nan,
              gross_R_min=q.score_R_min.sum(min_count=1),gross_R_max=q.score_R_max.sum(min_count=1),gap_adjusted_R_min=q.gap_adjusted_R_min.sum(min_count=1),
              spread_proxy_R_min=q.spread_proxy_net_R_min.sum(min_count=1),mean_R_min=q.score_R_min.mean())
            rows.append(row)
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=ROOT/'source/WS30pro_MT5_Jan_Nov_2026.zip');ap.add_argument('--fixture',action='store_true');ap.add_argument('--run',action='store_true');args=ap.parse_args()
    f=load(args.source)
    if args.fixture:print(json.dumps(fixture(f),indent=2));return
    assert args.run
    seal=json.loads((ROOT/'SEAL.json').read_text())
    for name,sha in seal['pre_run_file_sha256'].items():assert hashfile(ROOT/name)==sha,('seal mismatch',name)
    result=detect(f['H1'],journal=True);checks=prefix_checks(f['H1'],result);checks['fixture']=fixture(f)
    checks['source_sha256']=hashfile(args.source);checks['M1_H1_exact_match']=True;checks['H1_bars']=len(f['H1']);checks['first_H1']=stamp(f['H1'].t.iloc[0]);checks['last_confirmed_H1_close']=stamp(f['H1'].end.iloc[-1])
    spec=importlib.util.spec_from_file_location('be',ROOT/'be_two_close.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    outputs=[]
    for collection in ['first','raw','signals']:
        for row in result[collection]:outputs.extend(evaluate(row,f,mod.scheduled))
    out=pd.DataFrame(outputs);ep=pd.DataFrame(result['episodes'])
    # Retrospective filter attribution is separate from the signal detector.
    final=ep.set_index('id')
    out['eventual_N01_qualified']=out.episode_id.map(final.state).eq('qualified')
    out['rejection_reasons']=out.episode_id.map(final.get('rejection_reasons',pd.Series(dtype=str)))
    raw=out[out.kind.eq('RAW_SECOND')].copy();raw['base_eligible']=raw.episode_id.map(final.base_eligible)
    raw['acceptance_holds']=raw.episode_id.map(final.acceptance_holds)
    results=ROOT/'results';results.mkdir(exist_ok=True)
    for name,rows in [('episodes',result['episodes']),('events',result['events']),('H1_chronological_journal',result['bars']),('signals',result['signals'])]:pd.DataFrame(rows).to_csv(results/f'{name}.csv',index=False)
    out.to_csv(results/'all_outcomes.csv',index=False);raw.to_csv(results/'raw_second_breakouts.csv',index=False)
    primary=out[out.kind.eq('N01')].copy();primary.to_csv(results/'N01_outcomes.csv',index=False)
    unique=primary.drop_duplicates('episode_id').sort_values('entry_time').copy();unique['overlaps_prior_horizon']=False
    for idx,row in unique.iterrows():unique.loc[idx,'overlaps_prior_horizon']=((unique.entry_time<row.entry_time)&(unique.horizon_end>row.entry_time)).any()
    unique.to_csv(results/'N01_entries.csv',index=False)
    rejected=raw[~raw.eventual_N01_qualified & raw.management.eq('NO_BE') & raw.status.eq('WIN')]
    rejected.to_csv(results/'rejected_second_breakout_winners.csv',index=False)
    summaries(out).to_csv(results/'summary.csv',index=False)
    months=pd.period_range('2026-01','2026-11',freq='M').astype(str);monthly=[]
    for month in months:
        for mg in C['management_profiles']:
            for tp in C['targets_ATR']:
                q=primary[primary.month.eq(month)&primary.management.eq(mg)&primary.target_A.eq(tp)];vc=q.status.value_counts()
                monthly.append({'month':month,'management':mg,'target_A':tp,'signals':len(q),**{k:int(vc.get(k,0)) for k in ['WIN','LOSS','BE','TIMEOUT','AMBIGUOUS','CENSORED']},'gross_R_min':q.score_R_min.sum()})
    pd.DataFrame(monthly).to_csv(results/'monthly.csv',index=False)
    (results/'causality_and_data_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps({'counts':{k:len(result[k]) for k in ['episodes','events','signals','raw','first','bars']},'end_states':ep.state.value_counts().to_dict(),'checks':'PASS'},indent=2))
    print(summaries(out).query("kind == 'N01'").to_string(index=False))

if __name__=='__main__':main()
