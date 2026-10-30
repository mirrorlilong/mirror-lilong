#!/usr/bin/env python3
"""Mirror Lilong: reader language switch on article pages (plain Python 3, no packages).

Runs after build.py (see .github/workflows/pages.yml). For every translations/<slug>.json whose
story page _site/news-<slug>.html exists, it adds a 5-button bar (English | Manipuri | Meitei Mayek |
Bengali-script Manipuri | Hindi) and a small "translated by AI" note above the story. Stories without
a translation file are left exactly as build.py wrote them. A broken or partial file is logged and
skipped; this script never fails the site build.

Translation file shape (translations/<slug>.json, UTF-8):
  {"en":       {"title": "...", "summary": "...", "body": "para 1\n\npara 2 ..."},
   "mni-Latn": {...same keys...},   # Manipuri in English letters
   "mni-Mtei": {...},               # Manipuri in Meitei Mayek
   "mni-Beng": {...},               # Manipuri in Bengali script
   "hi":       {...},               # Hindi
   "_meta":    {...optional notes...}}
A language missing or without a title+body is simply not offered. English on the page always comes
from the story itself (content/stories), so edits to the English post show up as usual.
"""
import html, json, os, re, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, '_site'); TR = os.path.join(ROOT, 'translations')
LANGS = [  # code, icon, label, html lang
  ('en', 'EN', 'English', 'en'),
  ('mni-Latn', 'Ma', 'Manipuri', 'mni-Latn'),
  ('mni-Mtei', '\uabc3', '\uabc3\uabe4\uabc7\uabe9 \uabc3\uabcc\uabe6\uabdb', 'mni-Mtei'),
  ('mni-Beng', '\u09ae', '\u09ae\u09a3\u09bf\u09aa\u09c1\u09b0\u09c0', 'mni-Beng'),
  ('hi', '\u0939\u093f', '\u0939\u093f\u0928\u094d\u0926\u0940', 'hi'),
]
HEAD = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
  '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+Meetei+Mayek:wght@400;700;900&family=Noto+Sans+Bengali:wght@400;700;900&family=Noto+Sans+Devanagari:wght@400;700;900&display=swap">'
  '<style>'
  '.lang-pick{margin:12px 0 14px;padding:10px 10px 12px;background:#f6f6f6;border-top:3px solid var(--red,#d7141a);border-radius:0 0 10px 10px}'
  '.lang-pick .lp-lab{font-size:11.5px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#555;margin:0 0 8px;display:flex;align-items:center;gap:6px}'
  '.lang-pick .lp-row{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px}'
  '.lp-btn{display:flex;flex-direction:column;align-items:center;justify-content:flex-start;gap:5px;padding:8px 2px 7px;border:1.5px solid #d4d4d4;border-radius:12px;background:#fff;color:#111;cursor:pointer;font:inherit;min-height:74px;min-width:0;-webkit-tap-highlight-color:transparent;transition:background .15s,border-color .15s,transform .1s}'
  '.lp-btn:active{transform:scale(.97)}'
  '.lp-ic{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#111;color:#fff;font-weight:900;font-size:15px;line-height:1}'
  '.lp-tx{font-size:12px;font-weight:700;line-height:1.15;text-align:center;overflow-wrap:anywhere}'
  '.lp-btn[aria-pressed=true]{background:var(--red,#d7141a);border-color:var(--red,#d7141a);color:#fff}'
  '.lp-btn[aria-pressed=true] .lp-ic{background:#fff;color:var(--red,#d7141a)}'
  '.f-mtei,.lp-btn .f-mtei{font-family:"Noto Sans Meetei Mayek",sans-serif}'
  '.f-beng,.lp-btn .f-beng{font-family:"Noto Sans Bengali",sans-serif}'
  '.f-deva,.lp-btn .f-deva{font-family:"Noto Sans Devanagari",sans-serif}'
  '.lp-ic.f-mtei,.lp-ic.f-beng{font-size:19px}.lp-ic.f-deva{font-size:17px}'
  '.lang-disc{display:none;margin:0 0 14px;padding:8px 10px;border-left:3px solid #bbb;background:#fafafa;color:#777;font-size:12.5px;line-height:1.5}'
  '.lang-disc .ld-en{display:block;margin-top:3px;font-style:italic}'
  '.article.tr-on .lang-disc{display:block}'
  '.article[data-lang=mni-Mtei] [data-tr]{font-family:"Noto Sans Meetei Mayek",sans-serif}'
  '.article[data-lang=mni-Beng] [data-tr]{font-family:"Noto Sans Bengali",sans-serif}'
  '.article[data-lang=hi] [data-tr]{font-family:"Noto Sans Devanagari",sans-serif}'
  '.article.tr-on .art-body p:first-child:first-letter{float:none;font-size:inherit;padding:0;color:inherit;font-weight:inherit}'
  '.article[data-lang=mni-Mtei] .art-body p,.article[data-lang=mni-Beng] .art-body p,.article[data-lang=hi] .art-body p{line-height:1.85}'
  '@media (max-width:360px){.lang-pick{padding:8px 6px 10px}.lang-pick .lp-row{gap:4px}.lp-tx{font-size:11px}.lp-ic{width:30px;height:30px}}'
  '@media (min-width:700px){.lang-pick .lp-row{max-width:620px}}'
  '</style>')

DEFAULT_DISC = {'en': 'This translation was done automatically using AI and may contain errors. The original English version is the official one.'}

def log(msg): print('translations: ' + msg)
def esc(s): return html.escape(s, quote=False)
def body_html(text):
    return ''.join('<p>%s</p>' % esc(p.strip()) for p in text.split('\n\n') if p.strip())
def cls(code): return {'mni-Mtei': ' f-mtei', 'mni-Beng': ' f-beng', 'hi': ' f-deva'}.get(code, '')

def bar(disc, langs):
    btns = ''.join('<button type="button" class="lp-btn" data-lang="%s" lang="%s" aria-pressed="%s"><span class="lp-ic%s">%s</span><span class="lp-tx%s">%s</span></button>'
                   % (c, hl, 'true' if c == 'en' else 'false', cls(c), ic, cls(c), lab) for c, ic, lab, hl in langs)
    return ('<div class="lang-pick" role="group" aria-label="Choose language"><p class="lp-lab"><svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 100 20 10 10 0 000-20zm6.9 6h-2.9a15.7 15.7 0 00-1.4-3.6A8 8 0 0118.9 8zM12 4c.8 1.2 1.5 2.5 1.9 4h-3.8c.4-1.5 1.1-2.8 1.9-4zM4.3 14a8.2 8.2 0 010-4h3.4a16.5 16.5 0 000 4H4.3zm.8 2h2.9c.3 1.3.8 2.5 1.4 3.6A8 8 0 015.1 16zM8 8H5.1a8 8 0 014.3-3.6C8.8 5.5 8.3 6.7 8 8zm4 12c-.8-1.2-1.5-2.5-1.9-4h3.8c-.4 1.5-1.1 2.8-1.9 4zm2.3-6H9.7a14.7 14.7 0 010-4h4.6a14.7 14.7 0 010 4zm.3 5.6c.6-1.1 1.1-2.3 1.4-3.6h2.9a8 8 0 01-4.3 3.6zm1.7-5.6a16.5 16.5 0 000-4h3.4a8.2 8.2 0 010 4h-3.4z"/></svg>Read this news in</p>'
            '<div class="lp-row">%s</div></div><div class="lang-disc" role="note" aria-live="polite"><span class="ld-tr"></span><span class="ld-en">%s</span></div>') % (btns, esc(disc['en']))

JS = r"""<script>(function(){var a=document.querySelector('.article[data-has-tr]');if(!a)return;var D;try{D=JSON.parse(document.getElementById('tr-data').textContent)}catch(e){return}
var h=a.querySelector('h1'),s=a.querySelector('.art-dek'),b=a.querySelector('.art-body'),dt=a.querySelector('.ld-tr');if(!h||!b||!dt)return;
D.t.en={title:h.textContent,summary:s?s.textContent:'',body:b.innerHTML};
var K='ml-lang';function set(l,save){if(!D.t[l])l='en';var t=D.t[l];h.textContent=t.title;if(s&&t.summary)s.textContent=t.summary;else if(s)s.textContent=D.t.en.summary;b.innerHTML=t.body;
var hl=l==='en'?'en':l;a.setAttribute('data-lang',l);h.setAttribute('lang',hl);b.setAttribute('lang',hl);if(s)s.setAttribute('lang',hl);
a.classList.toggle('tr-on',l!=='en');dt.textContent=l==='en'?'':(D.d[l]||'');dt.className='ld-tr'+({'mni-Mtei':' f-mtei','mni-Beng':' f-beng','hi':' f-deva'}[l]||'');
var bs=a.querySelectorAll('.lp-btn');for(var i=0;i<bs.length;i++)bs[i].setAttribute('aria-pressed',bs[i].getAttribute('data-lang')===l?'true':'false');
if(save){try{localStorage.setItem(K,l)}catch(e){}}}
a.querySelector('.lang-pick').addEventListener('click',function(e){var x=e.target.closest('.lp-btn');if(x)set(x.getAttribute('data-lang'),true)});
var saved=null;try{saved=localStorage.getItem(K)}catch(e){}if(saved&&saved!=='en')set(saved,false);})();</script>"""

def inject(page, d, disc):
    if 'data-has-tr' in page: return None  # already done (idempotent)
    t = {}
    for c, _, _, _ in LANGS:
        if c == 'en': continue
        x = d.get(c)
        if isinstance(x, dict) and isinstance(x.get('title'), str) and isinstance(x.get('body'), str) and x['title'].strip() and x['body'].strip():
            summ = x.get('summary') if isinstance(x.get('summary'), str) else ''
            t[c] = {'title': x['title'].strip(), 'summary': summ.strip(), 'body': body_html(x['body'])}
    if not t: return None
    langs = [L for L in LANGS if L[0] == 'en' or L[0] in t]
    m = re.search(r'<article class="article">(.*?)</article>', page, flags=re.S)
    if not m or '<h1>' not in m.group(1) or '<div class="art-body">' not in m.group(1) or '</head>' not in page or '</body>' not in page:
        return None
    art = m.group(1)
    art = re.sub(r'^(<nav class="crumbs".*?</nav>)', lambda n: n.group(1) + bar(disc, langs), art, count=1, flags=re.S)
    if 'lang-pick' not in art:
        art = bar(disc, langs) + art
    art = art.replace('<h1>', '<h1 data-tr="title">', 1).replace('<p class="art-dek">', '<p class="art-dek" data-tr="summary">', 1)
    art = art.replace('<div class="art-body">', '<div class="art-body" data-tr="body">', 1)
    page = page[:m.start()] + '<article class="article" data-has-tr data-lang="en">' + art + '</article>' + page[m.end():]
    blob = json.dumps({'t': t, 'd': {k: v for k, v in disc.items() if k != 'en' and isinstance(v, str)}}, ensure_ascii=False).replace('</', '<\\/')
    page = page.replace('</head>', HEAD + '</head>', 1)
    i = page.rfind('</body>')
    page = page[:i] + '<script type="application/json" id="tr-data">%s</script>%s' % (blob, JS) + page[i:]
    return page

def main():
    if not os.path.isdir(TR) or not os.path.isdir(OUT):
        log('nothing to do'); return
    disc = dict(DEFAULT_DISC)
    try:
        dj = json.load(open(os.path.join(TR, '_disclaimer.json'), encoding='utf-8'))
        if isinstance(dj, dict): disc.update({k: v for k, v in dj.items() if isinstance(v, str)})
    except Exception as e:
        log('disclaimer file problem (%s), using English note only' % e)
    done, skipped = [], []
    for fn in sorted(os.listdir(TR)):
        if fn.startswith(('_', '.')) or not fn.endswith('.json'): continue
        slug = fn[:-5]
        try:
            p = os.path.join(OUT, 'news-%s.html' % slug)
            if not os.path.exists(p): skipped.append(slug + ' (no story page)'); continue
            d = json.load(open(os.path.join(TR, fn), encoding='utf-8'))
            if not isinstance(d, dict): raise ValueError('not a JSON object')
            page = open(p, encoding='utf-8').read()
            new = inject(page, d, disc)
            if new is None: skipped.append(slug + ' (already done, no usable language, or unexpected page layout)'); continue
            open(p, 'w', encoding='utf-8').write(new); done.append(slug)
        except Exception as e:
            skipped.append('%s (error: %s)' % (slug, e))
    log('added language switch to %d stories' % len(done))
    for s in skipped: log('skipped ' + s)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:  # never break the site build
        print('translations: step failed, site published without language switch (%s)' % e)
