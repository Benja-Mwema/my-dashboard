from pathlib import Path
import sys,json,threading,http.server,functools
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parents[1]/'vendor'))
from playwright.sync_api import sync_playwright

def main():
 public=len(sys.argv)>1
 if public:base=sys.argv[1]
 else:
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT/'preview')))
  threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
 results=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
  for width,height in [(1440,1000),(390,844)]:
   page=browser.new_page(viewport={'width':width,'height':height},accept_downloads=True);errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(base+'usdjpy.html',wait_until='networkidle',timeout=60000)
   page.wait_for_function("window.AurumCharts && AurumUI.kind==='usdjpy' && AurumCharts.getState().bars>0 && document.body.dataset.aurumView==='monitor'",timeout=60000)
   assert page.locator('#avMonitor').is_visible() and page.locator('#acPlot').is_visible()
   assert page.locator('.av-tabs').count()==1 and page.locator('.ac-workbench').count()==1
   assert page.locator('#chart svg').count()==0,'Separate custom chart remains'
   assert 'Performance validation pending' in page.locator('#avModel').inner_text()
   source=page.evaluate('JSON.stringify(AurumUI.getData())')
   parity=page.evaluate("""()=>{const d=AurumUI.getData(),b=new Map(AurumCharts.getBars().map(x=>[x.t,x]));return d.candles.every(c=>{const x=b.get(c.time);return x&&['open','high','low','close','ema10','ema20','ema50','atr14'].every(k=>x[k]===c[k])&&x.width===c.depth;});}""")
   assert parity,'Frozen OHLC/EMA/ATR values changed in shared chart'
   page.screenshot(path=str(ROOT/f'usdjpy_shared_{width}.png'),full_page=True)
   v=page.evaluate('AurumCharts.getState().view');page.locator('#acPanLeft').click();page.wait_for_timeout(100);assert page.evaluate('AurumCharts.getState().view.start')<v['start']
   v=page.evaluate('AurumCharts.getState().view');page.locator('#acZoomIn').click();page.wait_for_timeout(100);n=page.evaluate('AurumCharts.getState().view');assert n['end']-n['start']<v['end']-v['start']
   page.locator('#acLayer_ema50').uncheck();assert page.locator('#acPlot [data-layer="ema50"]').count()==0
   page.locator('#acLayer_ema50').check();assert page.locator('#acPlot [data-layer="ema50"]').count()>0
   page.locator('#acPlot').click();page.locator('#acPlot').press('ArrowRight');assert 'EMA50' in page.locator('#acCandle').inner_text()
   page.locator('.av-tabs a[href="#research"]').click();page.wait_for_function("document.body.dataset.aurumView==='research'")
   count=page.evaluate('AurumUI.getData().entries.length');assert int(page.locator('#auCount').inner_text())==count
   assert page.locator('#auValue').inner_text()=='H1 E1 v0.2' and page.locator('#auRate').inner_text()=='—'
   page.select_option('#side','BUY');page.wait_for_timeout(250)
   buys=page.evaluate("AurumUI.getData().entries.filter(e=>e.direction==='BUY').length");assert int(page.locator('#auCount').inner_text())==buys
   page.locator('#entries [data-id]').first.click();page.wait_for_timeout(200)
   assert page.locator('#acWhyBody .fail').count()==0 and page.locator('#acWhyBody tr').count()>=12
   assert 'Performance not evaluated' in page.locator('#acLifecycle').inner_text()
   page.select_option('#acMode','journey');assert page.locator('#acPlot [data-layer="close"]').count()>0
   page.select_option('#acMode','formation')
   with page.expect_download() as download:page.locator('#auSaveChart').click()
   assert download.value.suggested_filename=='usdjpy_formation.svg'
   assert page.evaluate('JSON.stringify(AurumUI.getData())')==source,'Display controls mutated snapshot'
   page.locator('#auSaved').click();page.wait_for_function("document.getElementById('dataset').value==='usdjpy-replay.json' && document.getElementById('auCount').textContent==='55'")
   page.wait_for_function('!AurumCharts.getState().currentContext')
   assert page.evaluate('AurumCharts.getBars().every(b=>!b.provisional)')
   page.locator('.av-tabs a[href="#audit"]').click();assert page.locator('#avAudit').is_visible()
   assert '0.50' in page.locator('#avAudit').inner_text()
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Page overflows viewport'
   assert not errors,errors
   results.append({'width':width,'shared_chart':True,'indicator_parity':True,'pan_zoom_layers':True,'candle_inspection':True,'entry_evidence':True,'svg_export':True,'snapshot_unchanged':True,'frozen_replay':55,'no_overflow':True,'errors':errors})
   page.close()
  page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  for name in ['index','xaueur','gbpjpy','audcad','ws30','dax40','cadjpy','eurjpy','gbpusd','eurusd','nas100','cac40','jpn225','aus200']:
   page.goto(base+name+'.html',wait_until='domcontentloaded',timeout=60000)
   page.wait_for_function('window.AurumCharts && AurumCharts.getState().bars>0',timeout=60000)
   assert page.locator('.ac-workbench').count()==1
   assert not errors,(name,errors)
   results.append({'route':name,'shared_chart_loaded':True,'errors':[]})
  browser.close()
 (ROOT/('public_ui_acceptance.json' if public else 'ui_acceptance.json')).write_text(json.dumps(results,indent=2))
 print(json.dumps(results),flush=True)
if __name__=='__main__':main()
