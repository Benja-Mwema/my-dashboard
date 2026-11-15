from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'ws30.html';s=p.read_text(encoding='utf-8')
start=s.index('<section class="panel" id="detail">');end=s.index('<section class="panel" id="paperJournal">')
detail=s[start:end];s=s[:start]+s[end:]
pos=s.index('<section class="panel"><div class="panelTitle"><div><div class="eyebrow">ENTRY REGISTER')
s=s[:pos]+detail+s[pos:]
s=s.replace('<th>Research R</th><th></th>','<th>Research R</th><th>TP / SL</th><th>Exit time</th><th>Gross index units</th><th>Sampled favourable close move</th><th>Overlaps</th><th>Detection / origin</th><th></th>')
p.write_text(s,encoding='utf-8')
# Extend the feature source; regenerate only the appended feature region.
p=ROOT/'tools/ws30_features.js';s=p.read_text(encoding='utf-8')
s=s.replace("let indicators=[], requestSequence=0, lastGood=null;","let indicators=[], requestSequence=0, lastGood=null;\nlet moveCache=new Map();\nfunction sampledMove(r){\n if(moveCache.has(r.id))return moveCache.get(r.id);\n const closes=data.candles.filter(b=>b.time>=r.entry_time&&b.close_time<(r.exit_time||r.horizon_end)).map(b=>sign(r)*(b.close-r.entry_reference));\n const ep=exitPrice(r);if(ep!==null)closes.push(sign(r)*(ep-r.entry_reference));\n const value=Math.max(0,...closes);moveCache.set(r.id,value);return value;\n}\nfunction overlaps(r){return data.signals.filter(z=>z.id!==r.id&&z.entry_time<=(r.exit_time||r.horizon_end)&&(z.exit_time||z.horizon_end)>=r.entry_time);}")
s=s.replace("originalRegister();selectedMetrics();", """originalRegister();selectedMetrics();
 const tableRecords=filtered().sort((a,b)=>a.entry_time.localeCompare(b.entry_time)).reverse();
 [...$('signalRows').children].forEach((tr,i)=>{
  const r=tableRecords[i];if(!r){tr.firstChild.colSpan=15;return;}
  const unit=r.score_final&&isNum(r.score_R_min)?format(r.score_R_min*risk(r),1):'Unresolved';
  for(const v of [format(r.target,1)+' / '+format(r.initial_stop,1),r.exit_time||'Pending',unit,
   format(sampledMove(r),1)+' units / '+format(sampledMove(r)/r.ATR,2)+' ATR',overlaps(r).length,
   r.observed_at||'Historical replay'])tr.insertBefore(el('td',v),tr.lastChild);
 });""")
s=s.replace("const overlap=data.signals.filter(z=>z.id!==r.id&&z.entry_time<=(r.exit_time||r.horizon_end)&&\n  (z.exit_time||z.horizon_end)>=r.entry_time);","const overlap=overlaps(r);")
s=s.replace("evidenceBox($('caseFacts'),'Detection'", "evidenceBox($('caseFacts'),'Sampled favourable close move',format(sampledMove(r),1)+' index units / '+format(sampledMove(r)/r.ATR,2)+' ATR; not intrabar MFE');\n evidenceBox($('caseFacts'),'Detection'")
s=s.replace("add('text',{x:W-R+3,y:y(p)-5","add('text',{x:L+6,y:y(p)-5")
s=s.replace("data=v;lastGood=v;indicators=", "data=v;lastGood=v;moveCache=new Map();indicators=")
s=s.replace("if($('chartTf').value!=='H1')await loadIntrabar();","if($('chartTf').value!=='H1'){ $('riskGraphic').replaceChildren(el('p','Loading verified intrabar evidence…','muted'));await loadIntrabar();}")
s=s.replace("'source_case_id'", "'source_case_id'") # Keep frozen fields as supplied.
p.write_text(s,encoding='utf-8')
j=ROOT/'ws30.js';base=j.read_text(encoding='utf-8').split('/* WS30 feature parity v2:')[0]
j.write_text(base+s,encoding='utf-8')
# The initial upgrade is intentionally one-shot and cannot silently duplicate controls.
p=ROOT/'tools/upgrade_ws30_features.py';s=p.read_text(encoding='utf-8')
s=s.replace("s=p.read_text(encoding='utf-8')","s=p.read_text(encoding='utf-8')\nassert 'id=\"selectionMetrics\"' not in s, 'Already upgraded; edit feature assets directly'",1)
p.write_text(s,encoding='utf-8')
print('Entry inspector moved before ledger; ledger fields complete; chart labels separated.')
