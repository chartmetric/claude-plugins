import fs from 'fs';
import { createRequire } from 'module'; const postcss = createRequire(process.env.REPO + '/package.json')('postcss');
const [inp,out]=process.argv.slice(2);
const root=postcss.parse(fs.readFileSync(inp,'utf8'));
const keep=new Set('us gb kr jp de fr es br mx ca au in cn it se nl ng za ar id'.split(' '));
const moodOk=/^\.(border-cm-mood|bg-cm-mood|hover\\:bg-cm-mood)[a-z-]*(:hover)?$/;
root.walkRules(r=>{
  if(r.parent && r.parent.type==='atrule' && /keyframes/.test(r.parent.name)) return;
  const sel=r.selector;
  const fl=[...sel.matchAll(/\.fi-([a-z0-9-]+)/g)].map(m=>m[1]);
  if(fl.length && !fl.some(f=>keep.has(f))){r.remove();return;}
  if(sel.includes('cm-mood') && !sel.includes(':root')){
    const ok=r.selectors.filter(s=>moodOk.test(s.trim()));
    if(!ok.length){r.remove();return;} r.selectors=ok;
  }
  if(sel.trim()===':root'){ r.walkDecls(d=>{ if(d.prop.startsWith('--')&&!d.prop.startsWith('--cm-mood')) d.remove(); }); if(!r.nodes.length) r.remove(); }
});
root.walkAtRules(a=>{ if(a.nodes && a.nodes.length===0) a.remove(); });
const s=root.toString();
if(/<\/style/i.test(s)) throw new Error('style end');
fs.writeFileSync(out,s); console.log(s.length);
