from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'ws30.html';s=p.read_text(encoding='utf-8')
assert 'id="inspectFrozen"' not in s
s=s.replace('<button id="reload"','<button id="inspectFrozen" type="button" aria-controls="detail">Inspect frozen entries</button>\n<button id="reload"',1)
s=s.replace('ws30.js?v=features-2','ws30.js?v=frozen-inspect-3')
p.write_text(s,encoding='utf-8')
handler="""
$('inspectFrozen').onclick=async()=>{
 const button=$('inspectFrozen');button.disabled=true;
 try{
  $('dataset').value='ws30-replay.json';
  // Preserve cohort/model/direction, but reveal entries hidden by outcome/month.
  $('outcomeFilter').value='all';$('monthFilter').value='all';
  $('chartTf').value='H1';chosen=null;
  await refreshFeatures();
  if(!data||$('dataset').value!=='ws30-replay.json')return;
  if(!filtered().length){$('ruleFilter').value='all';$('sideFilter').value='all';register();detail();}
  if(chosen){$('detail').scrollIntoView({behavior:'smooth',block:'start'});$('selected').focus({preventScroll:true});}
 }finally{button.disabled=false;}
};
"""
for name in ['ws30.js','tools/ws30_features.js']:
 p=root/name;s=p.read_text(encoding='utf-8')
 assert "$('inspectFrozen').onclick" not in s
 s=s.replace('instrumentPicker();refreshFeatures();',handler+'\ninstrumentPicker();refreshFeatures();')
 p.write_text(s,encoding='utf-8')
print('Frozen inspection shortcut added.')
