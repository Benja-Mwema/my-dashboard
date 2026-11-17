import pandas as pd
import numpy as np
def indicators(d):
    f=d.copy().reset_index(drop=True)
    for n in (10,20,50): f[f'e{n}']=f.close.ewm(span=n,adjust=False).mean()
    pc=f.close.shift(1)
    tr=pd.concat([f.high-f.low,(f.high-pc).abs(),(f.low-pc).abs()],axis=1).max(axis=1)
    f['atr']=tr.ewm(alpha=1/14,adjust=False).mean()
    f['width']=f[['e10','e20','e50']].max(axis=1)-f[['e10','e20','e50']].min(axis=1)
    f['depth']=f.width/f.atr
    f['q']=f.depth<=0.50
    for n in (10,20,50): f[f's{n}']=(f[f'e{n}']-f[f'e{n}'].shift(3))/(3*f.atr)
    f['contiguous4']=f.time.diff().eq(1800).rolling(3).sum().eq(3)
    f['up3']=f.close.gt(pc).rolling(3).sum()
    f['down3']=f.close.lt(pc).rolling(3).sum()
    f['lower3']=(f.high.lt(f.high.shift(1))&f.low.lt(f.low.shift(1))).rolling(3).sum()
    f['cl']=(f.close-f.low)/(f.high-f.low)
    f['previous_width']=f.width.shift(1)
    return f

def prepare(d):
    f=indicators(d)
    f['e200']=f.close.ewm(span=200,adjust=False).mean()
    f['s200']=(f.e200-f.e200.shift(3))/(3*f.atr)
    f['body_atr']=(f.close-f.open).abs()/f.atr
    f['band20_50']=(f.e20-f.e50).abs()/f.atr
    f['upper_wick']=(f.high-f[['open','close']].max(axis=1))/(f.high-f.low)
    f['lower_wick']=(f[['open','close']].min(axis=1)-f.low)/(f.high-f.low)
    f['prior2_high']=f.high.shift(1).rolling(2).max();f['prior2_low']=f.low.shift(1).rolling(2).min()
    for n in [6,12,24]:
        f[f'contig{n}']=f.time.diff().eq(1800).rolling(n-1).sum().eq(n-1)
        f[f'prior{n}_high']=f.high.shift(1).rolling(n).max();f[f'prior{n}_low']=f.low.shift(1).rolling(n).min()
    return f

def generate(f,c):
    a={col:f[col].to_numpy() for col in f.columns if col not in ['time_label','close_label']}
    t=a['time'];op=a['open'];hi=a['high'];lo=a['low'];cl=a['close'];A=a['atr'];E10=a['e10'];E20=a['e20'];E50=a['e50'];E200=a['e200']
    direction=1 if c['side']=='BUY' else -1
    result=[];active=None;n=0;start=None;used=False;previous_touch=False;last_signal=-100
    def emit(i,episode,phase,details):
        result.append(dict(index=i,time=int(t[i]),decision_time=int(t[i]+1800),decision_label=str(pd.to_datetime(t[i]+1800,unit='s')),side=c['side'],config_id=c['id'],family=c['family'],episode_id=int(t[episode]),phase=phase,atr=float(A[i]),e10=float(E10[i]),e20=float(E20[i]),e50=float(E50[i]),e200=float(E200[i]),depth=float(a['depth'][i]),body_atr=float(a['body_atr'][i]),extension20_atr=float(direction*(cl[i]-E20[i])/A[i]),s50=float(a['s50'][i]),band20_50=float(a['band20_50'][i]),**details))
    for i in range(len(f)):
        if i==0 or t[i]-t[i-1]!=1800:
            active=None;n=0;start=None;used=False;previous_touch=False;last_signal=-100
        if c['family']=='compression':
            q=a['depth'][i]<=c['depth']
            if q:
                if n==0:start=i;used=False;active=None
                n+=1
                continue
            if n:
                if c['nmin']<=n<=c['nmax']:
                    b=max(start,i-c['box_bars']);active=dict(start=start,end=i-1,n=n,high=float(max(hi[b:i])),low=float(min(lo[b:i])),atr=float(A[i-1]))
                else:active=None
                n=0
            if active is None or used:continue
            if i-active['end']>c['grace_bars']:active=None;continue
            if not a['contiguous4'][i] or hi[i]<=lo[i]:continue
            level=active['high']+c['buffer_atr']*active['atr'] if direction==1 else active['low']-c['buffer_atr']*active['atr']
            breakout=direction*(cl[i]-level)>0
            if c['hold']==2:breakout=breakout and i>active['end']+1 and direction*(cl[i-1]-level)>0
            trend=direction*(E10[i]-E20[i])>0 and direction*a['s10'][i]>0 and direction*a['s20'][i]>0
            if c['trend']=='aligned':trend=trend and direction*(E20[i]-E50[i])>0 and direction*a['s50'][i]>=0
            candle=direction*(cl[i]-op[i])>0 and (a['cl'][i] if direction==1 else 1-a['cl'][i])>=c['close_finish'] and a['body_atr'][i]>=c['body_min']
            extension=0<direction*(cl[i]-E20[i])/A[i]<=c['extension_cap']
            if breakout and trend and candle and extension and a['width'][i]>a['previous_width'][i]:
                emit(i,active['start'],'post_compression',{'n':active['n'],'anchor_high':active['high'],'anchor_low':active['low'],'anchor_end_index':active['end'],'bars_after_compression':i-active['end']});used=True
        elif c['family']=='pullback':
            trend=direction*(E20[i]-E50[i])>0 and direction*a['s20'][i]>0 and direction*a['s50'][i]>0 and c['band_min']<=a['band20_50'][i]<=c['band_max']
            if c['trend']=='ema200':trend=trend and direction*(E50[i]-E200[i])>0 and direction*a['s200'][i]>=0
            touch=(lo[i]<=E20[i] and cl[i]>=E50[i]) if direction==1 else (hi[i]>=E20[i] and cl[i]<=E50[i])
            touch=bool(touch and trend)
            if not trend:active=None
            if touch:
                if not previous_touch and i>0 and direction*(cl[i-1]-E20[i-1])>0:active={'start':i,'last_touch':i,'used':False}
                elif active is not None:active['last_touch']=i
            previous_touch=touch
            if active is None or active['used']:continue
            if i-active['last_touch']>c['wait_bars']:active=None;continue
            if not a['contig6'][i] or hi[i]<=lo[i] or i-last_signal<=c['cooldown_bars']:continue
            candle=direction*(cl[i]-op[i])>0 and (a['cl'][i] if direction==1 else 1-a['cl'][i])>=c['close_finish'] and a['body_atr'][i]>=c['body_min']
            trigger=(direction*(cl[i]-E10[i])>0 and direction*(cl[i-1]-E10[i-1])<=0) if c['trigger']=='ema10_reclaim' else (cl[i]>a['prior2_high'][i] if direction==1 else cl[i]<a['prior2_low'][i])
            extension=0<direction*(cl[i]-E20[i])/A[i]<=c['extension_cap']
            if candle and trigger and extension:
                emit(i,active['start'],'pullback_recovery',{'pullback_age':i-active['start'],'last_touch_index':active['last_touch'],'bars_since_touch':i-active['last_touch'],'cooldown_distance':i-last_signal});active['used']=True;last_signal=i
        else:
            nback=c['lookback']
            contiguous=i>=nback and np.all(np.diff(t[i-nback:i+1])==1800)
            if not contiguous or hi[i]<=lo[i]:active=None;continue
            ph=a[f'prior{nback}_high'][i];pl=a[f'prior{nback}_low'][i]
            boxwidth=(ph-pl)/A[i]
            regime=a['band20_50'][i]<=c['band_max'] and abs(a['s50'][i])<=c['slope50_max'] and c['box_width_min']<=boxwidth<=c['box_width_max']
            candle=direction*(cl[i]-op[i])>0 and (a['cl'][i] if direction==1 else 1-a['cl'][i])>=c['close_finish']
            reject=(lo[i]<pl-c['penetration_atr']*A[i] and cl[i]>pl and a['lower_wick'][i]>=c['wick_min']) if direction==1 else (hi[i]>ph+c['penetration_atr']*A[i] and cl[i]<ph and a['upper_wick'][i]>=c['wick_min'])
            # Evaluate an earlier rejection before a current bar can arm the next one.
            if active is not None:
                if i-active['start']>2:active=None
                elif candle and (cl[i]>active['high'] if direction==1 else cl[i]<active['low']) and abs(cl[i]-E20[i])/A[i]<=c['extension_cap'] and i-last_signal>c['cooldown_bars']:
                    emit(i,active['start'],'confirmed_failed_breakout',{'rejection_index':active['start'],'anchor_high':active['range_high'],'anchor_low':active['range_low']});last_signal=i;active=None
            if regime and reject and candle and abs(cl[i]-E20[i])/A[i]<=c['extension_cap']:
                if c['confirm']=='rejection':
                    if i-last_signal>c['cooldown_bars']:
                        emit(i,i,'failed_breakout_rejection',{'anchor_high':ph,'anchor_low':pl});last_signal=i
                else:active={'start':i,'high':hi[i],'low':lo[i],'range_high':ph,'range_low':pl}
    cols=['index','time','decision_time','decision_label','side','config_id','family','episode_id','phase','atr']
    return pd.DataFrame(result) if result else pd.DataFrame(columns=cols)

CONFIG={'family': 'pullback', 'side': 'SELL', 'trend': 'ema200', 'wait_bars': 3, 'trigger': 'ema10_reclaim', 'extension_cap': 1.0, 'body_min': 0.4, 'close_finish': 0.65, 'band_min': 0.25, 'band_max': 2.0, 'cooldown_bars': 12, 'id': 'F162'}
def scan(raw):
 f=prepare(raw);f['date']=pd.to_datetime(f.time,unit='s')
 signals=generate(f,CONFIG);out=[]
 for r in signals.to_dict('records'):
  i=r['index'];z=f.iloc[i];p=f.iloc[i-1]
  r.update(i=i,date=z.date,decision=z.date+pd.Timedelta(minutes=30),open=z.open,high=z.high,low=z.low,close=z.close,s20=z.s20,s200=z.s200,cl=z.cl,contig6=bool(z.contig6),prior_close=p.close,prior_e10=p.e10)
  out.append(r)
 return f,pd.DataFrame(out),None
