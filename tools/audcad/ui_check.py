import sys,json
from pathlib import Path
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'vendor'))
from playwright.sync_api import sync_playwright
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8124'
errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe');page=b.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(base+'/index.html?asset=AUDCAD.pro');page.wait_for_url('**/audcad.html');page.wait_for_selector('#entries tr');page.select_option('#dataset','audcad-replay.json');page.wait_for_function("document.querySelector('#quality').textContent==='Frozen replay'")
 assert page.locator('#entries tr').count()==58;assert page.locator('#gross').inner_text()=='180.0';assert page.locator('#rate').inner_text()=='52.6%';assert page.locator('#movement').inner_text()=='47 / 58';assert page.locator('#chart svg').count()==1
 page.locator('#entries button').last.click();assert page.locator('#features td').count()==8
 page.screenshot(path=str(r/'desktop.png'),full_page=True)
 page.select_option('#side','SELL');assert page.locator('#entries tr').count()==62;assert page.locator('#rate').inner_text()=='50.0%';assert '1 unscored' in page.locator('#excluded').inner_text()
 page.select_option('#month','2026-04');assert 'UNSCORED' in page.locator('#entries').inner_text()
 with page.expect_download() as dl:page.locator('#export').click()
 assert dl.value.suggested_filename=='AUDCAD_SELL_2026-04.csv'
 page.select_option('#dataset','audcad-data.json');page.wait_for_function("document.querySelector('#quality').textContent!=='Frozen replay'");assert 'detected' in page.locator('#detail').inner_text()
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(r/'mobile.png'),full_page=True)
 page.select_option('#instrument','GBPJPY.pro');page.wait_for_url('**/gbpjpy.html');page.wait_for_selector('#entries tr');assert page.locator('#entries tr').count()==15
 page.select_option('#instrument','XAUUSD.pro');page.wait_for_url('**/index.html?asset=XAUUSD.pro');page.wait_for_selector('#entries tr');assert page.locator('#entries tr').count()>=71
 assert not errors,errors;b.close()
(r/'ui_validation.json').write_text(json.dumps({'status':'PASS','base':base,'checks':['BUY fixtures','SELL fixtures and unscored','MACD SMA9 and EMA table','monthly CSV export','latest detection labels','mobile no overflow','GBPJPY and XAU navigation'],'errors':errors},indent=2));print('PASS: AUDCAD desktop/mobile, fixtures, export and other instruments')
