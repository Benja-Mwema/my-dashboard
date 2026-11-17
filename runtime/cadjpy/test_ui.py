from pathlib import Path
import sys,json,threading,http.server,functools
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'vendor'))
from playwright.sync_api import sync_playwright
def main(base=None):
 if base is None:
  handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT/'preview'))
  server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
 results=[]
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
  for name in ['cadjpy','index','gbpjpy','audcad','ws30','dax40']:
   page=b.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(base+name+'.html',wait_until='domcontentloaded',timeout=60000)
   page.wait_for_function('window.AurumCharts && AurumCharts.getState().bars>0',timeout=60000)
   assert page.locator('.aurum-topnav-link').count()==6
   if name=='cadjpy':
    page.locator('#auSaved').click();page.wait_for_function("document.getElementById('dataset').value==='cadjpy-replay.json' && document.getElementById('auCount').textContent==='49'")
    page.locator('#side').select_option('BUY');page.wait_for_function("document.getElementById('auCount').textContent==='28'")
    assert page.locator('#auRate').inner_text()=='57.14%'
    page.locator('#phase').select_option('first_outside');page.wait_for_function("document.getElementById('auCount').textContent==='8'")
    page.locator('#adverse').select_option('pass');page.wait_for_function("document.getElementById('auCount').textContent==='7'")
    page.locator('#horizon').select_option('12');page.locator('#phase').select_option('all');page.locator('#adverse').select_option('all');page.locator('#cost').select_option('2')
    page.wait_for_function("document.getElementById('auRate').textContent==='46.43%'")
    page.locator('#cost').select_option('0');page.locator('#horizon').select_option('24');page.locator('#side').select_option('SELL')
    page.wait_for_function("document.getElementById('auCount').textContent==='21'")
    assert page.locator('#auRate').inner_text()=='52.38%'
    page.locator('#entries button').first.click();page.wait_for_timeout(300)
    assert page.locator('#acWhyBody tr').count()>=12
    assert page.locator('#acWhyBody .fail').count()==0
    with page.expect_download() as dl:page.locator('#auExport').click()
    text=Path(dl.value.path()).read_text(encoding='utf-8-sig');assert 'adverse_pips' in text and len(text.splitlines())==22
    with page.expect_download() as dl:page.locator('#auSaveChart').click()
    assert '<svg' in Path(dl.value.path()).read_text()
    page.locator('#auRecordDownload').click(force=True) if False else None
    page.locator('#auSearch').fill('no-such-entry-xyz');page.wait_for_function("document.getElementById('auCount').textContent==='0'")
    assert 'No signals match' in page.locator('#entries').inner_text()
    page.locator('#auReset').click();page.wait_for_function("document.getElementById('auCount').textContent==='49'")
    page.locator('#acZoomIn').click();page.locator('#acPanLeft').click();page.locator('#acMode').select_option('journey')
    page.screenshot(path=str(ROOT/'desktop.png'),full_page=True)
   page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(400)
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),name+' mobile overflow'
   if name=='cadjpy':page.screenshot(path=str(ROOT/'mobile.png'),full_page=True)
   assert not errors,(name,errors)
   results.append(dict(page=name,charts=True,six_routes=True,mobile_overflow=False,javascript_errors=errors));page.close()
  b.close()
 (ROOT/('public_acceptance.json' if base.startswith('https') else 'ui_acceptance.json')).write_text(json.dumps(results,indent=2));print(json.dumps(results),flush=True)
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else None)
