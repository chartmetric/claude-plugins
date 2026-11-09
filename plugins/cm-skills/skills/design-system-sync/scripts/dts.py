import os,sys,re
d,out=sys.argv[1],sys.argv[2];parts=['/** Chartmetric Design System component types (from dist/*.d.ts). Documentation only. */']
for c in sorted(os.listdir(d)):
    txt=''
    for f in ['types.d.ts','constants.d.ts','index.d.ts']:
        p=os.path.join(d,c,f)
        if os.path.exists(p): txt+=f'// --- {c}/{f}\n'+open(p).read()+'\n'
    if not re.search(rf'(interface|type) {c}Props\b',txt):
        txt=re.sub(r'\binterface Props\b',f'interface {c}Props',txt); txt=re.sub(r'\bProps\b(?!\w)',f'{c}Props',txt)
    parts.append(f'// ===== {c} =====\n'+txt)
open(out,'w').write('\n'.join(parts))
