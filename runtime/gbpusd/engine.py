import numpy as np
import pandas as pd
def ema(x,n):
    a=2/(n+1); z=np.empty(len(x)); z[0]=x[0]
    for i in range(1,len(x)):z[i]=a*x[i]+(1-a)*z[i-1]
    return z

def indicators(df):
    t=df.time.to_numpy(); o,h,l,c=[df[k].to_numpy() for k in ['open','high','low','close']]
    e=np.column_stack([ema(c,n) for n in [10,20,50]])
    prev=np.r_[c[0],c[:-1]]
    tr=np.maximum(h-l,np.maximum(abs(h-prev),abs(l-prev))); tr[0]=h[0]-l[0]
    a=np.empty(len(t));a[0]=tr[0]
    for i in range(1,len(t)):a[i]=tr[i]/14+13*a[i-1]/14
    w=np.ptp(e,axis=1); depth=np.divide(w,a,out=np.full(len(t),np.inf),where=a>0)
    return dict(labels=pd.to_datetime(t,unit='s').astype(str).to_numpy(),close_labels=pd.to_datetime(t+1800,unit='s').astype(str).to_numpy(),t=t,o=o,h=h,l=l,c=c,e=e,a=a,w=w,depth=depth,q=depth<=.5,gap=np.r_[False,np.diff(t)!=1800])

def gates(f,side,omit=None):
    sg=1 if side=='BUY' else -1
    g={
      'continuity':f['contiguous4'], 'positive_atr':f['atr']>0, 'nonzero_range':f['high']>f['low'],
      'persistence':2<=f['N']<=8 if sg==1 else 4<=f['N']<=16,
      'ordering':f['ema10']>f['ema20']>f['ema50'] if sg==1 else f['ema10']<f['ema20']<f['ema50'],
      'slopes':sg*f['slope10']>0 and sg*f['slope20']>0 and sg*f['slope50']>=0,
      'expansion':f['width']>f['previous_width'],
      'beyond_band':sg*(f['close']-f['ema10'])>0,
      'candle_direction':sg*(f['close']-f['open'])>0,
      'candle_finish':f['close_location']>=.5 if sg==1 else f['close_location']<=.5,
      'close_progression':(f['up_closes3'] if sg==1 else f['down_closes3'])>=2,
      'lower_pairs':sg==1 or f['lower_pairs3']>=2,
    }
    if omit:g[omit]=True
    return {k:bool(v) for k,v in g.items()}

def e1_scan(v,omit=None,audit=True):
    t=v['t']; records=[];episodes=[];decisions=[]; ep=None;cid=0
    for i in range(len(t)):
        if v['gap'][i]:
            if ep is not None:ep.update(end_reason='gap',end_index=i-1)
            ep=None
        outside=False
        if v['q'][i]:
            if ep is None:
                cid+=1;ep=dict(episode_id=cid,start_index=i,start_time=v['labels'][i],N=0,min_depth=float(v['depth'][i]),used=False,signal_index=None,end_reason='data_edge',end_index=i)
                episodes.append(ep)
            ep['N']+=1;ep['min_depth']=min(ep['min_depth'],float(v['depth'][i]));ep['end_index']=i
        elif ep is not None:outside=True
        else:continue
        slopes=(v['e'][i]-v['e'][i-3])/(3*v['a'][i]) if i>=3 and v['a'][i]>0 else np.zeros(3)
        rg=v['h'][i]-v['l'][i]
        f=dict(i=i,episode_id=cid,signal_open_time=v['labels'][i],decision_time=v['close_labels'][i],decision_epoch=int(t[i]+1800),
          episode_start=ep['start_time'],N=ep['N'],min_depth_so_far=ep['min_depth'],phase='first_outside' if outside else 'inside',
          episode_unused=not ep['used'],contiguous4=i>=3 and bool(np.all(np.diff(t[i-3:i+1])==1800)),
          open=float(v['o'][i]),high=float(v['h'][i]),low=float(v['l'][i]),close=float(v['c'][i]),
          ema10=float(v['e'][i,0]),ema20=float(v['e'][i,1]),ema50=float(v['e'][i,2]),
          atr=float(v['a'][i]),width=float(v['w'][i]),previous_width=float(v['w'][i-1]) if i else 0.,depth=float(v['depth'][i]),
          slope10=float(slopes[0]),slope20=float(slopes[1]),slope50=float(slopes[2]),close_location=float((v['c'][i]-v['l'][i])/rg) if rg>0 else -1.,
          up_closes3=int(sum(v['c'][k]>v['c'][k-1] for k in range(i-2,i+1))) if i>=3 else 0,
          down_closes3=int(sum(v['c'][k]<v['c'][k-1] for k in range(i-2,i+1))) if i>=3 else 0,
          lower_pairs3=int(sum(v['h'][k]<v['h'][k-1] and v['l'][k]<v['l'][k-1] for k in range(i-2,i+1))) if i>=3 else 0)
        g={s:gates(f,s,omit) for s in ['BUY','SELL']}
        sides=[s for s in g if all(g[s].values())]
        assert len(sides)<=1
        if not ep['used'] and sides:
            ep['used']=True;ep['signal_index']=i
            records.append({**f,'side':sides[0]})
        if audit:
            decisions.append({**f,'signal_side':sides[0] if sides and f['episode_unused'] else '',
               **{s.lower()+'_failed':';'.join(k for k,val in g[s].items() if not val) for s in g},
               **{s.lower()+'_'+k:val for s in g for k,val in g[s].items()}})
        if outside:
            ep.update(end_reason='first_outside',end_index=i);ep=None
    return records,episodes,decisions


def scan(raw):
 f=raw.copy().reset_index(drop=True);v=indicators(f);records,episodes,audit=e1_scan(v)
 f['date']=pd.to_datetime(f.time,unit='s')
 for j,n in enumerate([10,20,50]):f[f'e{n}']=v['e'][:,j]
 f['atr']=v['a'];f['width']=v['w'];f['depth']=v['depth']
 out=[]
 for r in records:
  x=r.copy();x.update(time=int(v['t'][r['i']]),date=pd.Timestamp(r['signal_open_time']),decision=pd.Timestamp(r['decision_time']),e10=r['ema10'],e20=r['ema20'],e50=r['ema50'],s10=r['slope10'],s20=r['slope20'],s50=r['slope50'],min_depth=r['min_depth_so_far'],cl=r['close_location'],up=r['up_closes3'],down=r['down_closes3'],lower=r['lower_pairs3'],contig4=r['contiguous4'])
  out.append(x)
 return f,pd.DataFrame(out),pd.DataFrame(audit)
