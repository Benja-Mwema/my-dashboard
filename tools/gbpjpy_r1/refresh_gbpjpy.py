"""Read-only MT5 observer. --watch observes ticks continuously; publishes local JSON only.
Run publication separately. Never calls order_send. Ctrl+C stops the observer.
"""
import argparse,json,time,os
from pathlib import Path
from datetime import datetime,timezone
import MetaTrader5 as mt5
from gbpjpy_r1 import build,observe,VERSION
ROOT=Path(__file__).resolve().parent

def atomic(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');temp.replace(path)

def run(watch=False):
    if not mt5.initialize():raise RuntimeError(str(mt5.last_error()))
    symbol='GBPJPY.pro'
    if mt5.symbol_info(symbol) is None:
        matches=[s.name for s in mt5.symbols_get() if s.name.startswith('GBPJPY')]
        if len(matches)!=1:raise RuntimeError('Ambiguous broker mapping: '+repr(matches))
        symbol=matches[0]
    if not mt5.symbol_select(symbol,True):raise RuntimeError('Cannot select GBPJPY')
    frozen=json.loads((ROOT/'frozen_bars.json').read_text());saved=ROOT/'observed_touches.json';events=json.loads(saved.read_text()) if saved.exists() else {}
    cursor=None;lock=ROOT/'observer.lock';lastsave=0;d=None
    if watch:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    try:
        while True:
            tick=mt5.symbol_info_tick(symbol);info=mt5.symbol_info(symbol)
            if tick is None:raise RuntimeError('No broker quote')
            rates=mt5.copy_rates_from_pos(symbol,mt5.TIMEFRAME_H1,0,4000)
            if rates is None:raise RuntimeError(str(mt5.last_error()))
            raw=[{k:int(r['time']) if k=='time' else float(r[k]) for k in ('time','open','high','low','close')} for r in rates]
            bytime={b['time']:b for b in raw};overlap=0
            for f in frozen:
                if f['time'] not in bytime:continue
                overlap+=1
                if any(abs(f[k]-bytime[f['time']][k])>1e-9 for k in ('open','high','low','close')):raise RuntimeError('Frozen/native OHLC mismatch at '+str(f['time']))
            if overlap<24:raise RuntimeError('Insufficient frozen/native overlap')
            combined=frozen+[b for b in raw if b['time']>frozen[-1]['time']]
            d=build(combined,int(tick.time),symbol);d['point']=info.point
            d.update(generated_at=datetime.now(timezone.utc).isoformat(),quote_broker_time=int(tick.time),quote_bid=tick.bid,quote_ask=tick.ask,native_overlap_verified=overlap,publication_mode='Published snapshot; local observer updates are not streamed to this page',observation_mode='Continuous local tick sampling' if watch else 'Single refresh tick observation')
            samples=[tick]
            if cursor is not None:
                ticks=mt5.copy_ticks_from(symbol,datetime.fromtimestamp(cursor/1000,timezone.utc),100000,mt5.COPY_TICKS_ALL)
                if ticks is None:raise RuntimeError('Tick retrieval failed')
                if len(ticks)>=100000:raise RuntimeError('Tick window truncated; continuity cannot be asserted')
                samples=[r for r in ticks if int(r['time_msc'])>cursor and int(r['time_msc'])<=tick.time_msc]
            def val(t,k):return getattr(t,k) if hasattr(t,k) else t[k].item()
            bars=d['candles']
            for t in samples:
                tm=int(val(t,'time'));bar_open=tm//3600*3600
                prev=next((b for b in reversed(bars) if b['time']<bar_open),None)
                if not prev:continue
                for s in d['signals']:
                    if s['id'] in events:continue
                    ev=observe(s,prev,bar_open,tm,float(val(t,'bid')),float(val(t,'ask')))
                    if ev:
                        ev['broker_time_msc']=int(val(t,'time_msc'));ev['captured_at']=d['generated_at'];events[s['id']]=ev;atomic(saved,events)
            cursor=int(tick.time_msc)
            for s in d['signals']:
                s['observed_touch']=events.get(s['id'])
                if s['observed_touch']:
                    s['modeled_exit']=s['exit'];s['exit']=dict(s['observed_touch'],bar_close=s['observed_touch']['broker_time'])
                    ev=s['observed_touch'];prior=[b for b in bars if b['time']>=s['entry_time'] and b['open_time']<ev['bar_open']]
                    prices=[s['entry_reference'],ev['reference_price']]+[v for b in prior for v in (b['high'],b['low'])]
                    s['MFE_pips']=max(0,max(s['sgn']*(p-s['entry_reference'])/.01 for p in prices))
                    s['MAE_pips']=max(0,max(-s['sgn']*(p-s['entry_reference'])/.01 for p in prices))
                    s['path']=[p for p in s['path'] if p['time']<=ev['broker_time']]
            done=[s for s in d['signals'] if s['exit']];wins=sum(s['exit']['gross_pips']>=0 for s in done)
            d['summary'].update(completed=len(done),open=len(d['signals'])-len(done),nonnegative=wins,losses=len(done)-wins,rate=100*wins/len(done) if done else None,gross_pips=sum(s['exit']['gross_pips'] for s in done))
            if not watch or time.monotonic()-lastsave>=30:
                atomic(ROOT/'gbpjpy-data.json',d);lastsave=time.monotonic();print(json.dumps({'asof':d['candles'][-1]['close_time'],'candidate':d['candidate']['state'],'summary':d['summary'],'observed_events':len(events)}),flush=True)
            if not watch:break
            time.sleep(1)
    finally:
        mt5.shutdown()
        if watch:lock.unlink(missing_ok=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--watch',action='store_true');run(p.parse_args().watch)
