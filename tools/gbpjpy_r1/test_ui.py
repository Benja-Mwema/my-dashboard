import sys,json
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root.parent/'vendor'))
from playwright.sync_api import sync_playwright
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8124'
errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe')
 page=b.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(base+'/index.html?asset=GBPJPY.pro');page.wait_for_url('**/gbpjpy.html');page.wait_for_selector('#entries tr')
 assert page.locator('#entries tr').count()==15
 assert page.locator('#count').inner_text()=='15'
 assert page.locator('#rate').inner_text()=='42.9%'
 assert page.locator('#gross').inner_text()=='181.93'
 assert page.locator('#directionArrow').is_hidden()
 page.locator('#entries button').last.click()
 assert '2026-10-01 20:00:00' in page.locator('#detailTitle').inner_text()
 assert page.locator('#emas tr').count()==3
 assert 'Modeled touch' in page.locator('#detail').inner_text()
 assert page.locator('#chart svg').count()==1
 page.screenshot(path=str(root/'desktop.png'),full_page=True)
 page.select_option('#month','2026-11');assert page.locator('#entries tr').count()==3
 page.select_option('#dataset','gbpjpy-data.json');page.wait_for_function("document.querySelector('#sourceStatus').textContent !== 'Frozen acceptance replay'")
 assert page.locator('#state').inner_text() in ['C1 pending','C2 pending','Rejected','Confirmed BUY','Confirmed SELL','Waiting']
 assert 'not streamed' in page.locator('#notice').inner_text()
 page.set_viewport_size({'width':390,'height':844})
 assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
 page.screenshot(path=str(root/'mobile.png'),full_page=True)
 page.select_option('#instrument','XAUUSD.pro');page.wait_for_url('**/index.html?asset=XAUUSD.pro');page.wait_for_selector('#entries tr')
 assert page.locator('#entries tr').count()==71
 page.select_option('#assetClass','indices');page.wait_for_function("document.querySelector('#direction').textContent==='NOT AVAILABLE'")
 assert not errors,errors
 b.close()
(root/'ui_results.json').write_text(json.dumps({'base':base,'replay_rows':15,'replay_rate':'42.9%','gross_pips':181.93,'checks':['entry details','C0 C1 C2 EMA table','modeled exits','month filter','latest candidate','snapshot disclosure','390px no overflow','XAU 71 entries preserved','unpublished index isolation'],'js_errors':errors},indent=2))
print('PASS: GBPJPY replay/latest, desktop/mobile, XAU and indices; no JavaScript errors')
