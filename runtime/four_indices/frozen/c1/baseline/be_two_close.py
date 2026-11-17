"""Unchanged completed-bar BE execution function from the tested comparison."""
import pandas as pd

def scheduled(d,E,A,s,tp,times,terminal,end):
    # Information available at a completed H1 close is acted on at the next M1 open.
    effective=set()
    for t in times:
        j=int(d.t.searchsorted(pd.Timestamp(t)))
        if j<len(d):effective.add(str(d.t.iloc[j]))
    armed=False;arm_time='';done={};active=True;skipped=[]
    def finish(status,t,price,gap):
        val={'WIN':tp,'LOSS':-3.,'BE':0.}.get(status,s*(price-E)/A)
        done[(status,t)]=dict(status=status,time=t,arm_time=arm_time,score_R=val/3,
            gap_adjusted_R=(min(val,s*(price-E)/A) if status in ['LOSS','BE'] else val)/3,
            gap=bool(gap),price_proxy=price)
    for r in d[['t','open','high','low','close']].itertuples(index=False):
        if not active:break
        t=str(r.t);o=s*(r.open-E)/A
        high=s*((r.high if s==1 else r.low)-E)/A;low=s*((r.low if s==1 else r.high)-E)/A
        if armed and o<=0:finish('BE',t,float(r.open),o<0);active=False;break
        if not armed and o<=-3:finish('LOSS',t,float(r.open),o<-3);active=False;break
        if o>=tp:finish('WIN',t,float(r.open),o>tp);active=False;break
        if not armed and t in effective:
            if o>0:armed=True;arm_time=t
            else:skipped.append(t)
        if high>=tp:finish('WIN',t,E+s*tp*A,False)
        stop=0 if armed else -3
        if low<=stop:finish('BE' if armed else 'LOSS',t,E+s*stop*A,False)
        if high>=tp or low<=stop:active=False
    if active:finish('TIMEOUT',str(end),terminal,False)
    paths=list(done.values());status=sorted({p['status'] for p in paths});tm=sorted({p['time'] for p in paths})
    return dict(status=status[0] if len(status)==1 else 'AMBIGUOUS',possible_statuses='|'.join(status),
        score_R_min=min(p['score_R'] for p in paths),score_R_max=max(p['score_R'] for p in paths),
        gap_adjusted_R_min=min(p['gap_adjusted_R'] for p in paths),gap_adjusted_R_max=max(p['gap_adjusted_R'] for p in paths),
        first_activation_time=arm_time,exit_time_first=tm[0],exit_time_last=tm[-1],
        event_time_ambiguous=len(tm)>1,opening_gap_any=any(p['gap'] for p in paths),
        skipped_nonprofitable_activation=';'.join(skipped),paths=paths)
