# usage: python3 tokens.py <repo>/styles/index.css <out>/project/tokens.json <ref like main@abc1234>
# Builds the Claude Design tokens.json (list-shaped families) from the repo's CSS custom properties.
import re,json,sys,datetime
css=open(sys.argv[1]).read()
root=css[css.index(':root'):css.index('@keyframes')]
fam_note={
 'teal':'Primary brand teal. 500 is the brand color: primary buttons, active nav, focus, links (700 for link/active text).',
 'chillyellow':'Secondary brand yellow. Highlights and the dark-mode active-secondary text (100).',
 'brandgreen':'Secondary brand green. Positive-trend fills, celebratory banners, brand illustration.',
 'categorical':'General categorical data-viz series, used in order 1→12 for chart lines, bars and legends.',
 'lake':'Sequential data-viz ramp (light→deep blue-teal) for heatmaps and choropleths.',
 'forest':'Sequential data-viz ramp (pale yellow→deep green).',
 'rose':'Sequential data-viz ramp (cream→pink→navy).',
 'magma':'Sequential data-viz ramp (Magma).',
 'viridis':'Sequential data-viz ramp (Viridis), colour-blind safe.',
 'green':'Semantic green (formerly Success): positive change, success states. 50 fill / 100 border / 500 text.',
 'red':'Semantic red (formerly Error): errors, destructive actions, negative change. 50 fill / 100 border / 500 text.',
 'orange':'Semantic orange (formerly Warning): warnings. 50 fill / 100 border / 500 text.',
 'blue':'Semantic blue (formerly Info): informational notices.',
 'grayedteal':'Grayed teal neutral: cool panel fills and secondary button surfaces; 700 is disabled button text.',
 'gray':'Gray neutral: app background (50), card borders (300–500), dividers, muted surfaces; dark-* steps are dark-mode surfaces, dark-bg the dark page.',
 'gray-transparent':'White overlays for dark mode surfaces and hover states.',
 'black':'Black at fixed opacities: scrims, overlays, light-mode hover tints.',
 'white':'White at fixed opacities: card surfaces (100), dark-mode overlays and disabled text.',
 'charcoal':'Text ramp. 1 primary text, 2 secondary, 3 tertiary, 4 disabled, 5 suggested/placeholder; dark-* are the dark-mode equivalents.',
 'warmgreen':'Chartmetric Intelligence warm green accent.',
 'intelligence':'Chartmetric Intelligence blue accent for AI features.',
 'flow':'Chartmetric Intelligence "Flow" lime accent for Flow AI surfaces.',
}
plat={'spotify':'Spotify','instagram':'Instagram','soundcloud':'SoundCloud','facebook':'Facebook','x':'X','melon':'Melon','youtube':'YouTube','amazon':'Amazon','shazam':'Shazam','deezer':'Deezer','wikipedia':'Wikipedia','twitch':'Twitch','pandora':'Pandora','applemusic':'Apple Music','bandsintown':'Bandsintown','tiktok':'TikTok','linemusic':'Line Music'}
text_roles={'charcoal-1':'Primary text on white/gray-50 surfaces (CMText color="primary").','charcoal-2':'Secondary text.','charcoal-3':'Tertiary text, captions.','charcoal-4':'Disabled text.','charcoal-5':'Suggested/placeholder text.',
 'charcoal-dark-1':'Primary text in dark mode, on gray-dark-bg and gray-dark-1…3.','charcoal-dark-2':'Secondary text in dark mode.','charcoal-dark-3':'Tertiary text in dark mode.','charcoal-dark-4':'Disabled text in dark mode.','charcoal-dark-5':'Suggested text in dark mode.',
 'teal-500':'Brand teal: primary button fill, focus ring, active indicators.','teal-600':'Primary button hover, selected borders.','teal-700':'Link and active-primary text (CMText activePrimary); passes 4.5:1 on white.',
 'gray-50':'App page background.','gray-300':'Default card/container border.','gray-500':'Stronger border, input outline.','gray-dark-bg':'Dark-mode page background.','white-100':'Card and surface fill in light mode.'}
tokens=[];shadows=[]
for m in re.finditer(r'--([a-z0-9-]+):\s*([^;]+);',root):
    n,v=m.group(1),' '.join(m.group(2).split())
    if n.startswith('shadow-'):
        shadows.append({'name':n,'value':v,'usage':{'shadow-xs':'Subtle lift for small resting elements.','shadow-sm':'Resting cards and containers.','shadow-md':'Raised/hovered cards, dropdown panels.','shadow-lg':'Popovers, menus and modals.'}[n]});continue
    if n.startswith('cm-mood'): continue
    if v.startswith('#'): v=v.lower()
    elif not v.startswith('rgb'): print('skip',n,v,file=sys.stderr);continue
    key=n[3:]
    fam=re.sub(r'(-dark)?-(\d+|sec|bg)$','',key); fam=re.sub(r'-dark$','',fam)
    if key in text_roles: u=text_roles[key]
    elif fam in plat: u=f"{plat[fam]} platform colour for its series in charts and its brand accents; -dark-* steps are for dark mode."
    else: u=fam_note.get(fam, fam_note.get(key.split('-')[0],''))
    if not u: print('nousage',n,file=sys.stderr)
    tokens.append({'name':n,'value':v,'usage':u})
sp=[('3xs','2px'),('2xs','4px'),('xs','6px'),('sm','8px'),('md','12px'),('lg','16px'),('xl','24px'),('2xl','32px'),('3xl','40px'),('4xl','48px'),('5xl','56px')]
spu={'3xs':'Hairline gaps between icon and text.','2xs':'Tight inline gaps, tag inner gap.','xs':'Compact control padding.','sm':'Default gap inside controls and small stacks.','md':'Gap between form rows, button horizontal padding.','lg':'Card padding (compact), section gaps.','xl':'Card padding, gap between cards.','2xl':'Section spacing.','3xl':'Large section spacing.','4xl':'Page-level vertical rhythm.','5xl':'Hero spacing.'}
rd=[('2xs','0.125rem','Tiny indicators.'),('xs','0.25rem','Checkboxes, small tags.'),('sm','0.375rem','Buttons, inputs.'),('md','0.5rem','Dropdown panels, tooltips, small cards.'),('lg','0.75rem','Cards and containers.'),('xl','1rem','Large cards, modals.'),('full','9999px','Pills, avatars, switches.')]
styles=[]
V={'hero':('2.25rem',700,'130%','0em'),'display':('2.05rem',700,'130%','0em'),'h1':('1.75rem',700,'130%','0em'),'h2':('1.6rem',600,'130%','0em'),'h3':('1.4rem',600,'130%','0em'),'h4':('1.25rem',600,'130%','0em'),'h5':('1.125rem',600,'130%','0em'),
 'body':('1rem',500,'130%','0em'),'paragraph':('1rem',500,'150%','0em'),'button':('1rem',600,'150%','0em'),'link':('1rem',600,'150%','0em'),'link-sm':('0.875rem',600,'130%','0em'),
 'label-1':('0.875rem',600,'150%','0em'),'label-2':('0.875rem',500,'150%','0.01em'),'label-3':('0.875rem',400,'130%','0.01em'),'label-3-paragraph':('0.875rem',400,'150%','0.01em'),'mini-1':('0.75rem',500,'150%','0em'),'mini-2':('0.75rem',600,'150%','0em')}
smp={'hero':'Year in Music 2026','display':'Artist overview','h1':'Taylor Swift','h2':'Audience growth','h3':'Top markets','h4':'Recent viewed','h5':'Playlist reach','body':'Monthly listeners rose 12.4% this week.','paragraph':'Track streaming, social and chart performance across every major platform in one place.','button':'Add to shortlist','link':'See the full report','link-sm':'Remove all','label-1':'Monthly Listeners','label-2':'Spotify Followers','label-3':'Updated Mar 31, 2026','label-3-paragraph':'Data refreshes daily at 00:00 UTC.','mini-1':'+12.4%','mini-2':'NEW'}
groups=[('Headings',['hero','display','h1','h2','h3','h4','h5']),('Body',['body','paragraph','button','link','link-sm']),('Labels',['label-1','label-2','label-3','label-3-paragraph','mini-1','mini-2'])]
tg=[]
for g,names in groups:
    st=[]
    for n in names:
        fs,w,lh,ls=V[n]
        st.append({'name':n,'fontSize':fs,'fontWeight':w,'lineHeight':lh,'letterSpacing':ls,'sample':smp[n],'usage':f'CMText variant="{n}".'+(' Underlined.' if n.startswith('link') else '')})
    tg.append({'name':g,'family':'sans','styles':st})
out={'name':'Chartmetric Design System','version':1,
 'color':{'themes':[{'id':'light','name':'Light'},{'id':'dark','name':'Dark'}],'tokens':tokens},
 'type':{'fonts':[{'family':'Inter','file':'fonts/InterVariable.woff2','weight':'100 900','style':'normal'},{'family':'Inter','file':'fonts/InterVariable-Italic.woff2','weight':'100 900','style':'italic'}],'families':{'sans':'"Inter", system-ui, -apple-system, "Segoe UI", sans-serif'},'groups':tg},
 'spacing':{'tokens':[{'name':'spacing-'+a,'value':b,'usage':spu[a]+f' Tailwind gap-/p-/m-{a}.'} for a,b in sp]},
 'radius':{'tokens':[{'name':'radius-'+a,'value':b,'usage':u+f' Tailwind rounded-{a}.'} for a,b,u in rd]},
 'shadow':{'note':'Cool, low-contrast elevation. Borders separate inside tables and lists; shadows only on floating or raised elements.','tokens':shadows},
 'breakpoint':{'note':'Responsive breakpoints from src/breakpoints.ts / _breakpoints.scss.','tokens':[{'name':'breakpoint-sm','value':'0px','usage':'Mobile and up.'},{'name':'breakpoint-md','value':'773px','usage':'Tablet and up.'},{'name':'breakpoint-lg','value':'1280px','usage':'Desktop and up.'}]},
 'meta':{'source':'github','repo':'chartmetric/chartmetric-design-system','ref':sys.argv[3],'package':'.','paths':{'tokens':['styles/index.css','styles/_font.scss','styles/_spacing.scss','styles/_radius.scss','styles/_breakpoints.scss','src/variants/text.ts','tailwind.config.ts']},'components':{},'synced':datetime.date.today().isoformat()}}
json.dump(out,open(sys.argv[2],'w'),indent=1)
print(len(tokens),'colors',len(shadows),'shadows')
