"""USDJPY H1 EMA10/20/50 E1 v0.2, frozen research baseline.
Run: python formula.py  (requires numpy). No orders or external mutations.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import json, hashlib, csv
import numpy as np

P = Path(__file__).resolve().parent
CFG = json.loads((P/'formula_config.json').read_text())
STEP = CFG['bar_seconds']
def label(t): return datetime.fromtimestamp(int(t),timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
def epoch(s): return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,obj): (P/name).write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')
def csvfile(name,rows):
    if not rows: (P/name).write_text('',encoding='utf-8'); return
    with (P/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def ema(v,n):
    out=np.empty(len(v)); out[0]=v[0]; alpha=2/(n+1)
    for i in range(1,len(v)): out[i]=alpha*v[i]+(1-alpha)*out[i-1]
    return out

def indicators(raw):
    t=raw[:,0].astype(np.int64); o,h,l,c=(raw[:,k] for k in [1,2,3,4])
    e=np.stack([ema(c,k) for k in CFG['ema_periods']],axis=1)
    tr=np.maximum(h-l,np.maximum(abs(h-np.r_[c[0],c[:-1]]),abs(l-np.r_[c[0],c[:-1]])))
    atr=np.empty(len(t)); atr[0]=tr[0]; n=CFG['atr_period']
    for i in range(1,len(t)): atr[i]=tr[i]/n+atr[i-1]*(n-1)/n
    width=np.ptp(e,axis=1)
    wa=np.divide(width,atr,out=np.full(len(t),np.inf),where=atr>0)
    qual=(wa<=CFG['cluster_max_width_atr'])&(atr>0)
    side=np.where((e[:,0]>e[:,1])&(e[:,1]>e[:,2]),1,np.where((e[:,0]<e[:,1])&(e[:,1]<e[:,2]),-1,0))
    return dict(t=t,o=o,h=h,l=l,c=c,e=e,atr=atr,width=width,wa=wa,qual=qual,side=side,
                gap=np.r_[False,np.diff(t)!=STEP],span=h-l)

def scan(v):
    """Streaming episode state: at most one first-passing formation per episode."""
    t,o,h,l,c,e,atr,width,wa,qual,side,gap,span=[v[k] for k in ['t','o','h','l','c','e','atr','width','wa','qual','side','gap','span']]
    active=False; cycle=None; cid=0; events=[]; episodes=[]; lag=CFG['slope_lag_bars']
    for i in range(len(t)):
        first_out=False
        if gap[i]: active=False
        if qual[i]:
            if not active:
                cid+=1; cycle={'id':cid,'start':i,'end':i,'count':0,'min_width_atr':float(wa[i]),'consumed':False}
                episodes.append(cycle); active=True
            cycle['count']+=1; cycle['end']=i; cycle['min_width_atr']=min(cycle['min_width_atr'],float(wa[i]))
        elif active: first_out=True; active=False
        if cycle is None or not (active or first_out) or cycle['consumed']: continue
        sg=int(side[i]); count=cycle['count']
        if not sg or i<lag or t[i]-t[i-lag]!=lag*STEP or span[i]<=0 or atr[i]<=0: continue
        dc=sum(sg*(c[k]-c[k-1])>0 for k in range(i-lag+1,i+1))
        lower=sum(h[k]<h[k-1] and l[k]<l[k-1] for k in range(i-lag+1,i+1))
        low,high=CFG['buy_cluster_bars'] if sg==1 else CFG['sell_cluster_bars']
        passed=(low<=count<=high and sg*(c[i]-e[i,0])>0
          and sg*(e[i,0]-e[i-lag,0])>0 and sg*(e[i,1]-e[i-lag,1])>0
          and sg*(e[i,2]-e[i-lag,2])>=0 and width[i]>width[i-1]
          and sg*(c[i]-o[i])>0 and sg*(2*c[i]-h[i]-l[i])>=0
          and dc>=CFG['progression_min_count'] and (sg==1 or lower>=CFG['progression_min_count']))
        if passed:
            events.append({'cycle_id':cid,'index':i,'side':sg,'known_persistence':count,
              'min_width_so_far':cycle['min_width_atr'],'cycle_start':cycle['start'],'first_outside':bool(first_out)})
            cycle['consumed']=True
    return events,episodes

def independent(v):
    """Independent run-based implementation, inherited from the M30 verification approach."""
    ans=[]; i=0; lag=CFG['slope_lag_bars']
    while i<len(v['t']):
        if not v['qual'][i]: i+=1; continue
        a=b=i
        while b+1<len(v['t']) and v['qual'][b+1] and not v['gap'][b+1]: b+=1
        last=b+1 if b+1<len(v['t']) and not v['gap'][b+1] else b
        for k in range(a,last+1):
            sg=int(v['side'][k]); count=min(k,b)-a+1
            if not sg or k<lag or v['t'][k]-v['t'][k-lag]!=lag*STEP: continue
            low,high=CFG['buy_cluster_bars'] if sg==1 else CFG['sell_cluster_bars']
            if not low<=count<=high: continue
            o,h,l,c=[v[z][k] for z in ['o','h','l','c']]
            if h<=l or sg*(c-o)<=0 or sg*(2*c-h-l)<0: continue
            if sg*(c-v['e'][k,0])<=0 or v['width'][k]<=v['width'][k-1]: continue
            if np.any(sg*(v['e'][k,:2]-v['e'][k-lag,:2])<=0) or sg*(v['e'][k,2]-v['e'][k-lag,2])<0: continue
            if sum(sg*(v['c'][j]-v['c'][j-1])>0 for j in range(k-lag+1,k+1))<CFG['progression_min_count']: continue
            if sg==-1 and sum(v['h'][j]<v['h'][j-1] and v['l'][j]<v['l'][j-1] for j in range(k-lag+1,k+1))<CFG['progression_min_count']: continue
            ans.append(k); break
        i=b+1
    return ans

def main():
    assert CFG['timeframe']=='H1' and STEP==3600 and CFG['ema_periods']==[10,20,50]
    assert CFG['frozen'] is True and CFG['status']=='FROZEN_RESEARCH_BASELINE'
    src=json.loads((P/'source/native_source.json').read_text())
    assert src['timeframe']=='H1' and src['symbol']==CFG['symbol']
    allraw=np.array(src['bars'],dtype=float); ex=src['extraction']
    mask=(allraw[:,0]<ex['current_H1_open_epoch'])&(allraw[:,0]+STEP<=ex['latest_tick_epoch'])
    raw=allraw[mask]
    assert len(raw)>500 and np.all(np.diff(raw[:,0])>0) and np.all(raw[:,0]%STEP==0)
    assert np.all(np.isfinite(raw)) and np.all(raw[:,1:5]>0)
    assert np.all(raw[:,3]<=np.minimum(raw[:,1],raw[:,4])) and np.all(raw[:,2]>=np.maximum(raw[:,1],raw[:,4]))
    v=indicators(raw); events,episodes=scan(v)
    assert [r['index'] for r in events]==independent(v), 'Independent scan mismatch'
    checks=sorted(set([r['index'] for r in events[::max(1,len(events)//16)]]+[len(raw)-1]))
    for i in checks:
        vv=indicators(raw[:i+1]); ss,_=scan(vv)
        assert ss==[r for r in events if r['index']<=i], 'Future-data dependency'
        assert np.array_equal(vv['e'],v['e'][:i+1]) and np.array_equal(vv['atr'],v['atr'][:i+1])
    assert len({r['cycle_id'] for r in events})==len(events)
    assert all(not any(v['gap'][r['index']-2:r['index']+1]) for r in events)
    start=epoch(CFG['analysis_start_native_label']); selected=[r for r in events if v['t'][r['index']]>=start]
    formations=[]
    for r in selected:
        i=r['index']; j=i+1; e=v['e'][i]; atr=v['atr'][i]
        if j>=len(allraw): status='PENDING_NEXT_BAR'; price=None
        elif allraw[j,0]!=raw[i,0]+STEP: status='CANCELLED_GAP'; price=None
        else: status='OBSERVED_NEXT_OPEN_PROXY'; price=float(allraw[j,1])
        formations.append({'cycle_id':r['cycle_id'],'direction':'BUY' if r['side']==1 else 'SELL',
          'signal_bar_open_native':label(raw[i,0]),'known_at_close_native':label(raw[i,0]+STEP),
          'cluster_start_native':label(raw[r['cycle_start'],0]),'known_cluster_bars':r['known_persistence'],
          'first_outside_cluster':r['first_outside'],'ema10':float(e[0]),'ema20':float(e[1]),'ema50':float(e[2]),
          'atr14':float(atr),'width_atr':float(v['wa'][i]),'minimum_width_atr_so_far':r['min_width_so_far'],
          'next_open_status':status,'next_open_price_proxy':price})
    cols=src['columns']; barrows=[]
    for i,row in enumerate(raw):
        d=dict(zip(cols,[int(row[0])]+[float(x) for x in row[1:5]]+[int(x) for x in row[5:]]))
        d.update(open_native_label=label(row[0]),close_native_label=label(row[0]+STEP),sample='2026' if row[0]>=start else 'WARMUP',
          ema10=float(v['e'][i,0]),ema20=float(v['e'][i,1]),ema50=float(v['e'][i,2]),atr14=float(v['atr'][i]),
          cluster_width=float(v['width'][i]),cluster_width_atr=float(v['wa'][i]),cluster=bool(v['qual'][i]))
        barrows.append(d)
    gaps=[{'before':label(raw[i-1,0]),'after':label(raw[i,0]),'hours_between_opens':int((raw[i,0]-raw[i-1,0])/STEP)} for i in range(1,len(raw)) if v['gap'][i]]
    cycles=[{'cycle_id':r['id'],'start_native':label(raw[r['start'],0]),'last_converged_bar_native':label(raw[r['end'],0]),
      'observed_cluster_bars':r['count'],'observed_minimum_width_atr':r['min_width_atr'],'has_formation':r['consumed']} for r in episodes if raw[r['end'],0]>=start]
    audit={'source_sha256':sha(P/'source/native_source.json'),'raw_rows':len(allraw),'completed_rows':len(raw),
      'excluded_forming_or_future_rows':int((~mask).sum()),'warmup_rows':int((raw[:,0]<start).sum()),
      'analysis_2026_rows':int((raw[:,0]>=start).sum()),'first_completed_native':label(raw[0,0]),
      'last_completed_open_native':label(raw[-1,0]),'last_completed_close_native':label(raw[-1,0]+STEP),
      'fresh_against_tick':ex['fresh_against_tick'],'duplicates':0,'invalid_ohlc':0,'off_hour_timestamps':0,
      'gaps_count':len(gaps),'gaps':gaps,'gap_policy':'All gaps reset episodes; 3-bar confirmations require four consecutive hourly bars. Gaps are listed, not silently filled.',
      'timestamp_handling':src['timestamp_handling']}
    verification={'status':'PASS','independent_scan_exact':True,'causal_prefix_checks':len(checks),
      'one_formation_per_episode':True,'no_confirmation_across_gaps':True,'forming_bar_excluded':bool((~mask).sum()),
      'source_sha256':audit['source_sha256'],'config_sha256':sha(P/'formula_config.json'),'code_sha256':sha(P/'formula.py')}
    summary={'formula_id':CFG['formula_id'],'status':CFG['status'],'frozen':True,'timeframe':'H1','ema_periods':CFG['ema_periods'],
      'data':{k:v for k,v in audit.items() if k not in ['gaps','timestamp_handling']},
      'formations_2026':len(formations),'directions':dict(Counter(r['direction'] for r in formations)),
      'clusters_2026':len(cycles),'verification':verification,
      'performance_status':'Not evaluated. Formation counts and code checks are not a profitability or predictive-validation result.'}
    csvfile('USDJPY_H1_closed_bars_indicators.csv',barrows); csvfile('USDJPY_H1_formations_2026.csv',formations)
    csvfile('USDJPY_H1_clusters_2026.csv',cycles)
    dump('data_audit.json',audit); dump('verification.json',verification); dump('summary.json',summary)
    dump('formula_state.json',{'formula_id':CFG['formula_id'],'frozen':True,'editable':False,'status':CFG['status'],
      'parent_preserved':'previous_M30_v0_1/','freeze_authorized_on':'2026-11-18','deployment':'RESEARCH_FILES_ONLY'})
    print(json.dumps(summary),flush=True)

if __name__=='__main__': main()
