# Verifying an animated artifact

Headless Chrome confirms layout, content and JavaScript errors. It does not confirm motion.

## Layout and content, animations off

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --force-prefers-reduced-motion --hide-scrollbars --window-size=1320,2400 --virtual-time-budget=6000 --screenshot=$PWD/shot.png "file://$PWD/page.html"
```

To screenshot a particular step, append a script that clicks the step's button named in `location.hash`, then crop with `sips -c <h> <w> --cropOffset <y> 0`.

## Every step, collecting errors

```html
<script>window.__errs=[];addEventListener('error',e=>__errs.push(e.message+' @'+e.lineno));</script>
<script>setTimeout(()=>{
  document.querySelectorAll('.timeline button').forEach(b=>b.click());
  const o=document.createElement('pre'); o.id='OUT';
  o.textContent=JSON.stringify({errs:__errs, rows:document.querySelectorAll('.state-row').length});
  document.body.prepend(o);
},1500);</script>
```

```bash
"$CHROME" --headless=new --force-prefers-reduced-motion --virtual-time-budget=5000 --dump-dom "file://$PWD/test.html" | grep -o '<pre id="OUT">[^<]*'
```

## Headless gotchas

- Minimum viewport width is 500px; "mobile overflow" at narrower sizes is the harness, not the page.
- Virtual time does not reliably advance CSS animations or rAF loops. Elements mid-entry show collapsed; screenshot with reduced motion, or read `getComputedStyle(el).height` from the DOM dump.
- `resize` listeners that clear overlays (arrows) fire during headless setup, so overlays are missing from screenshots.
- `<title>` is a convenient channel for one measured value in `--dump-dom` output.

## What only a person can check

Arrow timing, streaming, stagger, chart draw-in, and whether anything opens by itself. Say which of these were not seen, and ask the user to press Play once end to end before presenting.
