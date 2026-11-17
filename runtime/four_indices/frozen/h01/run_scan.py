"""WS30-H01 v0.1 frozen scan. Historical research, no broker/order calls."""
from pathlib import Path
import argparse,json,hashlib,zipfile
import numpy as np
import pandas as pd
ROOT=Path(__file__).parent
P=json.loads((ROOT/'parameters.json').read_text())
def wilder(s,n=14):
    a=s.to_numpy(float);o=np.full(len(a),np.nan); ids=np.flatnonzero(np.isfinite(a))
    if len(ids)<n:return pd.Series(o,index=s.index)
    k=ids[n-1];o[k]=a[ids[:n]].mean()
    for i in range(k+1,len(a)):o[i]=(o[i-1]*(n-1)+a[i])/n
    return pd.Series(o,index=s.index)
def ts(t):
    return '' if pd.isna(t) else str(pd.Timestamp(t))
def split(t):
    t=pd.Timestamp(t)
    if t<pd.Timestamp('2026-07-01'):return 'development'
    if t<pd.Timestamp('2026-10-01'):return 'validation'
    if t<pd.Timestamp('2026-11-01'):return 'discovery'
    return 'november_check'
SPLIT_END={'development':pd.Timestamp('2026-07-01'),'validation':pd.Timestamp('2026-10-01'),'discovery':pd.Timestamp('2026-11-01'),'november_check':pd.Timestamp('2026-12-01')}
def load_data(source):
    frames={}
    with zipfile.ZipFile(source) as z:
        for tf,mins in [('M1',1),('M15',15),('H1',60),('H4',240),('D1',1440)]:
            d=pd.read_csv(z.open(f'data/WS30.pro_{tf}_2026_Jan_Nov.csv'))
            d['t']=pd.to_datetime(d.broker_time);d['end']=d.t+pd.Timedelta(minutes=mins)
            d=d[d.confirmed_by_later_bar==1].reset_index(drop=True)
            if tf in ['H1','H4']:
                for n in [10,20,50,200]:d[f'ema{n}']=d.close.ewm(span=n,adjust=False).mean()
                d['ema20_slope']=d.ema20.diff()
                d['macd']=d.close.ewm(span=12,adjust=False).mean()-d.close.ewm(span=26,adjust=False).mean()
                ch=d.close.diff();gain=wilder(ch.clip(lower=0));loss=wilder(-ch.clip(upper=0))
                d['rsi14']=100-100/(1+gain/loss)
                tr=pd.concat([d.high-d.low,(d.high-d.close.shift()).abs(),(d.low-d.close.shift()).abs()],axis=1).max(axis=1)
                d['atr14']=wilder(tr)
                d['bar_count']=np.arange(1,len(d)+1)
                for n in [10,20,50,200]:d.loc[d.bar_count<n,f'ema{n}']=np.nan
                d.loc[d.bar_count<26,'macd']=np.nan
                d.loc[d.bar_count<=20,'ema20_slope']=np.nan
            frames[tf]=d
    h=frames['H1'];daily=frames['D1'][['t','end','low','high']].rename(columns={'t':'ref_day','end':'ref_known','low':'ref_low','high':'ref_high'})
    frames['H1']=pd.merge_asof(h.sort_values('t'),daily.sort_values('ref_known'),left_on='t',right_on='ref_known',direction='backward')
    return frames
class Scan:
    def __init__(self,frames):
        self.f=frames;self.h=frames['H1'];self.m=frames['M1'];self.m15=frames['M15'];self.n=len(self.h)
        self.ht=self.h.t.to_numpy();self.mt=self.m.t.to_numpy();self.m15t=self.m15.t.to_numpy()
        self.cutoff=self.h.end.iloc[-1]
        self.stages=[];self.episodes=[];self.breaches=[];self.trades=[]
        g=self.m.groupby(self.m.t.dt.floor('h')).agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),tick_volume=('tick_volume','sum'))
        q=self.h.set_index('t').join(g,rsuffix='_m1');bad=q.open_m1.isna()
        for k in ['open','high','low','close','tick_volume']:bad|=(q[k]-q[k+'_m1']).abs()>1e-8
        self.bad_hours=set(q.index[bad]);assert not self.bad_hours,'Native M1/H1 disagreement requires explicit resolution'
    def log(self,e,k,stage,detail=''):
        self.stages.append({'episode_id':e['episode_id'],'direction':e['direction'],'h1_open':ts(self.h.t.iloc[k]),'known_at':ts(self.h.end.iloc[k]),'stage':stage,'detail':detail})
    def invalid(self,k,s,L,delta):
        r=self.h.iloc[k]; adverse=r.low if s==1 else r.high
        return s*(r.close-L)<0 or s*(adverse-L)<-delta
    def next_entry(self,k):
        when=self.h.end.iloc[k];mi=int(np.searchsorted(self.m15t,np.datetime64(when)))
        return None if mi>=len(self.m15) else self.m15.iloc[mi]
    def outcome(self,e,policy,k):
        s=e['sign'];A=e['A'];entry=self.next_entry(k)
        o={'episode_id':e['episode_id'],'direction':e['direction'],'policy':policy,'signal_h1_open':ts(self.h.t.iloc[k]),'signal_time':ts(self.h.end.iloc[k]),'A':A,'reference':e['reference'],'cohort_split':e['split']}
        if entry is None:
            o.update(status='censored',observed_status='no_next_open',score=np.nan,horizon_complete=False,horizon_end='',entry_time='',entry=np.nan)
            return o,pd.Timestamp.max
        E=float(entry.open);et=entry.t
        j=int(np.searchsorted(self.ht,np.datetime64(et)));last=j+23;complete=last<self.n
        end=self.h.end.iloc[last] if complete else self.cutoff
        hs=self.h.iloc[j:min(last+1,self.n)]
        o.update(entry_time=ts(et),entry=E,target=E+s*2*A,adverse_barrier=E-s*A,horizon_complete=complete,horizon_end=ts(end) if complete else '',
                 entry_spread_points=int(entry.spread),elapsed_hours_to_signal=(self.h.end.iloc[k]-pd.Timestamp(e['reclaim_time'])).total_seconds()/3600)
        fav_high=hs.high if s==1 else hs.low;adv_low=hs.low if s==1 else hs.high
        o['mfe_24_A']=float((s*(fav_high-E)).max()/A) if len(hs) else np.nan
        o['mae_24_A']=float((-s*(adv_low-E)).max()/A) if len(hs) else np.nan
        o['terminal_return_A']=float(s*(hs.close.iloc[-1]-E)/A) if len(hs) else np.nan
        status='timeout';score=o['terminal_return_A'];exitprice=float(hs.close.iloc[-1]) if len(hs) else E
        eventtime=end;lastspread=float(hs.spread.iloc[-1]) if len(hs) else float(entry.spread);gap=False
        for ii,r in hs.iterrows():
            openchange=s*(r.open-E)/A
            fh=r.high if s==1 else r.low;al=r.low if s==1 else r.high
            tf=s*(fh-E)>=2*A;ta=s*(al-E)<=-A
            if not(tf or ta):continue
            lo=int(np.searchsorted(self.mt,np.datetime64(max(et,r.t))));hi=int(np.searchsorted(self.mt,np.datetime64(r.end)))
            minutes=self.m.iloc[lo:hi]
            found=False
            for _,v in minutes.iterrows():
                oc=s*(v.open-E)/A
                f=s*((v.high if s==1 else v.low)-E)>=2*A
                a=s*((v.low if s==1 else v.high)-E)<=-A
                if oc>=2:status='favorable_first';score=2.;exitprice=float(v.open);gap=True
                elif oc<=-1:status='adverse_first';score=-1.;exitprice=float(v.open);gap=True
                elif f and a:status='ambiguous';score=-1.;exitprice=E-s*A
                elif f:status='favorable_first';score=2.;exitprice=E+s*2*A
                elif a:status='adverse_first';score=-1.;exitprice=E-s*A
                else:continue
                eventtime=v.t;lastspread=float(v.spread);found=True;break
            if not found:
                status='censored';score=np.nan;eventtime=r.t
            break
        o.update(observed_status=status,status=status if complete else 'censored',score=score if complete else np.nan,
            optimistic_score=(2. if status=='ambiguous' else score) if complete else np.nan,
            event_bar_open=ts(eventtime),event_price_proxy=exitprice,event_gap=gap,
            exit_spread_points=lastspread,full_horizon_hours=(end-et).total_seconds()/3600 if complete else np.nan)
        o['reference_failed_in_horizon']=bool(((hs.close<e['reference']) if s==1 else (hs.close>e['reference'])).any())
        spread_cost=.1*(float(entry.spread)+lastspread)/2/A
        execution_score=(min(score,s*(exitprice-E)/A) if status=='adverse_first' and gap else score)
        for mult in [0,1,2]:
            o[f'cost_{mult}spread_score']=(execution_score-mult*spread_cost) if complete else np.nan
        o['cost_2spread_plus1unit_score']=(execution_score-2*spread_cost-1/A) if complete else np.nan
        r=self.h.iloc[k]
        for key in ['ema10','ema20','ema50','ema200','macd','rsi14','atr14','bar_count']:o['H1_'+key]=float(r[key])
        h4=self.f['H4'];id4=int(h4.end.searchsorted(r.end,side='right'))-1
        if id4>=0:
            rr=h4.iloc[id4];o['H4_known_at']=ts(rr.end)
            for key in ['close','ema10','ema20','ema50','ema200','ema20_slope','macd','rsi14','bar_count']:o['H4_'+key]=float(rr[key])
        o['resumption_close_location']=float((r.close-r.low)/(r.high-r.low)) if r.high>r.low else .5
        o['resumption_hour']=r.t.hour
        return o,(end if complete else pd.Timestamp.max)
    def episode(self,b,s,serial):
        h=self.h;seed=h.iloc[b];L=float(seed.ref_low if s==1 else seed.ref_high);A=float(h.atr14.iloc[b-1]);delta=.1*A
        e={'episode_id':f'{"BUY" if s==1 else "SELL"}_{serial:03d}','direction':'BUY' if s==1 else 'SELL','sign':s,
            'break_h1_open':ts(seed.t),'break_time':ts(seed.end),'ref_day':ts(seed.ref_day),'reference':L,'A':A,
            'split':split(seed.t),'cohort_eligible':False,'reclaim_time':'','defense_time':'','H_signal_time':'','B_signal_time':'',
            'H_state':'not_eligible','B_state':'not_eligible','end_reason':'','depth_A':np.nan}
        self.log(e,b,'breakdown',f'reference={L}; A={A}')
        rc=None;ext=float(seed.low if s==1 else seed.high);decision_end=seed.end
        for k in range(b+1,min(self.n,b+25)):
            ext=min(ext,float(h.low.iloc[k])) if s==1 else max(ext,float(h.high.iloc[k]))
            decision_end=h.end.iloc[k]
            if s*(h.close.iloc[k]-L)>delta:
                rc=k;break
        e['depth_A']=-s*(ext-L)/A
        if rc is None:
            e['end_reason']='reclaim_expired' if b+24<self.n else 'reclaim_censored'
            self.log(e,min(self.n-1,b+24),e['end_reason'])
            e['decision_end']=ts(decision_end);e['episode_end']=ts(decision_end) if b+24<self.n else ''
            return e,decision_end if b+24<self.n else pd.Timestamp.max
        e['reclaim_time']=ts(h.end.iloc[rc]);e['reclaim_h1_open']=ts(h.t.iloc[rc])
        self.log(e,rc,'first_reclaim',f'depth_A={e["depth_A"]:.6f}')
        if e['depth_A']<1:
            e['end_reason']='insufficient_depth'
            self.log(e,rc,'insufficient_depth')
            e['decision_end']=ts(decision_end);e['episode_end']=ts(decision_end)
            return e,decision_end
        e['cohort_eligible']=True
        trades=[];rtrade,rend=self.outcome(e,'R',rc);trades.append(rtrade);busy=rend
        e['H_state']='awaiting_defense';e['B_state']='awaiting_defense'
        hold=None;pullback=False;postext=None
        for k in range(rc+1,min(self.n,rc+9)):
            decision_end=h.end.iloc[k];r=h.iloc[k]
            v=float(r.low if s==1 else r.high)
            postext=v if postext is None else min(postext,v) if s==1 else max(postext,v)
            if self.invalid(k,s,L,delta):
                e['H_state']=e['B_state']='invalid_before_defense';self.log(e,k,'invalid_before_defense');break
            pullback|=s*(r.close-h.close.iloc[k-1])<0
            if k-rc>=2 and pullback and -delta<=s*(postext-L)<=.5*A:
                hold=k;e['defense_time']=ts(r.end);e['defense_h1_open']=ts(r.t)
                e['defense_extreme']=postext;e['defense_distance_A']=s*(postext-L)/A
                Q=float(r.high if s==1 else r.low)
                peak=float(h.high.iloc[rc:k+1].max() if s==1 else h.low.iloc[rc:k+1].min())
                e['Q']=Q;e['breakout_reference']=peak;e['H_state']=e['B_state']='awaiting_trigger'
                self.log(e,k,'defended_retest',f'extreme={postext}; Q={Q}; breakout_reference={peak}')
                break
        if hold is None:
            if e['H_state']=='awaiting_defense':
                endstate='defense_expired' if rc+8<self.n else 'defense_censored'
                e['H_state']=e['B_state']=endstate;self.log(e,min(self.n-1,rc+8),endstate)
                if endstate.endswith('censored'):busy=pd.Timestamp.max
            e['end_reason']=e['H_state']
        else:
            for k in range(hold+1,min(self.n,hold+25)):
                decision_end=h.end.iloc[k];r=h.iloc[k]
                if self.invalid(k,s,L,delta):
                    for pol in ['H','B']:
                        if e[pol+'_state']=='awaiting_trigger':e[pol+'_state']='invalid_before_trigger';self.log(e,k,pol+'_invalid_before_trigger')
                else:
                    if e['H_state']=='awaiting_trigger' and k-hold<=4 and s*(r.close-Q)>delta and s*(r.close-r.open)>0:
                        e['H_state']='entered';e['H_signal_time']=ts(r.end);self.log(e,k,'H_resumption')
                        tr,end=self.outcome(e,'H',k);trades.append(tr);busy=max(busy,end)
                    if e['B_state']=='awaiting_trigger' and s*(r.close-peak)>delta:
                        e['B_state']='entered';e['B_signal_time']=ts(r.end);self.log(e,k,'B_breakout')
                        tr,end=self.outcome(e,'B',k);trades.append(tr);busy=max(busy,end)
                if k-hold==4 and e['H_state']=='awaiting_trigger':e['H_state']='resumption_expired';self.log(e,k,'H_resumption_expired')
                if k-hold==24 and e['B_state']=='awaiting_trigger':e['B_state']='breakout_expired';self.log(e,k,'B_breakout_expired')
                if e['H_state']!='awaiting_trigger' and e['B_state']!='awaiting_trigger':break
            for pol in ['H','B']:
                if e[pol+'_state']=='awaiting_trigger':
                    e[pol+'_state']='trigger_censored';busy=pd.Timestamp.max;self.log(e,self.n-1,pol+'_trigger_censored')
            e['end_reason']='policy_decisions_finished' if busy!=pd.Timestamp.max else 'episode_censored'
        busy=max(busy,decision_end)
        e['decision_end']=ts(decision_end);e['episode_end']=ts(busy) if busy!=pd.Timestamp.max else ''
        e['cross_partition']=busy!=pd.Timestamp.max and busy>SPLIT_END[e['split']]
        e['cohort_score_complete']=busy!=pd.Timestamp.max and all(t['status']!='censored' for t in trades)
        for pol in ['R','H','B']:
            found=next((t for t in trades if t['policy']==pol),None)
            state=e.get(pol+'_state','')
            e[pol+'_score']=found['score'] if found is not None else (np.nan if 'censored' in state else 0.)
            e[pol+'_status']=found['status'] if found is not None else 'no_entry'
            for cost in ['cost_0spread_score','cost_1spread_score','cost_2spread_score','cost_2spread_plus1unit_score']:
                e[pol+'_'+cost]=found.get(cost,np.nan) if found is not None else (np.nan if 'censored' in state else 0.)
        for t in trades:
            t['cross_partition']=e['cross_partition'];t['episode_end']=e['episode_end']
            t['formal_partition_eligible']=bool(e['cohort_score_complete'] and not e['cross_partition'])
        self.trades.extend(trades)
        return e,busy
    def run(self):
        busy={1:pd.Timestamp.min,-1:pd.Timestamp.min};active={1:'',-1:''};seen={1:set(),-1:set()};serial={1:0,-1:0}
        for i,r in self.h.iterrows():
            if pd.isna(r.ref_day):continue
            for s in [1,-1]:
                key=ts(r.ref_day);L=float(r.ref_low if s==1 else r.ref_high)
                if key in seen[s] or s*(r.close-L)>=0:continue
                seen[s].add(key)
                br={'direction':'BUY' if s==1 else 'SELL','ref_day':key,'reference':L,'h1_open':ts(r.t),'known_at':ts(r.end),'close':r.close,'disposition':'','blocking_episode':'','episode_id':''}
                if i==0 or not np.isfinite(self.h.atr14.iloc[i-1]):
                    br['disposition']='insufficient_ATR_warmup'
                elif r.end<busy[s]:
                    br['disposition']='skipped_active_episode';br['blocking_episode']=active[s]
                else:
                    serial[s]+=1;e,end=self.episode(i,s,serial[s]);self.episodes.append(e)
                    br['disposition']='episode_started';br['episode_id']=e['episode_id'];busy[s]=end;active[s]=e['episode_id']
                self.breaches.append(br)
        ep=pd.DataFrame(self.episodes);tr=pd.DataFrame(self.trades)
        tr['opposite_episode_overlap']=False
        for j,row in tr.iterrows():
            a=pd.Timestamp(row.entry_time) if row.entry_time else pd.Timestamp.max
            b=pd.Timestamp(row.horizon_end) if row.horizon_end else pd.Timestamp.max
            for _,other in ep[ep.direction!=row.direction].iterrows():
                oa=pd.Timestamp(other.break_time);ob=pd.Timestamp(other.episode_end) if other.episode_end else self.cutoff
                if a<ob and oa<b:tr.loc[j,'opposite_episode_overlap']=True;break
        return ep,tr,pd.DataFrame(self.breaches),pd.DataFrame(self.stages)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=ROOT.parent/'WS30pro_MT5_Jan_Nov_2026.zip');ap.add_argument('--end',default='2026-12-01');ap.add_argument('--out',type=Path,default=ROOT/'results');args=ap.parse_args()
    assert hashlib.sha256(args.source.read_bytes()).hexdigest()==P['source_sha256']
    args.out.mkdir(parents=True,exist_ok=True)
    fs=load_data(args.source);end=pd.Timestamp(args.end)
    fs={tf:d[d.end<=end].reset_index(drop=True) for tf,d in fs.items()}
    scan=Scan(fs);ep,tr,br,st=scan.run()
    for name,df in [('episodes',ep),('policy_entries',tr),('first_breaches',br),('stage_ledger',st)]:
        df.to_csv(args.out/(name+'.csv'),index=False,float_format='%.8f')
    H=tr[tr.policy=='H'].copy();H.to_csv(args.out/'H01_matches.csv',index=False,float_format='%.8f')
    print('Scan cutoff',scan.cutoff,'H1 bars',len(scan.h))
    print('First breaches',len(br),br.disposition.value_counts().to_dict())
    print('Episodes',len(ep),'eligible reclaims',int(ep.cohort_eligible.sum()))
    print('H stage',ep.H_state.value_counts().to_dict())
    print('Entries',tr.groupby(['policy','direction','status']).size().to_dict())
    print('H signals')
    print(H[['episode_id','direction','signal_time','entry_time','entry','A','status','score','cohort_split','cross_partition']].to_string(index=False))
    meta={'data_cutoff':ts(scan.cutoff),'H1_bars':len(scan.h),'M1_H1_mismatches':len(scan.bad_hours),'source_sha256':P['source_sha256'],'spec_sha256':P['spec_sha256'],'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'parameters':P}
    (args.out/'run_manifest.json').write_text(json.dumps(meta,indent=2))
if __name__=='__main__':main()

