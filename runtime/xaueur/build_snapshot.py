"""XAUEUR H1-P1 v2.0 research projection for the common dashboard publisher."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
VERSION = 'XAUEUR_H1_P1_V2_BASELINE'
SYMBOL = 'XAUEUR.pro'
ENGINE = 'd150b44886886b431329f4a175ad51803d3ed55287e62fdccf6b42add92ac4c9'
RULES = ['Narrowest of four EMA triples within 0.25 of the preceding H1 ATR14',
         'First close outside the fixed detection candle high or low',
         'EMA10 and EMA20 both move in the breakout direction on each of the next two H1 closes',
         'Two further closes beyond the next-open reference P0',
         'Next available H1 open, subject to same-direction EMA cycle ownership',
         'Benchmark: EUR 35 per ounce before the completed EMA10/20 cycle turns']


def stamp(t):
    return datetime.fromtimestamp(int(t), timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def native():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError(str(mt5.last_error()))
    try:
        info=mt5.symbol_info(SYMBOL)
        assert mt5.terminal_info().connected and info and info.point==.01 and info.currency_profit=='EUR'
        recent=mt5.copy_rates_from_pos(SYMBOL,mt5.TIMEFRAME_H1,0,1)
        tick=mt5.symbol_info_tick(SYMBOL)
        assert tick and recent is not None and len(recent)==1
        t=int(recent[-1]['time'])
        assert t<=tick.time<t+3600,'Native H1 series is behind the symbol quote'
        bars=mt5.copy_rates_range(SYMBOL,mt5.TIMEFRAME_H1,datetime(2024,10,1,tzinfo=timezone.utc),datetime.fromtimestamp(t-1,timezone.utc))
        assert bars is not None and len(bars)
        return pd.DataFrame(bars).rename(columns={'time':'time_epoch'}), (t,float(recent[-1]['open'])),int(tick.time)
    finally:
        mt5.shutdown()


def build(frame=None, window='recent'):
    reference=json.loads((HERE/'reference.json').read_text(encoding='utf-8'))[window]
    live=frame is None
    observed=datetime.now(timezone.utc).isoformat() if live else reference['observed']
    opening=tick=None
    if live:
        if window!='recent':
            raise ValueError(window)
        frame,opening,tick=native()
    df=frame.copy()
    assert df.time_epoch.is_monotonic_increasing and df.time_epoch.is_unique and not df.isna().any().any()
    assert (df.low>0).all() and (df.low<=df[['open','close']].min(axis=1)).all() and (df.high>=df[['open','close']].max(axis=1)).all()
    archive=df[df.time_epoch<=reference['last_open']]
    d=hashlib.sha256()
    for r in archive.itertuples():
        d.update(f'{r.time_epoch},{r.open:.2f},{r.high:.2f},{r.low:.2f},{r.close:.2f}\n'.encode())
    if len(archive)!=reference['bars'] or d.hexdigest()!=reference['bar_sha256']:
        raise ValueError('Native price history differs from the archived XAUEUR research prefix')
    for n in (10,20,50,200):
        df[f'ema{n}']=df.close.ewm(span=n,adjust=False).mean()
    tr=pd.concat([df.high-df.low,(df.high-df.close.shift()).abs(),(df.low-df.close.shift()).abs()],axis=1).max(axis=1).to_numpy()
    atr=np.full(len(df),np.nan)
    atr[13]=np.mean(tr[:14])
    for i in range(14,len(df)):
        atr[i]=(13*atr[i-1]+tr[i])/14
    df['wilder_atr14']=atr
    df['open_time']=[stamp(t) for t in df.time_epoch]
    df['close_time']=[stamp(t+3600) for t in df.time_epoch]
    rows=df.astype(object).where(df.notna(),None).to_dict('records')
    code=(HERE/'frozen_engine.py').read_text(encoding='utf-8')
    assert hashlib.sha256(code.encode()).hexdigest()==ENGINE
    original="'2025-01-01'<=r['open_time'][:10]<='2026-11-09'"
    assert code.count(original)==1
    code=code.replace(original,repr(reference['start'])+"<=r['open_time'][:10]")
    marker='  orders=[]\n  sign='
    assert code.count(marker)==1
    code=code.replace(marker,"  orders=[]\n  if r.get('opening_only'):break\n  sign=")
    ns={'__file__':str(HERE/'frozen_engine.py')}
    exec(compile(code,'XAUEUR_window_adapter','exec'),ns)
    feed=list(rows)
    if opening:
        assert opening[0]>=df.time_epoch.iat[-1]+3600
        feed.append(dict(rows[-1],open=opening[1],open_time=stamp(opening[0]),opening_only=True))
    result=ns['run'](feed)
    es=result['entries']
    outcomes=ns['outcomes'](rows,[e for e in es if e['entry_index']<len(rows)])
    checked=[[o['entry_time'],'BUY' if o['sgn']==1 else 'SELL',o['entry_price'],round(o['MFE_points']),round(o['MAE_points']),o['end_time'],o['target_hit']] for o in outcomes if o['entry_index']<len(archive)]
    assert checked==reference['entries'],'Archived XAUEUR entries or excursions differ'
    for e in es:
        if e['entry_index']==len(rows):
            outcomes.append(dict(e,cycle_complete=False,target_hit=False,MFE_points=0,MAE_points=0,
                                 end_time=e['entry_time'],end_close=e['entry_price'],MFE_bar_close=None,status='OPEN_NO_COMPLETED_BAR'))
    boxes={c['case']:c for c in result['clusters']}
    cases={c['case']:c for c in result['cases']}
    ends={r['close_time']:i for i,r in enumerate(rows)}
    entries=[]
    months={}
    for o in outcomes:
        c=cases[o['case']]
        e={k:o[k] for k in ('case','direction','sgn','entry_time','entry_price','signal_time','cycle_complete','target_hit','MFE_points','MAE_points','end_time','end_close','MFE_bar_close','status')}
        e.update(cluster=boxes[c['cluster_case']],breakout_time=c['first_break'],ema_confirmed=c['ema_signal_time'],
                 reference_price=c['reference_price'],benchmark_price=round(o['entry_price']+35*o['sgn'],2),
                 peak_price=round(o['entry_price']+.01*o['sgn']*o['MFE_points'],2),
                 cohort='archived' if o['entry_index']<len(archive) else 'after_cutoff')
        e['path']=[dict(time=o['entry_time'],price=o['entry_price'])]+[dict(time=r['close_time'],price=r['close']) for r in rows[o['entry_index']:ends.get(o['end_time'],-1)+1]]
        entries.append(e)
        m=months.setdefault(e['entry_time'][:7],dict(entries=0,hits=0,misses=0,open=0))
        m['entries']+=1
        m['open']+=int(not e['cycle_complete'])
        if e['cycle_complete']:
            m['hits' if e['target_hit'] else 'misses']+=1
    last=rows[-1]
    cur=dict(state='WAIT',direction=None,cluster=result['clusters'][-1],projection=None,reason='No active qualified entry or pending confirmation.')
    active=[e for e in entries if not e['cycle_complete']]
    pending=[c for c in result['cases'] if c['status'] in ('WAIT_TWO_CANDLES','WAIT_PRICE_FOLLOW_THROUGH','SIGNAL_AWAITING_OPEN','QUALIFIED_AWAITING_OPEN')]
    if active and len({x['sgn'] for x in active})==1:
        e=active[-1];cur.update(state='ACTIVE_CYCLE',direction=e['direction'],sgn=e['sgn'],entry=e,cluster=e['cluster'],reason='Qualified XAUEUR entry. Its directional EMA cycle is open.')
    elif active:
        cur.update(state='MIXED',reason='Opposing research cycles are open.')
    elif pending:
        c=pending[-1];cur.update(state=c['status'],direction=c['direction'],sgn=c['sgn'],cluster=boxes[c['cluster_case']],reason='A first breakout is being checked against the remaining confirmation stages.')
    if cur.get('sgn'):
        cur['projection']=dict(from_price=last['close'],illustrative_end_price=last['close']+cur['sgn']*last['wilder_atr14'])
    fields=('open_time','close_time','open','high','low','close','ema10','ema20','ema50','ema200')
    candles=[{k:r[k] for k in fields} for r in rows if r['open_time'][:10]>=reference['start']]
    return dict(version=VERSION,symbol=SYMBOL,timeframe='H1',point=.01,digits=2,benchmark_points=3500,benchmark_eur=35,
                generated_at=observed,quote_observed_at=observed,broker_tick_time=stamp(tick) if live else None,
                data_asof=last['close_time'],refresh_mode='Automatic snapshot refresh every 15 minutes' if live else 'Saved research replay',
                current=cur,entries=entries,candles=candles,months=months,rule_summary=RULES,
                validation=dict(archived_entries_reproduced=len(checked),archived_outcomes_exact=True,
                                overlap_bars=len(archive),new_completed_bars=len(rows)-len(archive),forming_candle_excluded=True,engine_sha256=ENGINE),
                broker_orders_enabled=False)
