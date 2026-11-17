"""Read-only MT5 chart context; forming bars never enter frozen signal engines."""
from pathlib import Path
from datetime import datetime,timezone
import json,time,math
import MetaTrader5 as mt
ROOT=Path(__file__).resolve().parent
REPO=Path(r'D:\render_sites\my-dashboard')
ASSETS={'eurusd':('eurusd','EURUSD.pro'),'gbpusd':('gbpusd','GBPUSD.pro'),'eurjpy':('eurjpy','EURJPY.pro'),'cadjpy':('cadjpy','CADJPY.pro'),'gold':('cluster','XAUUSD.pro'),'gbpjpy':('gbpjpy','GBPJPY.pro'),'audcad':('audcad','AUDCAD.pro'),'ws30':('ws30','WS30.pro'),'dax40':('dax40','DAX40.pro')}
def stamp():return datetime.now(timezone.utc).isoformat()
def label(t):return datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
def source_time(b):
 if isinstance(b,list):return int(b[0])
 v=b.get('open_time',b.get('time'))
 return int(v) if isinstance(v,(int,float)) else int(datetime.strptime(v,'%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp())
def build():
 out={'version':'AURUM_MARKET_CONTEXT_1','observed_at_utc':stamp(),'cadence_minutes':15,'clock':'NATIVE_BROKER_LABELS_NOT_UTC','assets':{}}
 assert mt.initialize(),mt.last_error()
 try:
  assert mt.terminal_info().connected,'MT5 terminal disconnected'
  for kind,(stem,sym) in ASSETS.items():
   try:
    step=1800 if kind in ('eurjpy','gbpusd','eurusd') else 3600;tf='M30' if kind in ('eurjpy','gbpusd','eurusd') else 'H1'
    assert mt.symbol_select(sym,True)
    for attempt in range(4):
     rr=mt.copy_rates_from_pos(sym,getattr(mt,'TIMEFRAME_'+tf),0,1024);tick=mt.symbol_info_tick(sym)
     if rr is not None and len(rr)>10 and tick and int(rr[-1]['time'])==tick.time//step*step:break
     time.sleep(.4)
    assert rr is not None and len(rr)>10 and tick,'Missing rate/quote source'
    lagging=int(rr[-1]['time'])!=tick.time//step*step
    bars=[dict(time=int(r['time']),open=float(r['open']),high=float(r['high']),low=float(r['low']),close=float(r['close'])) for r in rr]
    assert all(all(math.isfinite(b[k]) for k in ('open','high','low','close')) and b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high'] for b in bars)
    assert all(b['time']>a['time'] for a,b in zip(bars,bars[1:]))
    d=json.loads((REPO/(stem+'-data.json')).read_text(encoding='utf-8'))
    old={source_time(b):b for b in d['candles']};common=[b for b in bars[:-1] if b['time'] in old][-64:]
    assert len(common)>=3,'Insufficient published/source overlap'
    errors=[]
    for b in common:
     a=old[b['time']]
     for i,k in enumerate(('open','high','low','close'),1):
      if abs(b[k]-(a[i] if isinstance(a,list) else a[k]))>1e-6:errors.append((b['time'],k))
    assert not errors,'Published/native OHLC mismatch '+str(errors[:3])
    completed=bars[:-1];forming=bars[-1];origin='NATIVE_'+tf;warning=None
    if lagging:
     start=tick.time//step*step;first_missing=completed[-1]['time']+step;fetch_start=min(start,first_missing)
     assert start-fetch_start<=24*60*60,'Native H1 feed lag exceeds tick-reconstruction limit'
     ticks=mt.copy_ticks_range(sym,datetime.fromtimestamp(fetch_start,timezone.utc),datetime.fromtimestamp(tick.time+1,timezone.utc),mt.COPY_TICKS_ALL)
     assert ticks is not None and 0<len(ticks)<1000000,'Current-hour ticks unavailable or oversized'
     all_ticks=[z for z in ticks if fetch_start<=int(z['time'])<=tick.time and float(z['bid'])>0]
     for h in range(fetch_start,start,step):
      group=[z for z in all_ticks if h<=int(z['time'])<h+step]
      assert group and int(group[0]['time'])<=h+2 and int(group[-1]['time'])>=h+step-5,'Missing completed-hour tick coverage'
      prices=[float(z['bid']) for z in group];completed.append(dict(time=h,open=prices[0],high=max(prices),low=min(prices),close=prices[-1],chart_origin='TICK_RECONSTRUCTED_'+tf))
     ticks=[z for z in all_ticks if int(z['time'])>=start]
     assert ticks and int(ticks[0]['time'])<=start+2 and int(ticks[-1]['time'])>=tick.time-5,'Current-hour tick coverage not sufficient'
     bids=[float(z['bid']) for z in ticks];forming=dict(time=start,open=bids[0],high=max(bids),low=min(bids),close=bids[-1]);origin='TICK_RECONSTRUCTED_'+tf;warning='Native '+tf+' feed is behind live ticks. Current candle reconstructed from current-hour bid ticks; frozen signals are unchanged.'
    out['assets'][kind]={'symbol':sym,'timeframe':tf,'period_seconds':step,'forming_origin':origin,'source_warning':warning,'state':'VERIFIED_NATIVE_CONTEXT','observed_at_utc':stamp(),'tick_native':int(tick.time),'tick_label':label(tick.time),'bid':tick.bid,'ask':tick.ask,'overlap_bars_verified':len(common),'completed':completed,'forming':dict(forming,complete=False),'latest_completed_open':completed[-1]['time'],'forming_open_label':label(forming['time'])}
   except Exception as e:out['assets'][kind]={'symbol':sym,'state':'UNAVAILABLE','reason':str(e),'observed_at_utc':stamp()}
 finally:mt.shutdown()
 out['observed_at_utc']=stamp()
 return out
if __name__=='__main__':
 d=build();p=ROOT/'market-context.json';p.write_text(json.dumps(d,separators=(',',':'),allow_nan=False),encoding='utf-8');print(json.dumps({k:{z:v.get(z) for z in ['state','forming_open_label','reason','overlap_bars_verified']} for k,v in d['assets'].items()}))
