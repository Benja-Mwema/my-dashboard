from pathlib import Path
import sys,json,threading,http.server,functools,re
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'vendor'))
from playwright.sync_api import sync_playwright

def main(base=None):
 public=bool(base)
 if base is None:
  handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT/'preview'))
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
 results=[]
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
  for name in ['eurusd','gbpusd','eurjpy','index','gbpjpy','audcad','ws30','dax40','cadjpy']:
   page=b.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(base+name+'.html',wait_until='domcontentloaded',timeout=60000)
   page.wait_for_function('window.AurumCharts && AurumCharts.getState().bars>0',timeout=60000)
   assert page.locator('.aurum-topnav-link').count()==9,(name,'navigation count')
   assert page.locator('.aurum-topnav-link[href="gbpusd.html"]').count()==1
   timeframe='M30' if name in ['eurjpy','gbpusd','eurusd'] else 'H1'
   assert timeframe in page.locator('.ac-tag').inner_text()
   seconds=1800 if timeframe=='M30' else 3600
   assert page.evaluate('(s)=>AurumCharts.getBars().every(b=>b.end-b.t===s)',seconds),(name,'bar duration')
   if name=='eurusd':
    assert 'Later consistency gate failed' in page.locator('#researchStatus').inner_text()
    assert page.locator('#instrument option').count()==9
    assert page.locator('#side option').count()==2
    page.locator('#auSaved').click();page.wait_for_function("document.getElementById('dataset').value==='eurusd-replay.json' && document.getElementById('auCount').textContent==='53'")
    page.wait_for_function('!AurumCharts.getState().currentContext')
    assert page.locator('#auRate').inner_text()=='59.62%'
    assert page.locator('#auSides').inner_text()=='0 BUY · 53 SELL'
    assert page.locator('#auComplete').inner_text()=='52 / 1'
    assert page.locator('#auValue').inner_text()=='+260.1'
    assert page.locator('#acLayer_ema200').count()==1
    assert re.fullmatch(r'\d+\.\d{5}',page.locator('#entries tr').first.locator('td').nth(4).inner_text())
    page.locator('#month').select_option('2026-07');page.wait_for_function("document.getElementById('auCount').textContent==='4'")
    assert page.locator('#auRate').inner_text()=='25%'
    page.locator('#month').select_option('all');page.locator('#cost').select_option('0');page.wait_for_function("document.getElementById('auRate').textContent==='69.23%'")
    page.locator('#cost').select_option('2');page.locator('#horizon').select_option('6');page.wait_for_function("document.getElementById('auRate').textContent==='57.69%'")
    page.locator('#horizon').select_option('24');page.wait_for_function("document.getElementById('auRate').textContent==='57.69%'")
    page.locator('#horizon').select_option('12');page.locator('#entries button').first.click();page.wait_for_timeout(400)
    assert page.locator('#acWhyBody tr').count()>=12 and page.locator('#acWhyBody .fail').count()==0
    assert 'EMA200' in page.locator('#acWhyBody').inner_text() and '1800' in page.locator('#acWhyBody').inner_text()
    assert page.locator('path[data-layer="ema200"]').count()>0
    with page.expect_download() as dl:page.locator('#auExport').click()
    csv=Path(dl.value.path()).read_text(encoding='utf-8-sig');assert 'pullback_age' in csv and len(csv.splitlines())==54 and 'CANCELLED_GAP' in csv
    with page.expect_download() as dl:page.locator('#auSaveChart').click()
    svg=Path(dl.value.path()).read_text();assert '<svg' in svg and 'M30' in svg and 'ema200' in svg
    page.locator('#auDataDetails summary').click()
    with page.expect_download() as dl:page.locator('#auRecordDownload').click()
    rec=json.loads(Path(dl.value.path()).read_text());assert rec['id'].startswith('EURUSD_E2S_M30_')
    page.locator('#auSearch').fill('2026-10-10 00:00');page.wait_for_function("document.getElementById('auCount').textContent==='1'")
    assert 'CANCELLED_GAP' in page.locator('#entries').inner_text()
    page.locator('#auSearch').fill('no-such-entry-xyz');page.wait_for_function("document.getElementById('auCount').textContent==='0'")
    assert 'No signals match' in page.locator('#entries').inner_text()
    page.locator('#auReset').click();page.wait_for_function("document.getElementById('auCount').textContent==='53'")
    page.locator('#acZoomIn').click();page.locator('#acPanLeft').click();page.locator('#acMode').select_option('journey')
    page.locator('#dataset').select_option('eurusd-data.json');page.wait_for_timeout(700)
    page.locator('#acFocus').select_option('current');page.locator('#acMode').select_option('formation')
    page.locator('#auChartSection').scroll_into_view_if_needed();page.screenshot(path=str(ROOT/('eurusd_public_desktop.png' if public else 'eurusd_desktop.png')))
   if name=='gbpusd':
    page.wait_for_function('AurumCharts.getState().currentContext && AurumCharts.getState().forming',timeout=30000)
    assert 'M30' in page.locator('#acLiveStatus').inner_text()
    assert page.locator('#instrument option').count()==9
    page.locator('#auSaved').click();page.wait_for_function("document.getElementById('dataset').value==='gbpusd-replay.json' && document.getElementById('auCount').textContent==='109'")
    page.wait_for_function('!AurumCharts.getState().currentContext')
    assert page.locator('#auRate').inner_text()=='48.62%'
    assert page.locator('#auSides').inner_text()=='51 BUY · 58 SELL'
    assert re.fullmatch(r'\d+\.\d{5}',page.locator('#entries tr').first.locator('td').nth(4).inner_text())
    page.locator('#side').select_option('BUY');page.wait_for_function("document.getElementById('auCount').textContent==='51'")
    assert page.locator('#auRate').inner_text()=='43.14%'
    page.locator('#cost').select_option('2');page.wait_for_function("document.getElementById('auRate').textContent==='35.29%'")
    page.locator('#side').select_option('SELL');page.wait_for_function("document.getElementById('auCount').textContent==='58'")
    assert page.locator('#auRate').inner_text()=='48.28%'
    page.locator('#side').select_option('all');page.locator('#month').select_option('2026-07');page.wait_for_function("document.getElementById('auRate').textContent==='81.82%'")
    assert page.locator('#auCount').inner_text()=='11'
    page.locator('#month').select_option('all');page.locator('#cost').select_option('0');page.locator('#horizon').select_option('24');page.wait_for_function("document.getElementById('auRate').textContent==='53.21%'")
    page.locator('#cost').select_option('2');page.wait_for_function("document.getElementById('auRate').textContent==='48.62%'")
    assert '1 flat' in page.locator('#auRateNote').inner_text()
    page.locator('#horizon').select_option('12');page.locator('#cost').select_option('0');page.locator('#entries button').first.click();page.wait_for_timeout(400)
    assert page.locator('#acWhyBody tr').count()>=12 and page.locator('#acWhyBody .fail').count()==0
    assert '1800' in page.locator('#acWhyBody').inner_text()
    with page.expect_download() as dl:page.locator('#auExport').click()
    csv=Path(dl.value.path()).read_text(encoding='utf-8-sig');assert 'adverse_pips' in csv and len(csv.splitlines())==110
    with page.expect_download() as dl:page.locator('#auSaveChart').click()
    svg=Path(dl.value.path()).read_text();assert '<svg' in svg and 'M30' in svg
    page.locator('#auDataDetails summary').click()
    with page.expect_download() as dl:page.locator('#auRecordDownload').click()
    rec=json.loads(Path(dl.value.path()).read_text());assert rec['id'].startswith('GBPUSD_E1_M30_')
    page.locator('#auSearch').fill('no-such-entry-xyz');page.wait_for_function("document.getElementById('auCount').textContent==='0'")
    assert 'No signals match' in page.locator('#entries').inner_text()
    page.locator('#auReset').click();page.wait_for_function("document.getElementById('auCount').textContent==='109'")
    # Phase counts independently obtained from the analysis ledger, not the page.
    expected=json.loads((ROOT/'ui_expected.json').read_text())
    page.locator('#phase').select_option('inside');page.wait_for_function('(n)=>document.getElementById("auCount").textContent===String(n)',arg=expected['inside'])
    page.locator('#phase').select_option('first_outside');page.wait_for_function('(n)=>document.getElementById("auCount").textContent===String(n)',arg=expected['first_outside'])
    page.locator('#auReset').click();page.locator('#acZoomIn').click();page.locator('#acPanLeft').click();page.locator('#acMode').select_option('journey')
    page.locator('#dataset').select_option('gbpusd-data.json');page.wait_for_function('AurumCharts.getState().currentContext')
    page.locator('#acFocus').select_option('current');page.locator('#acMode').select_option('formation')
    page.locator('#auChartSection').scroll_into_view_if_needed();page.screenshot(path=str(ROOT/('public_desktop.png' if public else 'desktop.png')))
   if name=='cadjpy':
    page.locator('#auSaved').click();page.wait_for_function("document.getElementById('auCount').textContent==='49'")
    page.locator('#side').select_option('BUY');page.wait_for_function("document.getElementById('auCount').textContent==='28'")
    assert page.locator('#auRate').inner_text()=='57.14%'
   if name=='eurjpy':
    page.locator('#auSaved').click();page.wait_for_function("document.getElementById('auCount').textContent==='119'")
    assert page.locator('#auRate').inner_text()=='55.46%'
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(400)
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),name+' mobile overflow'
   if name in ['gbpusd','eurusd']:
    page.locator('#auChartSection').scroll_into_view_if_needed();page.screenshot(path=str(ROOT/('public_mobile.png' if public else 'mobile.png')))
   assert not errors,(name,errors)
   results.append(dict(page=name,timeframe=timeframe,charts=True,nine_routes=True,mobile_overflow=False,javascript_errors=errors));page.close()
  b.close()
 (ROOT/('public_acceptance.json' if public else 'ui_acceptance.json')).write_text(json.dumps(results,indent=2));print(json.dumps(results),flush=True)
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else None)
