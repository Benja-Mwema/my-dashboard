from pathlib import Path
import sys,json,threading,http.server,functools,csv,io,math
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'vendor'))
from playwright.sync_api import sync_playwright
CANDIDATES={'nas100':7,'cac40':8,'jpn225':8,'aus200':12}
ROUTES=list(CANDIDATES)+['index','ws30','dax40','eurusd','gbpusd','eurjpy','gbpjpy','cadjpy','audcad']
class QuietHandler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
def main(base=None):
 public=bool(base)
 if base is None:
  handler=functools.partial(QuietHandler,directory=str(ROOT/'preview'))
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
 results=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
  for name in ROUTES:
   page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(base+name+'.html',wait_until='domcontentloaded',timeout=60000)
   page.wait_for_function('window.AurumCharts && AurumCharts.getState().bars>0',timeout=60000)
   assert page.locator('.aurum-topnav-link').count()==13,(name,'navigation')
   assert page.locator('.aurum-nav-category').all_text_contents()==['Metals','Indices','Currencies']
   assert page.locator('.aurum-topnav-link[aria-current="page"]').count()==1
   timeframe='M30' if name in ['eurusd','gbpusd','eurjpy'] else 'H1'
   assert timeframe in page.locator('.ac-tag').inner_text()
   assert page.evaluate('(s)=>AurumCharts.getBars().every(b=>b.end-b.t===s)',1800 if timeframe=='M30' else 3600)
   if name in CANDIDATES:
    contract=json.loads((ROOT/'runtime/candidates.json').read_text(encoding='utf-8'))['candidates'][name]
    assert page.locator('.heading .eyebrow').inner_text()==contract['formation'].upper(),(name,'formation text encoding')
    expected=json.loads((ROOT/'site'/(name+'-replay.json')).read_text(encoding='utf-8'))
    page.wait_for_function('AurumCharts.getState().currentContext && AurumCharts.getState().forming',timeout=30000)
    assert page.locator('#instrument option').count()==13
    assert page.locator('#instrument optgroup').evaluate_all('(xs)=>xs.map(x=>x.label)')==['Metals','Indices','Currencies']
    assert any(x in page.locator('#researchStatus').inner_text().lower() for x in ['pending','unproven'])
    page.locator('#auSaved').click();page.wait_for_function('(n)=>document.getElementById("auCount").textContent===String(n)',arg=CANDIDATES[name])
    page.wait_for_function('!AurumCharts.getState().currentContext')
    for target in ['2','3']:
     page.locator('#targetATR').select_option(target)
     total=sum(e['outcomes'][target]['net_R'] for e in expected['entries'])
     wins=sum(e['outcomes'][target]['status']=='WIN' for e in expected['entries'])
     page.wait_for_function('(v)=>Math.abs(Number(document.getElementById("auValue").textContent)-v)<.011',arg=total)
     assert abs(float(page.locator('#auRate').inner_text().rstrip('%'))-100*wins/CANDIDATES[name])<.011
     with page.expect_download() as dl:page.locator('#auExport').click()
     exported=list(csv.DictReader(io.StringIO(Path(dl.value.path()).read_text(encoding='utf-8-sig'))))
     assert len(exported)==CANDIDATES[name] and all(e['target_ATR']==target for e in exported)
     assert math.isclose(sum(float(e['net_R']) for e in exported),total,abs_tol=1e-8)
     for e in exported:
      sign=1 if e['direction']=='BUY' else -1
      assert math.isclose(float(e['target']),float(e['entry_price'])+sign*int(target)*float(e['ATR']),abs_tol=1e-7)
     page.locator('#entries button').first.click();page.wait_for_timeout(300)
     assert page.locator('#acWhyBody tr').count()>=5
     assert page.locator('#acWhyBody .fail').count()==0,(name,page.locator('#acWhyBody').inner_text())
    page.locator('#targetATR').select_option('2')
    with page.expect_download() as dl:page.locator('#auSaveChart').click()
    chart=Path(dl.value.path()).read_text();assert '<svg' in chart and 'H1' in chart
    page.locator('#auDataDetails summary').click()
    with page.expect_download() as dl:page.locator('#auRecordDownload').click()
    record=json.loads(Path(dl.value.path()).read_text());assert record['id'].startswith(name.upper()+'_')
    page.locator('#auSearch').fill('no-such-entry-qzr');page.wait_for_function("document.getElementById('auCount').textContent==='0'")
    assert 'No signals match' in page.locator('#entries').inner_text()
    page.locator('#auReset').click();page.wait_for_function('(n)=>document.getElementById("auCount").textContent===String(n)',arg=CANDIDATES[name])
    page.locator('#cohort').select_option('post_research');page.wait_for_function("document.getElementById('auCount').textContent==='0'")
    page.locator('#cohort').select_option('all')
    page.locator('#acZoomIn').click();page.locator('#acPanLeft').click();page.locator('#acMode').select_option('journey')
    page.locator('#dataset').select_option(name+'-data.json');page.wait_for_function('AurumCharts.getState().currentContext')
    page.locator('#acFocus').select_option('current');page.locator('#acMode').select_option('formation')
    if name=='nas100':
     page.locator('#auChartSection').scroll_into_view_if_needed();page.screenshot(path=str(ROOT/('public_desktop.png' if public else 'preview_desktop.png')))
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(250)
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),name+' mobile overflow'
   if name=='nas100':page.screenshot(path=str(ROOT/('public_mobile.png' if public else 'preview_mobile.png')))
   assert not errors,(name,errors)
   result=dict(page=name,timeframe=timeframe,grouped_routes=13,charts=True,mobile_overflow=False,javascript_errors=errors,candidate_checks=name in CANDIDATES)
   results.append(result);print(json.dumps(result),flush=True);page.close()
  browser.close()
 (ROOT/('public_acceptance.json' if public else 'ui_acceptance.json')).write_text(json.dumps(results,indent=2))
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else None)
