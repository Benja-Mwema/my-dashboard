"""Publish native USDJPY H1 evidence using the frozen v0.2 formula. No order API."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, csv, sys, time
import numpy as np
import formula as engine

ROOT=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(): return datetime.now(timezone.utc).isoformat()
def label(t): return engine.label(t)
def atomic(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,separators=(',',':'),allow_nan=False),encoding='utf-8')
    tmp.replace(path)
def completed(source):
    rows=np.array(source['bars'],dtype=float); ex=source['extraction']
    return rows[(rows[:,0]<ex['current_H1_open_epoch'])&(rows[:,0]+3600<=ex['latest_tick_epoch'])]
def read_live():
    import MetaTrader5 as mt
    assert mt.initialize(),mt.last_error()
    try:
        assert mt.terminal_info().connected,'MT5 disconnected'
        assert mt.account_info().server=='SCFMLimited-Live2','Unexpected source server'
        assert mt.symbol_select('USDJPY.pro',True)
        info=mt.symbol_info('USDJPY.pro');assert info.digits==3 and abs(info.point-.001)<1e-12
        for _ in range(4):
            tick=mt.symbol_info_tick('USDJPY.pro'); assert tick and tick.time>0
            rates=mt.copy_rates_range('USDJPY.pro',mt.TIMEFRAME_H1,engine.epoch('2025-10-01'),int(tick.time))
            if rates is not None and len(rates)>500 and 0<=int(tick.time)-int(rates[-1]['time'])<3600:break
            time.sleep(.4)
        assert rates is not None and len(rates)>500,'H1 source unavailable'
        bars=[[int(r['time'])]+[float(r[k]) for k in ['open','high','low','close']]+[int(r[k]) for k in ['tick_volume','spread','real_volume']] for r in rates]
        return {'symbol':'USDJPY.pro','server':'SCFMLimited-Live2','timeframe':'H1','bars':bars,
          'extracted_at_utc':stamp(),'bid':float(tick.bid),'ask':float(tick.ask),
          'extraction':{'current_H1_open_epoch':int(rates[-1]['time']),'latest_tick_epoch':int(tick.time),
            'fresh_against_tick':0<=int(tick.time)-int(rates[-1]['time'])<3600}}
    finally:mt.shutdown()
def project(source,offline=False):
    manifest=json.loads((ROOT/'freeze_manifest.json').read_text())
    for name,h in manifest['files'].items():assert sha(ROOT/name)==h,'Frozen file changed: '+name
    assert engine.CFG['frozen'] is True and engine.CFG['status']=='FROZEN_RESEARCH_BASELINE'
    config=json.loads((ROOT/'config.json').read_text());assert config['paper_only'] and config['broker_orders_enabled'] is False
    baseline=json.loads((ROOT/'reference/native_source.json').read_text());base=completed(baseline);raw=completed(source)
    assert len(raw)>=len(base) and np.all(np.diff(raw[:,0])>0) and np.all(raw[:,0]%3600==0)
    assert np.isfinite(raw).all() and np.all(raw[:,1:5]>0)
    assert np.all(raw[:,3]<=np.minimum(raw[:,1],raw[:,4])) and np.all(raw[:,2]>=np.maximum(raw[:,1],raw[:,4]))
    past=raw[raw[:,0]<=base[-1,0]]
    assert past.shape==base.shape and np.array_equal(past[:,:5],base[:,:5]),'Frozen native OHLC history changed; retaining previous publication'
    v=engine.indicators(raw);events,cycles=engine.scan(v)
    assert [e['index'] for e in events]==engine.independent(v)
    start=engine.epoch('2026-01-01');events=[e for e in events if raw[e['index'],0]>=start]
    with (ROOT/'reference/formations.csv').open(newline='',encoding='utf-8') as f:reference=list(csv.DictReader(f))
    archived=[e for e in events if raw[e['index'],0]<=base[-1,0]]
    assert len(archived)==len(reference)==55,'Baseline formation count changed'
    for event,ref in zip(archived,reference):
        i=event['index'];side='BUY' if event['side']==1 else 'SELL'
        assert label(raw[i,0])==ref['signal_bar_open_native'] and side==ref['direction']
        assert event['known_persistence']==int(ref['known_cluster_bars'])
        assert abs(float(v['e'][i,0])-float(ref['ema10']))<1e-10
    points=sorted(set([e['index'] for e in events[::max(1,len(events)//12)]]+[len(raw)-1]))
    full,_=engine.scan(v)
    for i in points:assert engine.scan(engine.indicators(raw[:i+1]))[0]==[e for e in full if e['index']<=i]
    allraw=np.array(source['bars'],dtype=float);bytime={int(r[0]):r for r in allraw};entries=[]
    for event in events:
        i=event['index'];r=raw[i];sg=event['side'];e=v['e'][i];a=v['atr'][i];slopes=(e-v['e'][i-3])/(3*a)
        following=bytime.get(int(r[0])+3600);later=any(t>int(r[0]) for t in bytime)
        status='OBSERVED_NEXT_OPEN_PROXY' if following is not None else 'CANCELLED_GAP' if later else 'PENDING_NEXT_BAR'
        up=sum(v['c'][k]>v['c'][k-1] for k in range(i-2,i+1));down=sum(v['c'][k]<v['c'][k-1] for k in range(i-2,i+1))
        lower=sum(v['h'][k]<v['h'][k-1] and v['l'][k]<v['l'][k-1] for k in range(i-2,i+1))
        entries.append({'id':f'USDJPY_H1_E1_{int(r[0])}_{sg}','direction':'BUY' if sg==1 else 'SELL',
          'signal_epoch':int(r[0]),'signal_bar_open':label(r[0]),'signal_available_at':label(r[0]+3600),
          'entry_time':label(r[0]+3600) if following is not None else None,'entry_price':float(following[1]) if following is not None else None,
          'entry_status':status,'phase':'first_outside' if event['first_outside'] else 'inside','N':event['known_persistence'],
          'cluster_start':label(raw[event['cycle_start'],0]),'min_depth':event['min_width_so_far'],
          'depth':float(v['wa'][i]),'ema10':float(e[0]),'ema20':float(e[1]),'ema50':float(e[2]),'atr14':float(a),
          'slope10':float(slopes[0]),'slope20':float(slopes[1]),'slope50':float(slopes[2]),
          'width_growth':float(v['width'][i]-v['width'][i-1]),'close_minus_ema10':float(r[4]-e[0]),
          'body':float(r[4]-r[1]),'close_location':float((r[4]-r[3])/(r[2]-r[3])),
          'directional_closes3':int(up if sg==1 else down),'lower_pairs3':int(lower),
          'performance_status':'NOT_EVALUATED','origin':'Historical reconstruction; not an executed trade'})
    candles=[{'time':int(r[0]),'open_time':label(r[0]),'close_time':label(r[0]+3600),'open':float(r[1]),'high':float(r[2]),'low':float(r[3]),'close':float(r[4]),
      'ema10':float(v['e'][i,0]),'ema20':float(v['e'][i,1]),'ema50':float(v['e'][i,2]),'atr14':float(v['atr'][i]),'depth':float(v['wa'][i]),'cluster':bool(v['qual'][i])} for i,r in enumerate(raw)]
    last=candles[-1];fresh=source['extraction']['fresh_against_tick'];forming=None
    remaining=allraw[allraw[:,0]>raw[-1,0]]
    if fresh and len(remaining):
        r=remaining[0];forming={'time':int(r[0]),'open':float(r[1]),'high':float(r[2]),'low':float(r[3]),'close':float(r[4]),'complete':False}
    return {'version':'USDJPY_H1_E1_v0.2','symbol':'USDJPY.pro','point':.001,'pip':.01,'timeframe':'H1',
      'generated_at':stamp(),'latest_completed_h1':last['close_time'],'latest_completed_open':last['open_time'],
      'quote_broker_time':label(source['extraction']['latest_tick_epoch']),'candles':candles,'entries':entries,'forming':forming,
      'health':{'state':'FROZEN_REPLAY' if offline else 'OK' if fresh else 'STALE_NATIVE_SOURCE','refreshed_at':stamp()},
      'current':{'ema_order':'BULLISH' if last['ema10']>last['ema20']>last['ema50'] else 'BEARISH' if last['ema10']<last['ema20']<last['ema50'] else 'MIXED',
        'depth':last['depth'],'converged':last['cluster'],'last_confirmation':entries[-1] if entries else None},
      'meta':{'frozen':True,'status':'FROZEN_RESEARCH_BASELINE','timeframe':'H1','ema_periods':[10,20,50],'cluster_width_atr':.5,
        'performance_status':'NOT_EVALUATED','paper_only':True,'broker_orders_enabled':False,'warmup_start':'2025-10-01',
        'clock':'Native broker labels; historical UTC/EAT conversion unverified','refresh_minutes':15,
        'freeze_manifest_sha256':sha(ROOT/'freeze_manifest.json'),'source_sha256':hashlib.sha256(json.dumps(source,separators=(',',':')).encode()).hexdigest()},
      'validation':{'baseline_formations_exact':55,'baseline_buy':34,'baseline_sell':21,'baseline_ohlc_exact':len(base),
        'independent_scan_exact':True,'causal_prefix_checks':len(points),'forming_candle_excluded':True}}
def main():
    offline='--offline' in sys.argv
    source=json.loads((ROOT/'reference/native_source.json').read_text()) if offline else read_live()
    out=project(source,offline)
    atomic(ROOT/'site'/('usdjpy-replay.json' if offline else 'usdjpy-data.json'),out)
    atomic(ROOT/'site/usdjpy-acceptance.json',out['validation'])
    atomic(ROOT/'site/usdjpy-rules.json',{'formula':engine.CFG,'freeze_manifest':json.loads((ROOT/'freeze_manifest.json').read_text())})
    if not offline:atomic(ROOT/'latest_native.json',source)
    print(json.dumps({'formations':len(out['entries']),'asof':out['latest_completed_h1'],'health':out['health'],'validation':out['validation']}),flush=True)
if __name__=='__main__':main()
