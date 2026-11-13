import sys
from pathlib import Path
r=Path(__file__).resolve().parent
sys.path.insert(0,str(r.parent/'vendor'))
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
 page=b.new_page(viewport={'width':390,'height':844})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 if '--local' in sys.argv:
  for name in ['audcad.html','audcad.js']:
   page.route('**/'+name+'*',lambda route,request,n=name:route.fulfill(path=str(r/n),content_type='text/html' if n.endswith('html') else 'application/javascript'))
 page.goto('https://my-dashboard-olo8.onrender.com/audcad.html')
 page.wait_for_selector('#entries tr')
 assert page.locator('#side').input_value()=='all'
 page.select_option('#dataset','audcad-replay.json')
 page.wait_for_function("document.querySelector('#quality').textContent==='Frozen replay'")
 assert page.locator('#count').inner_text()=='119'
 assert set(page.locator('#entries tr td:first-child').all_text_contents())=={'BUY','SELL'}
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.select_option('#exitMode','frozen')
 assert page.locator('#gross').inner_text()=='180.0'
 assert page.locator('#rate').inner_text()=='51.3%'
 page.select_option('#side','BUY');assert page.locator('#count').inner_text()=='58'
 page.select_option('#side','SELL');assert page.locator('#count').inner_text()=='61'
 page.select_option('#side','all');page.click('#latest')
 assert page.evaluate("document.querySelector('#selected').value===rows().at(-1).id")
 page.select_option('#exitMode','overlay');assert page.locator('#chart svg').count()==1
 page.screenshot(path=str(r/'combined_mobile.png'),full_page=True)
 assert not errors,errors
 b.close()
print('PASS: combined totals, BUY/SELL filters, latest selection, chart, mobile and frozen parity')
