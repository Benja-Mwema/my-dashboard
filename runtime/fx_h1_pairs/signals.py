from datetime import datetime,timezone
import pandas as pd
import numpy as np
HOUR=3600
START=int(pd.Timestamp("2026-01-01",tz="UTC").timestamp())

BASE=dict(width=.50,finish=.50,max_buy=8,max_sell=16,side="both",max_age=None)
CHANGES={
    "baseline":{},
    "width_040":{"width":.40},
    "width_060":{"width":.60},
    "strong_close":{"finish":.65},
    "recent_cross":{"max_age":2},
    "short_cluster":{"max_buy":5,"max_sell":10},
    "buy_only":{"side":"BUY"},
    "sell_only":{"side":"SELL"},
}
PROFILES={name:{**BASE,**changes} for name,changes in CHANGES.items()}

def label(t):
    return datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%d %H:%M")

def run(m, bars, profile, limit=None):
    bars = bars if limit is None else bars.iloc[:limit]
    cfg=PROFILES[profile]
    t,o,h,l,c = (bars[key].to_numpy() for key in ("time","open","high","low","close"))
    assert np.all(np.diff(t)>0) and np.isfinite([o,h,l,c]).all()
    assert (l>0).all() and (h>=np.maximum(o,c)).all() and (l<=np.minimum(o,c)).all()
    e10,e20,e50 = [bars.close.ewm(span=n,adjust=False).mean().to_numpy() for n in (10,20,50)]
    prev=np.r_[c[0],c[:-1]]
    tr=np.maximum.reduce([h-l,abs(h-prev),abs(l-prev)])
    atr=pd.Series(tr).ewm(alpha=1/14,adjust=False).mean().to_numpy()
    width=np.maximum.reduce([e10,e20,e50])-np.minimum.reduce([e10,e20,e50])
    depth=np.divide(width,atr,where=atr>0,out=np.full(len(atr),np.inf))
    delta=e10-e20
    n=0
    last_cross=0
    used=False
    events=[]
    episode=0
    cross_i=None
    for i,tm in enumerate(t):
        neighbor=i>0 and tm-t[i-1]==HOUR
        if not neighbor:
            n=0
        q=depth[i]<=cfg["width"]
        if not n:
            if not q:
                continue
            episode+=1
            start=i
            used=False
            last_cross=0
            cross_i=None
            min_d=depth[i]
        if q:
            n+=1
            min_d=min(min_d,depth[i])
        if neighbor:
            direction=1 if delta[i-1]<=0<delta[i] else -1 if delta[i-1]>=0>delta[i] else 0
            if direction:
                last_cross=direction
                cross_i=i
        if (not used and last_cross and i>=3 and tm-t[i-3]==3*HOUR and h[i]>l[i] and atr[i]>0 and width[i]>width[i-1]):
            s10,s20,s50=[(e[i]-e[i-3])/(3*atr[i]) for e in (e10,e20,e50)]
            cl=(c[i]-l[i])/(h[i]-l[i])
            change=np.diff(c[i-3:i+1])
            ups,downs=int((change>0).sum()),int((change<0).sum())
            lower=int(((np.diff(h[i-3:i+1])<0)&(np.diff(l[i-3:i+1])<0)).sum())
            buy=(last_cross==1 and 2<=n<=cfg["max_buy"] and e10[i]>e20[i]>e50[i] and s10>0 and s20>0 and s50>=0 and c[i]>e10[i] and c[i]>o[i] and cl>=cfg["finish"] and ups>=2)
            sell=(last_cross==-1 and 4<=n<=cfg["max_sell"] and e10[i]<e20[i]<e50[i] and s10<0 and s20<0 and s50<=0 and c[i]<e10[i] and c[i]<o[i] and cl<=round(1-cfg["finish"],2) and downs>=2 and lower>=2)
            buy=buy and cfg["side"] in ("both","BUY")
            sell=sell and cfg["side"] in ("both","SELL")
            fresh=cfg["max_age"] is None or (cross_i is not None and i-cross_i<=cfg["max_age"])
            if fresh and (buy or sell):
                used=True
                if START<=tm+HOUR:
                    events.append(dict(pair=m['pair'],symbol=m['symbol'],side="BUY" if buy else "SELL",i=i,episode=episode,
                         cluster_first_open=label(t[start]),cross_bar_open=label(t[cross_i]),signal_open=label(tm),decision_close=label(tm+HOUR),
                         cross_age=i-cross_i,decision_epoch=int(tm+HOUR),month=label(tm+HOUR)[:7],phase="inside" if q else "first outside",
                         N=n,min_depth=min_d,width=width[i],previous_width=width[i-1],depth=depth[i],ATR14=atr[i],EMA10=e10[i],EMA20=e20[i],EMA50=e50[i],
                         S10=s10,S20=s20,S50=s50,CL=cl,up_closes=ups,down_closes=downs,lower_pairs=lower))
        if not q:
            n=0
    return events
