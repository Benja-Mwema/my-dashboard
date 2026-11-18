"""Prepare one broker-verified, closed-bar H1 research snapshot."""
from datetime import datetime, timezone
from pathlib import Path
import json
import time
import pandas as pd
import numpy as np
from .signals import run, label, PROFILES

ROOT=Path(__file__).resolve().parent
CONFIG=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
VERSION='FX_H1_EMA_CROSS_V0_2'
def stamp(t):
    return label(t)+':00'

def snapshot(pair,bars,active_time,active_price,generated):
    spec=CONFIG['pairs'][pair]
    assert len(bars)>1200 and int(bars.time.iat[0])<=1762387200
    assert not bars.time.duplicated().any() and bars.time.is_monotonic_increasing
    assert int(bars.time.iat[-1])<active_time and (np.diff(bars.time)%3600==0).all()
    emas={f'ema{n}':bars.close.ewm(span=n,adjust=False).mean() for n in (10,20,50)}
    tr=pd.concat([bars.high-bars.low,(bars.high-bars.close.shift()).abs(),(bars.low-bars.close.shift()).abs()],axis=1).max(axis=1)
    atr=tr.ewm(alpha=1/14,adjust=False).mean()
    em=pd.DataFrame(emas)
    depth=(em.max(axis=1)-em.min(axis=1))/atr
    columns=bars[['time','open','high','low','close']].copy()
    for key,vs in emas.items():columns[key]=vs.round(12)
    columns['atr14']=atr.round(12)
    columns['depth']=depth.round(10)
    models={}
    for role,profile,h in [('original','baseline',12),('adjusted',spec['profile'],spec['horizon'])]:
        rule=dict(PROFILES[profile],profile=profile,horizon=h)
        entries=[]
        for x in run(dict(pair=pair,symbol=pair+'.pro'),bars,profile):
            i=x['i']; side=x['side']; sign=1 if side=='BUY' else -1
            b=bars.iloc[i]; nt=int(bars.time.iat[i+1]) if i+1<len(bars) else active_time
            price=(float(bars.open.iat[i+1]) if i+1<len(bars) else active_price) if nt==int(b.time)+3600 else None
            xf=i+h
            complete=price is not None and xf<len(bars)
            exit_price=float(bars.close.iat[xf]) if complete else None
            gross=round(sign*(exit_price-price)*10000,1) if complete else None
            net=round(gross-2,1) if complete else None
            state='COMPLETE' if complete else 'PENDING' if price is not None else 'CANCELLED_GAP' if nt!=int(b.time)+3600 else 'PENDING'
            close=float(b.close)
            entries.append(dict(id=pair+'-'+role+'-'+str(x['decision_epoch'])+'-'+side,direction=side,
              signal_bar_open=stamp(b.time),signal_available_at=stamp(x['decision_epoch']),signal_epoch=int(b.time),
              cluster_start=x['cluster_first_open']+':00',cross_bar_open=x['cross_bar_open']+':00',N=x['N'],phase=x['phase'].replace(' ','_'),min_depth=round(x['min_depth'],8),
              width_growth=round(x['width']-x['previous_width'],12),ema10=x['EMA10'],ema20=x['EMA20'],ema50=x['EMA50'],slope10=x['S10'],slope20=x['S20'],slope50=x['S50'],
              close_location=x['CL'],directional_closes3=x['up_closes'] if sign==1 else x['down_closes'],lower_pairs3=x['lower_pairs'],body=close-float(b.open),close_minus_ema10=close-x['EMA10'],
              entry_time=stamp(nt) if price is not None else None,entry_price=price,selected_horizon=h,selected_cost=2,execution_status=state,raw_gross_pips=gross,net_pips=net,
              exit_price=exit_price,exit_bar_available_at=stamp(int(bars.time.iat[xf])+3600) if complete else None,forward_gap=bool(int(bars.time.iat[xf])-int(b.time)!=3600*h) if complete else None))
        proved=[[e['signal_available_at'][:16],e['direction'],e['N'],e['cross_bar_open'][:16],e['net_pips']] for e in entries if e['signal_available_at']<'2026-11-18']
        assert proved==CONFIG['reference'][pair][role],pair+' '+role+' archived entries or outcomes differ'
        models[role]=dict(rule=rule,entries=entries,verified_archive_count=len(proved))
    return dict(symbol=pair+'.pro',version=VERSION,primary=spec['primary'],research_status=spec['status'],generated_at=generated,
      latest_completed_h1=stamp(int(bars.time.iat[-1])+3600),digits=5,pip=.0001,models=models,candles=columns.to_dict('records'),
      meta=dict(timeframe='H1',paper_only=True,broker_orders_enabled=False,email_enabled=False),health=dict(state='OK'))

def build(pair):
    import MetaTrader5 as mt
    symbol=pair+'.pro'
    if not mt.initialize():raise RuntimeError(str(mt.last_error()))
    try:
        assert mt.terminal_info().connected and mt.symbol_select(symbol,True)
        meta=mt.symbol_info(symbol)
        assert meta.digits==5 and meta.currency_profit==pair[3:] and abs(meta.point-.00001)<1e-10
        for attempt in range(4):
            current=mt.copy_rates_from_pos(symbol,mt.TIMEFRAME_H1,0,1)
            if current is None or len(current)!=1:time.sleep(.5);continue
            cutoff=int(current[0]['time'])
            rates=mt.copy_rates_range(symbol,mt.TIMEFRAME_H1,datetime(2025,11,1,tzinfo=timezone.utc),datetime.fromtimestamp(cutoff,timezone.utc))
            tick=mt.symbol_info_tick(symbol)
            if rates is not None and len(rates)>1200 and int(rates[-1]['time'])==cutoff and tick and tick.time//3600*3600==cutoff:break
            time.sleep(.75)
        else:raise ValueError('MT5 H1 history did not reach the current quote hour')
        frame=pd.DataFrame(rates[:-1])
        return snapshot(pair,frame,cutoff,float(rates[-1]['open']),datetime.now(timezone.utc).isoformat())
    finally:mt.shutdown()
