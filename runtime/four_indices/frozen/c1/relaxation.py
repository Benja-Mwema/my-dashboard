"""N01 exploratory relaxations. Decision code never uses outcome columns."""
from pathlib import Path
import importlib.util,json,hashlib,copy,argparse
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parent
def module(name,file):
    s=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=module('original_n01',ROOT/'baseline/walk.py');be=module('original_be',ROOT/'baseline/be_two_close.py')
DEFAULT={'branch':'second','initial_floor':True,'secondary_floor':True,'recovery':True,'defense':True,'floor_mode':'low','accept':'low','accept_window':1,'second_window':24}

def menu():
    defs=[
      ('S0','Original strict N01',{}),
      ('R1','Remove separate shallower pullback',{'defense':False}),
      ('R2','Use closes for both floor guards',{'floor_mode':'close'}),
      ('R3','Remove initial-floor veto',{'initial_floor':False}),
      ('R4','Remove secondary-base veto',{'secondary_floor':False}),
      ('R5','Next close above ceiling, allow wick below',{'accept':'close'}),
      ('R6','Allow 48 H1 bars for second break',{'second_window':48}),
      ('R7','Enter raw second break after base checks',{'accept':'none'}),
      ('C1','No extra pullback; close floor guards; close acceptance',{'defense':False,'floor_mode':'close','accept':'close'}),
      ('C2','Keep initial wick floor only; close acceptance',{'recovery':False,'defense':False,'secondary_floor':False,'accept':'close'}),
      ('C3','Keep initial closing floor only; close acceptance',{'recovery':False,'defense':False,'secondary_floor':False,'floor_mode':'close','accept':'close'}),
      ('C4','No base sequence; next full range above ceiling',{'initial_floor':False,'secondary_floor':False,'recovery':False,'defense':False}),
      ('C5','No base sequence; next close above ceiling',{'initial_floor':False,'secondary_floor':False,'recovery':False,'defense':False,'accept':'close'}),
      ('C6','C5 with up to 3 H1 bars to accept/reclaim',{'initial_floor':False,'secondary_floor':False,'recovery':False,'defense':False,'accept':'close','accept_window':3}),
      ('C7','C5 with 48 H1 second-break deadline',{'initial_floor':False,'secondary_floor':False,'recovery':False,'defense':False,'accept':'close','second_window':48}),
      ('C8','C5 with 48 H1 deadline and 3-bar acceptance',{'initial_floor':False,'secondary_floor':False,'recovery':False,'defense':False,'accept':'close','second_window':48,'accept_window':3}),
      ('F0','Initial breakout, no acceptance wait',{'branch':'first','accept':'none'}),
      ('F1','Initial breakout, next full H1 range above daily high',{'branch':'first','accept':'low'}),
      ('F2','Initial breakout, next H1 close above daily high',{'branch':'first','accept':'close'})]
    return [{**DEFAULT,**changes,'id':vid,'label':label} for vid,label,changes in defs]

def scan(h,seeds,v):
    """Each seed and all examined bars are already closed by decision time.
    A historical loop can stop at any prefix without changing prior entries.
    """
    sig=[];cases=[];n=len(h)
    for seed in seeds:
        i=int(seed['signal_idx']);R=float(seed['R']);B=float(seed['B']);eid=seed['episode_id']
        if i>=n:continue
        e={'episode_id':eid,'variant':v['id'],'seed_idx':i,'seed_time':seed['seed_time'],'R':R,'B':B,'stage':'await_failure','reason':''}
        Q=R;raw=None;recovered=False;defended=False;P=None;badB=False;badP=False
        if v['branch']=='first':raw=i
        else:
            Q=float(h.iloc[i].high);failure=None
            for k in range(i+1,min(n,i+25)):
                r=h.iloc[k];Q=max(Q,float(r.high))
                if r.close<R:failure=k;break
            if failure is None:
                e.update(stage='no_failure' if i+24<n else 'pending_failure');cases.append(e);continue
            e.update(failure_idx=failure,failure_time=base.stamp(h.iloc[failure].end),Q=Q)
            fr=h.iloc[failure];low=float(fr.low);badB=float(fr[v['floor_mode']])<=B
            for k in range(failure+1,min(n,failure+v['second_window']+1)):
                r=h.iloc[k];prev=h.iloc[k-1];low=min(low,float(r.low))
                badB|=float(r[v['floor_mode']])<=B
                if P is not None:badP|=float(r[v['floor_mode']])<=P
                if r.close>Q:raw=k;break
                goodB=not v['initial_floor'] or not badB;goodP=not v['secondary_floor'] or not badP
                if goodB and not recovered and r.close>prev.high:
                    recovered=True;P=low;e.update(recovery_idx=k,P=P)
                elif recovered and goodB and goodP and not defended and r.close<prev.close and float(r[v['floor_mode']])>P:
                    defended=True;e['defense_idx']=k
            if raw is None:
                e.update(stage='no_second_break' if failure+v['second_window']<n else 'pending_second_break');cases.append(e);continue
            e.update(raw_idx=raw,raw_time=base.stamp(h.iloc[raw].end),Q=Q,P=P,bad_initial_floor=bool(badB),bad_secondary_floor=bool(badP))
            reasons=[]
            if v['initial_floor'] and badB:reasons.append('initial_floor')
            if v['secondary_floor'] and badP:reasons.append('secondary_floor')
            if v['recovery'] and not recovered:reasons.append('no_prior_recovery')
            if v['defense'] and not defended:reasons.append('no_shallower_pullback')
            if reasons:e.update(stage='base_rejected',reason=';'.join(reasons));cases.append(e);continue
        confirmed=None
        if v['accept']=='none':confirmed=raw
        else:
            for k in range(raw+1,min(n,raw+1+v['accept_window'])):
                if float(h.iloc[k][v['accept']])>Q:confirmed=k;break
        if confirmed is None:
            e.update(stage='acceptance_rejected' if raw+v['accept_window']<n else 'pending_acceptance');cases.append(e);continue
        row={'episode_id':eid,'signal_idx':confirmed,'signal_time':base.stamp(h.iloc[confirmed].end),'seed_time':seed['seed_time'],
          'kind':v['id'],'variant':v['id'],'R':R,'B':B,'Q':Q,'P':P,'signal_key':f'{eid}@{confirmed}'}
        sig.append(row);e.update(stage='signal',signal_idx=confirmed,signal_time=row['signal_time']);cases.append(e)
    return sig,cases

def summarize(out,signals,original):
    rows=[]
    for vid,d in out.groupby('variant',sort=False):
        keys=set(signals[signals.variant.eq(vid)].signal_key);exact=keys&original
        for scope in ['all','outside_discovery','Jan-Jun','Jul-Nov']:
            subset=d if scope=='all' else d[~d.discovery_overlap] if scope=='outside_discovery' else d[d.month<'2026-07'] if scope=='Jan-Jun' else d[d.month>='2026-07']
            for (mg,tp),q in subset.groupby(['management','target_A']):
                counts=q.status.value_counts();resolved=q.status.isin(['WIN','LOSS']).sum();added=q[~q.signal_key.isin(original)]
                rows.append({'variant':vid,'scope':scope,'management':mg,'target_A':tp,'entries':len(q),'recoveries_covered':q.episode_id.nunique(),
                  'exact_original_entries_retained':len(exact),'all_original_entries_preserved':len(exact)==len(original),
                  **{s:int(counts.get(s,0)) for s in ['WIN','LOSS','BE','TIMEOUT','AMBIGUOUS','CENSORED']},
                  'wins_pct_all':100*counts.get('WIN',0)/len(q),'wins_pct_TP_SL_only':100*counts.get('WIN',0)/resolved if resolved else np.nan,
                  'gross_R_min':q.score_R_min.sum(min_count=1),'gross_R_max':q.score_R_max.sum(min_count=1),
                  'gap_R_min':q.gap_adjusted_R_min.sum(min_count=1),'spread_proxy_R_min':q.spread_proxy_net_R_min.sum(min_count=1),'mean_R':q.score_R_min.mean(),
                  'added_entries_vs_exact_baseline':len(added),'added_wins':int(added.status.eq('WIN').sum()),'added_losses':int(added.status.eq('LOSS').sum()),
                  'added_BE':int(added.status.eq('BE').sum()),'added_timeouts':int(added.status.eq('TIMEOUT').sum()),'added_gross_R':added.score_R_min.sum()})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare',action='store_true');ap.add_argument('--run',action='store_true');ap.add_argument('--source',type=Path,default=ROOT/'source/WS30pro_MT5_Jan_Nov_2026.zip');a=ap.parse_args()
    if a.prepare:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        (ROOT/'variants.json').write_text(json.dumps(menu(),indent=2)+'\n')
        seal={'registered_at':datetime.now(ZoneInfo('Africa/Kampala')).isoformat(),'in_sample_exploration':True,'files':{f:base.hashfile(ROOT/f) for f in ['study.py','variants.json','EXPERIMENT_PLAN.md','baseline/walk.py','baseline/config.json','baseline/be_two_close.py']}}
        (ROOT/'EXPERIMENT_RECORD.json').write_text(json.dumps(seal,indent=2)+'\n');print('Experiment menu recorded');return
    assert a.run
    for fn,sha in json.loads((ROOT/'EXPERIMENT_RECORD.json').read_text())['files'].items():assert base.hashfile(ROOT/fn)==sha
    f=base.load(a.source);h=f['H1'];original=base.detect(h);seeds=original['first'];assert len(seeds)==80
    origkeys={f"{r['episode_id']}@{r['signal_idx']}" for r in original['signals']};assert len(origkeys)==3
    variants=json.loads((ROOT/'variants.json').read_text());alls=[];allc=[]
    for v in variants:
        sig,cases=scan(h,seeds,v);alls.extend(sig);allc.extend(cases)
        if v['id']=='S0':assert {r['signal_key'] for r in sig}==origkeys
    # Prefixes include each completed calendar month and the known discovery transitions.
    cuts=list(pd.date_range('2026-02-01','2026-11-01',freq='MS'))+[pd.Timestamp('2026-11-09 13:00'),pd.Timestamp('2026-11-09 14:00')]
    for cut in cuts:
        hh=h[h.end<=cut];ss=base.detect(hh)['first']
        for v in variants:
            got,_=scan(hh,ss,v);want=[s for s in alls if s['variant']==v['id'] and pd.Timestamp(s['signal_time'])<=cut]
            assert [s['signal_key'] for s in got]==[s['signal_key'] for s in want],(cut,v['id'])
    unions=[('U1',['S0','F1']),('U2',['S0','F2']),('U3',['C5','F1']),('U4',['C5','F2'])]
    for name,parts in unions:
        merged={}
        for r in alls:
            if r['variant'] in parts:
                key=r['signal_key']
                if key not in merged:merged[key]={**r,'variant':name,'kind':name,'components':r['variant']}
                else:merged[key]['components']+=';'+r['variant']
        alls.extend(merged.values())
    signals=pd.DataFrame(alls);cases=pd.DataFrame(allc);out=[];cache={}
    for r in alls:
        key=r['signal_key']
        if key not in cache:cache[key]=base.evaluate(r,f,be.scheduled)
        for outcome in cache[key]:out.append({**outcome,**r})
    results=ROOT/'results';results.mkdir(exist_ok=True)
    outputs=pd.DataFrame(out)
    # Exact timestamp retention must also retain identical entry, ATR and outcomes.
    for key in origkeys:
        q=outputs[outputs.signal_key.eq(key)]
        for _,g in q.groupby(['management','target_A']):
            for col in ['entry','A','status','exit_time_first','score_R_min']:assert g[col].nunique(dropna=False)==1,(key,col)
    signals.to_csv(results/'all_variant_signals.csv',index=False);cases.to_csv(results/'all_80_recoveries_by_variant.csv',index=False)
    outputs.to_csv(results/'all_variant_outcomes.csv',index=False);summary=summarize(outputs,signals,origkeys);summary.to_csv(results/'summary.csv',index=False)
    preservation=[]
    for vid,g in signals.groupby('variant',sort=False):
        keys=set(g.signal_key);episodes=set(g.episode_id);preservation.append({'variant':vid,'entries':len(keys),'recoveries':len(episodes),'multiple_entry_recoveries':int(g.groupby('episode_id').size().gt(1).sum()),'original_retained':len(keys&origkeys),'removed_original_keys':';'.join(sorted(origkeys-keys))})
    pd.DataFrame(preservation).to_csv(results/'preservation_and_coverage.csv',index=False)
    # Every baseline comparator is reproduced rather than silently replaced.
    check={'initial_recoveries':len(seeds),'variants':len(variants),'causal_module_unions':len(unions),'prefix_checks':len(cuts)*len(variants),
      'baseline_exact_signal_reproduction':True,'exact_entry_price_ATR_exit_preservation':True,'source_sha256':base.hashfile(a.source),
      'last_confirmed_H1_close':str(h.end.iloc[-1]),'unique_entry_evaluations':len(cache)}
    (results/'CHECKS.json').write_text(json.dumps(check,indent=2)+'\n')
    print(json.dumps(check,indent=2));print(summary[(summary.scope=='all')&(summary.management=='BE_H1_2C')][['variant','target_A','entries','recoveries_covered','exact_original_entries_retained','WIN','LOSS','BE','TIMEOUT','gross_R_min','spread_proxy_R_min']].to_string(index=False))

if __name__=='__main__':main()
