#!/usr/bin/env python3
"""Mirror Lilong site builder.

Reads one JSON file per story from content/stories/ (written by the admin panel at /admin),
plus content/settings/videos.json, and writes the finished static site into _site/.
Standard library only: no packages to install. Run:  python3 build.py
"""
import json, html, datetime, os, re, shutil, struct, sys
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, 'content')
STATIC = os.path.join(HERE, 'static')
OUT = os.path.join(HERE, '_site')
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
esc = html.escape

FBPAGE = 'https://www.facebook.com/100077335757093/'
IG = 'https://www.instagram.com/mirrorlilong/'
YT = 'https://www.youtube.com/@teammirrormanipur'
WA_CH = 'https://whatsapp.com/channel/0029VaVurd6GzzKbrvh1xP3r'  # WhatsApp Channel (floating pill + footer)
CATS = ['Manipur', 'Northeast', 'India', 'World', 'Sports', 'Entertainment']
NAV = [('Home', 'index.html')] + [(c, c.lower() + '.html') for c in CATS] + [('Writers', 'writers.html'), ('Videos', 'videos.html')]
SITE = 'https://mirrorlilong.com'  # used for share links
# Google Analytics: paste a measurement id like "G-XXXXXXXXXX" here and every page gets the gtag snippet.
GA_ID = "G-EVK542T9WM"

SEARCH_SVG = '<svg class="ic-s" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="2.4"/><path d="M15.5 15.5 21 21" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>'
CLOSE_SVG = '<svg class="ic-x" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>'
CARET = '<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true" focusable="false"><path d="M2 4.2 6 8l4-3.8" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
WA_SVG = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path fill="currentColor" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>'
FB_SVG = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path fill="currentColor" d="M9.101 23.691v-7.98H6.627v-3.667h2.474v-1.58c0-4.085 1.848-5.978 5.858-5.978.401 0 .955.042 1.468.103a8.68 8.68 0 0 1 1.141.195v3.325a8.623 8.623 0 0 0-.653-.036 26.805 26.805 0 0 0-.733-.009c-.707 0-1.259.096-1.675.309a1.686 1.686 0 0 0-.679.622c-.258.42-.374.995-.374 1.752v1.297h3.919l-.386 2.103-.287 1.564h-3.246v8.245C19.396 23.238 24 18.179 24 12.044c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.628 3.874 10.35 9.101 11.647Z"/></svg>'
LINK_SVG = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path d="M10 14a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5M14 10a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>'

# Northeast states: sub-sections of Northeast. Keywords (state, capital, major towns) place older
# Northeast stories that have no "State (Northeast)" set.
NE_STATES = [
    ('Arunachal Pradesh', ['arunachal', 'itanagar', 'naharlagun', 'tawang', 'pasighat', 'ziro', 'bomdila', 'tezu', 'roing', '\u0905\u0930\u0941\u0923\u093e\u091a\u0932', '\u0908\u091f\u093e\u0928\u0917\u0930']),
    ('Assam', ['assam', 'assamese', 'guwahati', 'dispur', 'dibrugarh', 'jorhat', 'silchar', 'tezpur', 'nagaon', 'tinsukia', 'dima hasao', 'haflong', 'umrangso', 'kaziranga', 'kokrajhar', 'bodoland', 'barak valley', '\u0905\u0938\u092e', '\u0917\u0941\u0935\u093e\u0939\u093e\u091f\u0940']),
    ('Manipur', ['manipur', 'imphal', 'churachandpur', 'bishnupur', 'thoubal', 'ukhrul', 'kangpokpi', 'senapati', 'jiribam', 'moreh', 'lilong', 'tamenglong', 'chandel', '\u092e\u0923\u093f\u092a\u0941\u0930', '\u0907\u0902\u092b\u093e\u0932']),
    ('Meghalaya', ['meghalaya', 'shillong', 'tura', 'jowai', 'cherrapunji', 'sohra', 'nongpoh', '\u092e\u0947\u0918\u093e\u0932\u092f', '\u0936\u093f\u0932\u093e\u0902\u0917']),
    ('Mizoram', ['mizoram', 'mizo', 'aizawl', 'lunglei', 'champhai', 'kolasib', 'serchhip', '\u092e\u093f\u091c\u094b\u0930\u092e', '\u0906\u0907\u091c\u094b\u0932']),
    ('Nagaland', ['nagaland', 'kohima', 'dimapur', 'mokokchung', 'tuensang', 'meluri', 'wokha', 'zunheboto', '\u0928\u093e\u0917\u093e\u0932\u0948\u0902\u0921', '\u0915\u094b\u0939\u093f\u092e\u093e']),
    ('Tripura', ['tripura', 'agartala', 'dharmanagar', 'kailashahar', '\u0924\u094d\u0930\u093f\u092a\u0941\u0930\u093e', '\u0905\u0917\u0930\u0924\u0932\u093e']),
]
NE_NAMES = [n for n, _ in NE_STATES]
def state_page(n): return 'northeast-%s.html' % n.lower().replace(' ', '-')
# Weather box: the 7 state capitals (Open-Meteo, fetched in the reader's browser)
NE_CAPITALS = [('Itanagar', 'Arunachal', 27.0844, 93.6053), ('Dispur', 'Assam', 26.1433, 91.7898), ('Imphal', 'Manipur', 24.8170, 93.9368),
               ('Shillong', 'Meghalaya', 25.5788, 91.8933), ('Aizawl', 'Mizoram', 23.7271, 92.7176), ('Kohima', 'Nagaland', 25.6751, 94.1086), ('Agartala', 'Tripura', 23.8315, 91.2868)]

def infer_states(text):
    t = ' ' + re.sub(r'\s+', ' ', str(text or '').lower()) + ' '
    t = t.replace('assam rifles', ' ')
    found = []
    for name, words in NE_STATES:
        for kw in words:
            if (re.search(r'(?<![a-z])' + re.escape(kw) + r'(?![a-z])', t) if kw.isascii() else kw in t):
                found.append(name); break
    return found

def warn(msg): print('WARNING: ' + msg, file=sys.stderr)

# ---------- reading content ----------
def parse_date(v):
    """Accepts 2026-10-28, 2026-10-28T13:05, 2026-10-28 13:05, or full ISO with Z/offset. Returns IST datetime."""
    if isinstance(v, (int, float)):
        return datetime.datetime.fromtimestamp(v, IST)
    s = str(v or '').strip()
    if not s:
        return None
    s = s.replace('Z', '+00:00').replace(' ', 'T', 1)
    try:
        d = datetime.datetime.fromisoformat(s)
    except ValueError:
        try:
            d = datetime.datetime.combine(datetime.date.fromisoformat(s[:10]), datetime.time(0, 0))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=IST)
    return d.astimezone(IST)

def asset(path):
    """'/img/x.jpg', 'img/x.jpg' or 'static/img/x.jpg' -> 'img/x.jpg' (relative, works on every page)."""
    p = str(path or '').strip()
    if p.startswith('http://') or p.startswith('https://'):
        return p
    p = p.lstrip('/')
    if p.startswith('static/'):
        p = p[len('static/'):]
    return p

def load_stories():
    folder = os.path.join(CONTENT, 'stories')
    out = []
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith('.json'):
            continue
        slug = re.sub(r'[^a-z0-9-]+', '-', fn[:-5].lower()).strip('-')
        try:
            s = json.load(open(os.path.join(folder, fn), encoding='utf-8'))
        except Exception as e:
            warn('skipped %s: not valid JSON (%s)' % (fn, e)); continue
        if not isinstance(s, dict) or not str(s.get('title') or '').strip():
            warn('skipped %s: no headline' % fn); continue
        if s.get('hidden'):
            continue
        s['slug'] = slug
        s['title'] = str(s['title']).strip()
        s['dt'] = parse_date(s.get('date')) or datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(folder, fn)), IST)
        cat = s.get('category') or 'Manipur'
        if cat not in CATS:
            warn('%s: unknown category %r, using Manipur' % (fn, cat)); cat = 'Manipur'
        s['cat'] = cat
        if s.get('also_in') not in CATS or s.get('also_in') == cat:
            s['also_in'] = None
        s['summary'] = str(s.get('summary') or '').strip()
        st = s.get('state') if s.get('state') in NE_NAMES else None
        if st:
            s['states'] = [st]
        else:
            s['states'] = infer_states(s['title'] + ' ' + s['summary']) if 'Northeast' in (cat, s['also_in']) else []
        if 'Manipur' in (cat, s['also_in']) and 'Manipur' not in s['states']:
            s['states'].append('Manipur')
        s['img'] = asset(s.get('image')) or 'img/lilong.jpg'
        s['full'] = asset(s.get('full_image')) or s['img']
        s['sources'] = [x for x in (s.get('sources') or []) if isinstance(x, dict) and x.get('url')]
        out.append(s)
    out.sort(key=lambda s: (s['dt'], s['slug']), reverse=True)  # newest first
    return out

def load_videos():
    try:
        return json.load(open(os.path.join(CONTENT, 'settings', 'videos.json'), encoding='utf-8')).get('links') or []
    except Exception as e:
        warn('videos.json not read (%s)' % e); return []

# ---------- tiny markdown (what the editor's toolbar can produce) ----------
def inline(t):
    t = esc(t, quote=False)
    def link(m):
        u = m.group(2).strip()
        if not re.match(r'^(https?://|mailto:|/|#|[\w.-]+\.html)', u):
            return m.group(0)
        ext = u.startswith('http')
        return '<a href="%s"%s>%s</a>' % (u.replace('"', '&quot;'), ' target="_blank" rel="noopener"' if ext else '', m.group(1))
    t = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'__(.+?)__', r'<b>\1</b>', t)
    t = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<i>\1</i>', t)
    t = re.sub(r'(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])', r'<i>\1</i>', t)
    t = t.replace('\\\n', '<br>').replace('  \n', '<br>').replace('\n', ' ')
    return t

def markdown(text, fig=None, keep_lines=False):
    """fig: optional callback for in-story photos; given a stripped block, returns figure HTML
    ('' = render nothing) or None (not a photo block, render as usual).
    keep_lines: keep single line breaks inside a paragraph (poems / Prose & Verse)."""
    text = str(text or '').replace('\r\n', '\n').replace('\u00a0', ' ').strip()
    out = []
    for block in re.split(r'\n\s*\n', text):
        block = block.strip('\n')
        if not block.strip():
            continue
        if fig is not None:
            f = fig(block.strip())
            if f is not None:
                if f: out.append(f)
                continue
        lines = block.split('\n')
        m = re.match(r'^(#{1,6})\s+(.*)$', block.strip())
        if m and len(lines) == 1:
            lvl = 2 if len(m.group(1)) <= 2 else 3
            out.append('<h%d>%s</h%d>' % (lvl, inline(m.group(2)), lvl)); continue
        if all(re.match(r'^\s*[-*+]\s+', l) for l in lines):
            out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % inline(re.sub(r'^\s*[-*+]\s+', '', l)) for l in lines)); continue
        if all(re.match(r'^\s*\d+[.)]\s+', l) for l in lines):
            out.append('<ol>%s</ol>' % ''.join('<li>%s</li>' % inline(re.sub(r'^\s*\d+[.)]\s+', '', l)) for l in lines)); continue
        if all(l.lstrip().startswith('>') for l in lines):
            out.append('<blockquote><p>%s</p></blockquote>' % inline('\n'.join(re.sub(r'^\s*>\s?', '', l) for l in lines))); continue
        if keep_lines:
            out.append('<p>%s</p>' % '<br>'.join(inline(l.rstrip()) for l in lines))
            continue
        out.append('<p>%s</p>' % inline(block))
    return ''.join(out)

# ---------- in-story photos ("More photos" in the admin panel) ----------
# In Story text, a paragraph that is just [photo1] / [Photo 2] shows that photo from the story's
# "photos" list (1 = first). A paragraph that is just ![caption](image-link) works too.
# Photos never referenced by a marker are shown after the story text, in order.
PHOTO_RE = re.compile(r'^\[\s*photo\s*(\d+)\s*\]$', re.I)
MDIMG_RE = re.compile(r'^!\[([^\]\n]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"\n]*")?\s*\)$')

def story_photos(s):
    """The story's photos list as [(img-path or '', caption)], keeping positions (1-based markers)."""
    out = []
    for x in (s.get('photos') or []) if isinstance(s.get('photos'), list) else []:
        if isinstance(x, dict):
            img, cap = x.get('image'), x.get('caption')
        else:
            img, cap = x, ''
        img = asset(img) if isinstance(img, str) and img.strip() else ''
        out.append((img, cap.strip() if isinstance(cap, str) else ''))
    return out

def photo_figure(img, cap, alt, key):
    if not img or not re.match(r'^(https?://[^\s"<>]+|[\w./%-]+)$', img) or '..' in img:
        return ''
    size = image_size(img) if not img.startswith('http') else None
    tall = bool(size) and size[1] > size[0]
    wh = ' width="%d" height="%d"' % size if size else ''
    paras = [p.strip() for p in re.split(r'\n\s*\n|\n|\s{2,}', cap or '') if p.strip()]
    if cap and (len(cap) > 160 or len(paras) > 1):
        # Long "caption" = story text typed under this photo: show it as normal story paragraphs.
        body = ''.join('<p>%s</p>' % inline(p) for p in paras)
        return ('<figure class="art-fig art-photo art-photo-long" data-photo="%s"><div class="ph-frame%s"><img src="%s" loading="lazy" alt="%s"%s></div>'
                '<div class="photo-text">%s</div></figure>') % (esc(key), ' ph-tall' if tall else '', esc(img), esc(alt), wh, body)
    capt = '<figcaption>%s</figcaption>' % inline(cap) if cap else ''
    return '<figure class="art-fig art-photo%s" data-photo="%s"><img src="%s" loading="lazy" alt="%s"%s>%s</figure>' % (
        ' fbcard' if tall else '', esc(key), esc(img), esc(cap or alt), wh, capt)

def article_body(s, keep_lines=False):
    """Story text as HTML with in-story photos; plain markdown() when the story has none."""
    photos = story_photos(s)
    body = s.get('body')
    used = set()
    def fig(block):
        m = PHOTO_RE.match(block)
        if m:
            n = int(m.group(1))
            if 1 <= n <= len(photos):
                used.add(n)
                return photo_figure(photos[n - 1][0], photos[n - 1][1], s['title'], str(n))
            return ''
        m = MDIMG_RE.match(block)
        if m:
            u = m.group(2).strip()
            img = asset(u)
            for i, (p, _) in enumerate(photos, 1):  # same image as an uploaded photo: count it as used
                if p and p == img:
                    used.add(i)
            return photo_figure(img, m.group(1).strip(), s['title'], 'img:' + img)
        return None
    html_ = markdown(body, fig, keep_lines)
    rest = ''.join(photo_figure(p, c, s['title'], str(i)) for i, (p, c) in enumerate(photos, 1) if i not in used)
    return html_ + rest

# ---------- image size (jpeg/png/webp/gif) ----------
def image_size(rel):
    path = os.path.join(STATIC, rel)
    try:
        with open(path, 'rb') as f:
            head = f.read(32)
            if head[:8] == b'\x89PNG\r\n\x1a\n':
                return struct.unpack('>II', head[16:24])
            if head[:6] in (b'GIF87a', b'GIF89a'):
                return struct.unpack('<HH', head[6:10])
            if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
                f.seek(12); chunk = f.read(4); f.seek(20); d = f.read(10)
                if chunk == b'VP8 ':
                    return struct.unpack('<H', d[6:8])[0] & 0x3fff, struct.unpack('<H', d[8:10])[0] & 0x3fff
                if chunk == b'VP8L':
                    b = d[1:5]; bits = int.from_bytes(b, 'little')
                    return (bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1
                if chunk == b'VP8X':
                    return int.from_bytes(d[4:7], 'little') + 1, int.from_bytes(d[7:10], 'little') + 1
            if head[:2] == b'\xff\xd8':
                f.seek(2)
                while True:
                    b = f.read(1)
                    while b and b != b'\xff':
                        b = f.read(1)
                    while b == b'\xff':
                        b = f.read(1)
                    if not b:
                        break
                    marker = b[0]
                    if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        f.read(3); h, w = struct.unpack('>HH', f.read(4)); return w, h
                    ln = struct.unpack('>H', f.read(2))[0]; f.seek(ln - 2, 1)
    except Exception:
        pass
    return None

# ---------- page parts (same markup and classes as the original design) ----------
def fdate(s): return s['dt'].strftime('%d %b %Y')
def iso(s): return s['dt'].strftime('%Y-%m-%d')
def url(s): return s.get('_page') or 'news-%s.html' % s['slug']
def ext(u, label): return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(u), label)
def badge(s): return '<span class="desk">Mirror Lilong</span>' if s.get('desk') else ''

def card(s, size='m', dek=False):
    play = '<span class="play" aria-hidden="true"></span>' if s.get('video') else ''
    d = '<p class="dek">%s</p>' % esc(s['summary']) if dek and s['summary'] else ''
    return ('<article class="card card-%s"><a href="%s" class="card-link"><div class="thumb"><img src="%s" alt="" loading="lazy" width="1200" height="675">%s</div>'
            '<div class="card-body"><div class="meta-top"><span class="kicker">%s</span>%s</div><h3>%s</h3>%s<time datetime="%s">%s</time></div></a></article>') % (
            size, url(s), esc(s['img']), play, esc(s['cat']), badge(s), esc(s['title']), d, iso(s), fdate(s))

def header(active, ctx):
    def li(n, h):
        cur = ' aria-current="page"' if n == active else ''
        if n == 'Writers':
            sub = ''.join('<li><a href="%s">%s</a></li>' % (p, esc(x)) for x, _, p in WR_CATS)
            return ('<li class="has-sub"><a href="%s"%s>%s</a><button class="sub-btn" type="button" aria-expanded="false" aria-controls="wrSub" aria-label="Show Writers sections">%s</button>'
                    '<ul class="sub" id="wrSub">%s</ul></li>') % (h, cur, n, CARET, sub)
        if n != 'Northeast':
            return '<li><a href="%s"%s>%s</a></li>' % (h, cur, n)
        sub = ''.join('<li><a href="%s">%s</a></li>' % (state_page(x), x) for x in NE_NAMES)
        return ('<li class="has-sub"><a href="%s"%s>%s</a><button class="sub-btn" type="button" aria-expanded="false" aria-controls="neSub" aria-label="Show Northeast states">%s</button>'
                '<ul class="sub" id="neSub"><li class="sub-all"><a href="%s">All Northeast</a></li>%s</ul></li>') % (h, cur, n, CARET, h, sub)
    nav = ''.join(li(n, h) for n, h in NAV)
    tick = ' <span class="sep" aria-hidden="true">&#9670;</span> '.join('<a href="%s">%s</a>' % (url(s), esc(s['title'])) for s in ctx['tick'])
    return ('<a class="skip" href="#main">Skip to content</a>'
     '<div class="topbar"><div class="wrap topbar-in"><span id="today" class="today">%s</span><span class="topbar-links">%s%s%s</span></div></div>'
     '<header class="masthead"><div class="wrap mast-in"><button class="menu-btn" id="menuBtn" type="button" aria-controls="mainNav" aria-expanded="false" aria-label="Open sections menu"><span></span><span></span><span></span></button>'
     '<a href="index.html" class="brand"><picture><source srcset="logo.webp" type="image/webp"><img src="logo.png" alt="Mirror Lilong" width="1200" height="197"></picture></a><div class="mast-tools"><div class="hsearch" id="hSearch"><button class="hs-btn" id="hsBtn" type="button" aria-controls="hsForm" aria-expanded="false" aria-label="Search news">%s%s</button>'
     '<form class="hs-form" id="hsForm" action="/search" method="get" role="search"><input class="hs-input" type="search" name="q" placeholder="Search news" autocomplete="off" enterkeyhint="search" aria-label="Search news" aria-controls="hsRes"><button class="hs-go" type="submit" aria-label="Search">%s</button>'
     '<div class="hs-res" id="hsRes" hidden></div></form></div>'
     '<a class="watch-btn" href="videos.html"><span class="dot" aria-hidden="true"></span>Watch</a></div></div>'
     '<nav class="mainnav" id="mainNav" aria-label="Sections"><ul class="wrap">%s</ul></nav></header>'
     '<div class="ticker" role="region" aria-label="Breaking news"><div class="wrap ticker-in"><span class="ticker-label">Breaking</span><div class="ticker-track"><div class="ticker-move"><span>%s</span><span aria-hidden="true">%s</span></div></div></div></div>') % (
     ctx['today'], ext(FBPAGE, 'Facebook'), ext(IG, 'Instagram'), ext(YT, 'YouTube'), SEARCH_SVG, CLOSE_SVG, SEARCH_SVG, nav, tick, tick.replace('<a ', '<a tabindex="-1" '))

def footer(ctx):
    cats = ''.join('<li><a href="%s">%s</a></li>' % (h, n) for n, h in NAV[1:])
    return ('<footer class="footer"><div class="wrap foot-in"><div class="foot-brand"><picture><source srcset="logo-white.webp" type="image/webp"><img src="logo-white.png" alt="Mirror Lilong" width="1200" height="197" loading="lazy"></picture>'
     '<p>News, interviews and stories from Lilong, Manipur and the Northeast.</p><p class="social">%s &middot; %s &middot; %s &middot; %s</p></div>'
     '<div><h2 class="foot-h">Sections</h2><ul class="foot-list">%s</ul></div>'
     '<div><h2 class="foot-h">About our stories</h2><p class="small">Stories marked <b>Mirror Lilong</b> come from the Mirror Lilong desk. Other stories are short original summaries, and each one links to the publisher that first reported it. Photos are credited on each story.</p></div></div>'
     '<div class="copy"><div class="wrap copy-in"><span>&copy; %s Mirror Lilong &middot; Imphal, Manipur</span><nav class="foot-legal" aria-label="About Mirror Lilong"><a href="about.html">About</a> &middot; <a href="contact.html">Contact</a> &middot; <a href="privacy-policy.html">Privacy Policy</a> &middot; <a href="terms.html">Terms</a></nav></div></div></footer>%s<script src="script.js" defer></script>') % (
     ext(FBPAGE, 'Facebook'), ext(IG, 'Instagram'), ext(YT, 'YouTube'), ext(WA_CH, 'WhatsApp Channel'), cats, ctx['year'], wa_channel_pill())

def wa_channel_pill():
    """Floating 'Join our WhatsApp Channel' pill, bottom-right on every page (styles: .wa-ch in styles.css)."""
    return ('<a class="wa-ch" href="%s" target="_blank" rel="noopener" aria-label="Join the Mirror Lilong WhatsApp Channel">'
            '<span class="wa-ch-ic">%s</span><span class="wa-ch-t"><span class="wa-ch-long">Join our WhatsApp Channel</span><span class="wa-ch-short">Join Channel</span></span></a>') % (esc(WA_CH), WA_SVG)

def page(title, desc, active, main, ctx, og_img=None, strip='', og_type='website', head=''):
    og = ('<meta property="og:title" content="%s"><meta property="og:description" content="%s"><meta property="og:type" content="%s"><meta property="og:site_name" content="Mirror Lilong">' % (esc(title), esc(desc), og_type))
    base = os.environ.get('URL', '').rstrip('/')  # Netlify sets URL to the site's address
    if og_img and base:
        og += '<meta property="og:image" content="%s">' % esc(og_img if og_img.startswith('http') else base + '/' + og_img)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
     '<title>%s</title><meta name="description" content="%s">%s<meta name="theme-color" content="#d7141a"><link rel="icon" href="favicon-32.png" sizes="32x32" type="image/png"><link rel="icon" href="favicon-192.png" sizes="192x192" type="image/png"><link rel="apple-touch-icon" href="apple-touch-icon.png"><link rel="stylesheet" href="styles.css"><meta name="google-adsense-account" content="ca-pub-4739495411759158"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4739495411759158" crossorigin="anonymous"></script>%s%s</head><body>'
     '%s%s<main id="main" class="wrap">%s</main>%s</body></html>') % (esc(title), esc(desc), og, ga_snippet(), head, header(active, ctx), strip, main, footer(ctx))


# ---------- SEO: structured data (JSON-LD) for Google Search / News ----------
LOGO_URL = SITE + '/logo.png'
SAME_AS = [FBPAGE, IG, YT, WA_CH]
def abs_url(p):
    p = str(p or '').strip()
    if not p:
        return ''
    return p if p.startswith(('http://', 'https://')) else SITE + '/' + p.lstrip('/')
def page_url(name):
    """Clean public URL of an output file, matching w(): index.html -> /, x.html -> /x."""
    return SITE + '/' if name == 'index.html' else SITE + '/' + re.sub(r'\.html$', '', name)
def publisher_ld():
    return {'@type': 'Organization', 'name': 'Mirror Lilong', 'url': SITE + '/',
            'logo': {'@type': 'ImageObject', 'url': LOGO_URL, 'width': 1200, 'height': 197}}
def ld_script(data):
    return '<script type="application/ld+json">%s</script>' % json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
def site_ld(home=False):
    org = dict(publisher_ld(), sameAs=SAME_AS)
    org['@context'] = 'https://schema.org'
    if not home:
        return ld_script(org)
    org.pop('@context')
    org['@id'] = SITE + '/#organization'
    web = {'@type': 'WebSite', '@id': SITE + '/#website', 'name': 'Mirror Lilong', 'url': SITE + '/', 'inLanguage': 'en',
           'publisher': {'@id': SITE + '/#organization'},
           'potentialAction': {'@type': 'SearchAction', 'target': {'@type': 'EntryPoint', 'urlTemplate': SITE + '/search?q={search_term_string}'},
                               'query-input': 'required name=search_term_string'}}
    return ld_script({'@context': 'https://schema.org', '@graph': [org, web]})
def ld_headline(t, n=110):
    t = re.sub(r'\s+', ' ', str(t or '')).strip()
    if len(t) <= n:
        return t
    cut = t[:n - 1].rsplit(' ', 1)[0].rstrip(' ,;:-')
    return cut + '\u2026'
def plain(t, n=300):
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)|\[\s*photo\s*\d+\s*\]', ' ', str(t or ''), flags=re.I)
    t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)
    t = re.sub(r'[*_#>`]+', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t if len(t) <= n else t[:n].rsplit(' ', 1)[0] + '\u2026'
def article_head(s, name, news=True):
    """<head> additions for a story or writing page: NewsArticle/Article JSON-LD + article meta tags."""
    u = page_url(name)
    pub = s['dt'].replace(microsecond=0)
    mod = (parse_date(s.get('updated') or s.get('modified')) or pub).replace(microsecond=0)
    if mod < pub:
        mod = pub
    imgs = []
    for p in ([s.get('full'), s.get('img')] + [i for i, _ in story_photos(s)]):
        a = abs_url(p)
        if a and a not in imgs:
            imgs.append(a)
    if not imgs:
        imgs = [LOGO_URL]
    w = s.get('w')
    if w:
        author = {'@type': 'Person', 'name': w['name'], 'url': page_url(wurl(w))}
    else:
        author = {'@type': 'Organization', 'name': 'Mirror Lilong', 'url': SITE + '/'}
    data = {'@context': 'https://schema.org', '@type': 'NewsArticle' if news else 'Article',
            'mainEntityOfPage': {'@type': 'WebPage', '@id': u}, 'url': u,
            'headline': ld_headline(s['title']),
            'description': plain(s.get('summary') or s.get('body') or s['title']),
            'image': imgs, 'datePublished': pub.isoformat(), 'dateModified': mod.isoformat(),
            'author': [author], 'publisher': publisher_ld(), 'inLanguage': 'en',
            'isAccessibleForFree': True}
    sec = s.get('cat') or s.get('category')
    if sec:
        data['articleSection'] = sec
    meta = ('<meta name="robots" content="max-image-preview:large">'
            '<meta property="article:published_time" content="%s"><meta property="article:modified_time" content="%s">' % (pub.isoformat(), mod.isoformat()))
    if sec:
        meta += '<meta property="article:section" content="%s">' % esc(sec)
    return meta + ld_script(data)

def ga_snippet():
    if not re.match(r'^G-[A-Z0-9]+$', GA_ID or ''):
        return ''
    return ('<script async src="https://www.googletagmanager.com/gtag/js?id=%s"></script><script>window.dataLayer=window.dataLayer||[];'
            'function gtag(){dataLayer.push(arguments);}gtag(\'js\',new Date());gtag(\'config\',\'%s\');</script>') % (GA_ID, GA_ID)

def weather_box(strip=False):
    """Northeast capitals weather; numbers are filled in by script.js from Open-Meteo."""
    items = ''.join('<li data-i="%d"><span class="wx-city">%s<small>%s</small></span><span class="wx-ic" aria-hidden="true"></span><span class="wx-t">--&deg;</span><span class="wx-hl"></span></li>' % (k, c, st) for k, (c, st, _, _) in enumerate(NE_CAPITALS))
    data = ' data-wx="%s"' % esc(json.dumps([[la, lo] for (_, _, la, lo) in NE_CAPITALS]))
    if strip:
        return '<div class="wx-strip" role="region" aria-label="Weather in Northeast capitals"%s><div class="wrap wx-strip-in"><span class="wx-lab">Weather</span><ul class="wx-list">%s</ul></div></div>' % (data, items)
    return '<section class="wx-box" aria-label="Weather in Northeast capitals"%s>%s<ul class="wx-list">%s</ul><p class="wx-note">Loading weather&hellip;</p></section>' % (data, sec_title('Northeast Weather'), items)

def share_bar(s, where):
    u = SITE + '/' + url(s)[:-5]
    wa = 'https://wa.me/?text=' + quote(s['title'] + ' ' + u, safe='')
    fb = 'https://www.facebook.com/sharer/sharer.php?u=' + quote(u, safe='')
    return ('<div class="share share-%s" data-share data-url="%s" data-title="%s"><span class="share-lab">Share this %s</span><div class="share-btns">'
            '<a class="sh sh-wa" href="%s" target="_blank" rel="noopener" aria-label="Share on WhatsApp">%s<span>WhatsApp</span></a>'
            '<a class="sh sh-st" href="%s" target="_blank" rel="noopener" data-native aria-label="Share to WhatsApp Status">%s<span>Status</span></a>'
            '<a class="sh sh-fb" href="%s" target="_blank" rel="noopener" aria-label="Share on Facebook">%s<span>Facebook</span></a>'
            '<button class="sh sh-cp" type="button" data-copy aria-label="Copy link">%s<span>Copy link</span></button></div></div>') % (
            where, esc(u), esc(s['title']), 'post' if s.get('_page') else 'story', esc(wa), WA_SVG, esc(wa), WA_SVG, esc(fb), FB_SVG, LINK_SVG)

def sec_title(t, href=None):
    more = ' <a class="more" href="%s">More &rsaquo;</a>' % href if href else ''
    return '<h2 class="sec-title"><span>%s</span>%s</h2>' % (t, more)

def ago(iso_s, now):
    try:
        d = datetime.datetime.fromisoformat(iso_s.replace('Z', '+00:00'))
    except Exception:
        return '', ''
    m = int((now - d).total_seconds() // 60)
    txt = 'just now' if m < 2 else '%d min ago' % m if m < 60 else '%d hr ago' % (m // 60) if m < 1440 else d.astimezone(IST).strftime('%d %b')
    return txt, d.astimezone(IST).strftime('%d %b %Y, %H:%M IST')

def trending(ctx, exclude=None, n=6):
    news = ctx.get('news')
    if news and news.get('items'):
        # Mirror Lilong's own stories switched to Trending in the admin come first (newest first),
        # then live news from publishers' feeds (trending.py), Manipur first, then Northeast, India, World
        now = ctx['now']
        rows = ''
        own = [s for s in ctx.get('trend_own', []) if s is not exclude][:4]
        for s in own:
            when, full = ago(s['dt'].isoformat(), now)
            rows += ('<li class="tn-item tn-own tn-%s"><a href="%s"><span class="tn-img"><img src="%s" alt="" loading="lazy" decoding="async" width="120" height="80"></span>'
                     '<span class="tn-body"><span class="tn-cat">%s</span><span class="tn-tt">%s</span><span class="tn-meta">Mirror Lilong &middot; <time datetime="%s" title="%s" data-ago>%s</time></span></span></a></li>') % (
                     esc(s['cat'].lower()), url(s), esc(s['img']), esc(s['cat']), esc(s['title']), esc(s['dt'].isoformat()), esc(full), when)
        feed = news['items'][:max(len(news['items']) - len(own), 3)]
        for x in feed:
            when, full = ago(x.get('published', ''), now)
            c = x.get('category', '')
            rows += ('<li class="tn-item tn-%s"><a href="%s" target="_blank" rel="noopener"><span class="tn-img"><img src="%s" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" width="120" height="80" onerror="this.closest(\'li\').hidden=true"></span>'
                     '<span class="tn-body"><span class="tn-cat">%s</span><span class="tn-tt">%s</span><span class="tn-meta">%s &middot; <time datetime="%s" title="%s" data-ago>%s</time></span></span></a></li>') % (
                     esc(c.lower()), esc(x['url']), esc(x['image']), esc(c), esc(x['title']), esc(x.get('source', '')), esc(x.get('published', '')), esc(full), when)
        upd = ''
        try:
            u = datetime.datetime.fromisoformat(news['updated'].replace('Z', '+00:00')).astimezone(IST)
            upd = '<p class="tn-upd"><span class="tn-live" aria-hidden="true"></span>Updated %s IST</p>' % u.strftime('%H:%M')
        except Exception:
            pass
        return '<section class="trending tnews" aria-label="Trending news">%s%s<ol class="tn-list">%s</ol></section>' % (sec_title('Trending'), upd, rows)
    lst = [s for s in ctx['trend'] if s is not exclude][:n]
    items = ''.join('<li><a href="%s"><span class="num">%d</span><span class="tt">%s</span></a></li>' % (url(s), i + 1, esc(s['title'])) for i, s in enumerate(lst))
    return '<section class="trending" aria-label="Trending">%s<ol>%s</ol></section>' % (sec_title('Trending'), items)

def follow_box():
    return ('<section class="follow">%s<p>Get Lilong and Manipur news as it happens.</p><div class="follow-btns">%s%s%s%s</div></section>') % (
        sec_title('Follow Mirror Lilong'), '<a class="fb" href="%s" target="_blank" rel="noopener">Facebook</a>' % FBPAGE,
        '<a class="ig" href="%s" target="_blank" rel="noopener">Instagram</a>' % IG, '<a class="yt" href="%s" target="_blank" rel="noopener">YouTube</a>' % YT,
        '<a class="wa" href="%s" target="_blank" rel="noopener">WhatsApp</a>' % WA_CH)

def flagged(stories, flag, n, exclude=()):
    """Newest stories with the flag; topped up with the newest others so the box is never empty."""
    lst = [s for s in stories if s.get(flag) and s not in exclude][:n]
    if len(lst) < n:
        lst += [s for s in stories if s not in lst and s not in exclude][:n - len(lst)]
    return lst

def build_index(stories, ctx):
    lead = ctx['lead']
    slides = ctx.get('slides') or [lead]
    n = len(slides)
    sl = []
    for k, s in enumerate(slides):
        h = 'h1' if k == 0 else 'h2'
        lazy = '' if k == 0 else ' loading="lazy" decoding="async"'
        sl.append(('<article class="lead ls-slide" role="group" aria-roledescription="slide" aria-label="%d of %d"><a href="%s" class="card-link"%s><div class="thumb"><img src="%s" alt="%s" width="1200" height="675"%s></div>'
          '<div class="lead-body"><div class="meta-top"><span class="kicker">%s</span>%s</div><%s>%s</%s><time datetime="%s">%s</time></div></a></article>') % (
          k + 1, n, url(s), '' if k == 0 else ' tabindex="-1"', esc(s['img']), esc(s['title']), lazy, s['cat'], badge(s), h, esc(s['title']), h, iso(s), fdate(s)))
    if n > 1:
        dots = ''.join('<button type="button" aria-label="Story %d"%s></button>' % (k + 1, ' aria-current="true"' if k == 0 else '') for k in range(n))
        leadhtml = ('<div class="lead-slider" data-slider role="region" aria-roledescription="carousel" aria-label="Lead stories">'
          '<div class="ls-track">%s</div>'
          '<button type="button" class="ls-arrow ls-prev" aria-label="Previous story">&lsaquo;</button>'
          '<button type="button" class="ls-arrow ls-next" aria-label="Next story">&rsaquo;</button>'
          '<div class="ls-dots">%s</div></div>') % (''.join(sl), dots)
    else:
        leadhtml = sl[0].replace(' ls-slide" role="group" aria-roledescription="slide" aria-label="1 of 1"', '"')
    top = ''.join('<li><a href="%s"><span class="kicker">%s</span>%s</a></li>' % (url(s), s['cat'], esc(s['title'])) for s in ctx['top'])
    desk = [s for s in stories if s.get('desk') and s is not lead][:4]
    parts = ['<div class="hero-grid">%s<aside class="top-list"><h2 class="sec-title"><span>Top Stories</span></h2><ul>%s</ul></aside></div>' % (leadhtml, top)]
    if desk:
        parts.append('<section class="block desk-block">%s<div class="grid g4">%s</div></section>' % (sec_title('From the Mirror Lilong desk'), ''.join(card(s) for s in desk)))
    main_col = []
    for c in CATS:
        allc = bycat(stories, c)
        if not allc:
            continue
        lst = [s for s in allc if s is not lead and s not in desk] or allc
        if c == 'Manipur':
            body = '<div class="grid g-feature">%s<div class="stack">%s</div></div>' % (card(lst[0], 'l', True), ''.join(card(s, 's') for s in lst[1:5]))
        else:
            body = '<div class="grid %s">%s</div>' % ('g3' if len(lst) >= 3 else 'g2', ''.join(card(s) for s in lst[:3]))
        main_col.append('<section class="block">%s%s</section>' % (sec_title(c, c.lower() + '.html'), body))
    parts.append('<div class="two-col"><div class="col-main">%s</div><aside class="col-side">%s%s%s</aside></div>' % (''.join(main_col), weather_box(), trending(ctx), follow_box()))
    return page('Mirror Lilong | Latest news from Lilong, Manipur and the Northeast', 'Mirror Lilong brings the latest news from Lilong, Manipur, the Northeast, India and the world.', 'Home', ''.join(parts), ctx, lead['img'], strip=weather_box(True))

def bycat(stories, c): return [s for s in stories if s['cat'] == c or s.get('also_in') == c]

def bystate(stories, st): return [s for s in stories if st in s.get('states', [])]

def state_chips(stories, current=None):
    chips = ['<a href="northeast.html"%s>All</a>' % (' aria-current="page"' if current is None else '')]
    for x in NE_NAMES:
        chips.append('<a href="%s"%s>%s <span>%d</span></a>' % (state_page(x), ' aria-current="page"' if x == current else '', x, len(bystate(stories, x))))
    return '<nav class="chips" aria-label="Northeast states">%s</nav>' % ''.join(chips)

def story_grid(lst):
    first = '<div class="grid g-feature">%s<div class="stack">%s</div></div>' % (card(lst[0], 'l', True), ''.join(card(s, 's') for s in lst[1:4]))
    rest = '<div class="grid g3">%s</div>' % ''.join(card(s, 'm', True) for s in lst[4:]) if len(lst) > 4 else ''
    return first + rest

def build_state(stories, st, ctx):
    lst = bystate(stories, st)
    n = len(lst)
    body = story_grid(lst) if lst else ('<div class="empty-state"><p class="es-big">No stories from %s yet.</p><p>New stories will show up here as soon as they are posted. Meanwhile, catch up on <a href="northeast.html">all Northeast news</a>.</p></div>' % st)
    main = ('<nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a> &rsaquo; <a href="northeast.html">Northeast</a> &rsaquo; %s</nav>'
            '<div class="cat-head cat-head-sub"><h1>%s</h1><p>%d %s</p></div>%s<div class="two-col"><div class="col-main">%s</div><aside class="col-side">%s%s%s</aside></div>') % (
            st, st, n, 'story' if n == 1 else 'stories', state_chips(stories, st), body, weather_box(), trending(ctx), follow_box())
    return page('%s News | Northeast | Mirror Lilong' % st, 'Latest news from %s on Mirror Lilong.' % st, 'Northeast', main, ctx, strip=weather_box(True))

def build_cat(stories, c, ctx):
    lst = bycat(stories, c)
    if c == 'Northeast':
        n = len(lst)
        body = story_grid(lst) if lst else '<p class="note">No stories in this section yet.</p>'
        main = '<div class="cat-head"><h1>%s</h1><p>%d %s</p></div>%s<div class="two-col"><div class="col-main">%s</div><aside class="col-side">%s%s%s</aside></div>' % (
            c, n, 'story' if n == 1 else 'stories', state_chips(stories), body, weather_box(), trending(ctx), follow_box())
        return page('%s News | Mirror Lilong' % c, 'Latest %s news from Mirror Lilong.' % c, c, main, ctx, strip=weather_box(True))
    if lst:
        first = '<div class="grid g-feature">%s<div class="stack">%s</div></div>' % (card(lst[0], 'l', True), ''.join(card(s, 's') for s in lst[1:4]))
        rest = '<div class="grid g3">%s</div>' % ''.join(card(s, 'm', True) for s in lst[4:]) if len(lst) > 4 else ''
    else:
        first, rest = '<p class="note">No stories in this section yet.</p>', ''
    n = len(lst)
    main = '<div class="cat-head"><h1>%s</h1><p>%d %s</p></div><div class="two-col"><div class="col-main">%s%s</div><aside class="col-side">%s%s</aside></div>' % (
        c, n, 'story' if n == 1 else 'stories', first, rest, trending(ctx), follow_box())
    return page('%s News | Mirror Lilong' % c, 'Latest %s news from Mirror Lilong.' % c, c, main, ctx)

def build_videos(stories, videos, ctx):
    tiles = ''
    for s in [s for s in stories if s.get('video')]:
        tiles += ('<article class="card card-m vid"><a href="%s" class="card-link"><div class="thumb"><img src="%s" alt="" loading="lazy" width="1200" height="675"><span class="play" aria-hidden="true"></span></div>'
                  '<div class="card-body"><span class="kicker">Watch on Mirror Lilong</span><h3>%s</h3></div></a></article>') % (url(s), esc(s['img']), esc(s['title']))
    for v in videos:
        if not v.get('url') or not v.get('title'):
            continue
        tiles += ('<article class="card card-m vid"><a href="%s" class="card-link" target="_blank" rel="noopener"><div class="thumb"><img src="%s" alt="" loading="lazy" width="1200" height="675"><span class="play" aria-hidden="true"></span></div>'
                  '<div class="card-body"><span class="kicker">Watch on %s</span><h3>%s</h3></div></a></article>') % (
                  esc(v['url']), esc(asset(v.get('image')) or 'img/lilong.jpg'), esc(v.get('where') or 'Facebook'), esc(v['title']))
    main = '<div class="cat-head"><h1>Videos</h1><p>Interviews, ground reports and podcasts from Mirror Lilong</p></div><div class="two-col"><div class="col-main"><div class="grid g3">%s</div><p class="note">Videos play on Mirror Lilong\'s Facebook, YouTube and Instagram pages. Some thumbnails here are file photos.</p></div><aside class="col-side">%s%s</aside></div>' % (tiles, trending(ctx), follow_box())
    return page('Videos | Mirror Lilong', 'Watch interviews, podcasts and ground reports from Mirror Lilong.', 'Videos', main, ctx)

def build_article(stories, s, ctx):
    links = []
    if s.get('facebook'):
        links.append('<li>%s</li>' % ext(s['facebook'], 'Read on Facebook &rsaquo;'))
    for x in s['sources']:
        lab = 'Read on Facebook &rsaquo;' if 'facebook.com' in x['url'] else esc(x.get('name') or 'Source') + ' &rsaquo;'
        links.append('<li>%s</li>' % ext(x['url'], lab))
    srcs = ('<div class="sources"><h2>%s</h2><ul>%s</ul></div>' % ('Source' if len(links) == 1 else 'Sources', ''.join(links))) if links else ''
    size = image_size(s['full']) or (1200, 675)
    portrait = size[1] > size[0]
    cap = s.get('image_credit') or ''
    capt = '<figcaption>%s</figcaption>' % inline(cap) if cap else ''
    fig = '<figure class="art-fig%s"><img src="%s" alt="%s" width="%d" height="%d">%s</figure>' % (
        ' fbcard' if portrait else '', esc(s['full']), esc(s['title']), size[0], size[1], capt)
    related = [x for x in bycat(stories, s['cat']) if x is not s][:3]
    rel = '<section class="block">%s<div class="grid g3">%s</div></section>' % (sec_title('More from ' + s['cat'], s['cat'].lower() + '.html'), ''.join(card(x) for x in related)) if related else ''
    by = 'Mirror Lilong Desk' if s.get('desk') else 'Mirror Lilong News Desk'
    if s.get('w'):
        by = '<a class="by-w" href="%s">%s<span>By %s</span></a>' % (wurl(s['w']), avatar(s['w'], 's'), esc(s['w']['name']))
    dek = '<p class="art-dek">%s</p>' % esc(s['summary']) if s['summary'] else ''
    main = ('<div class="two-col article-wrap"><article class="article"><nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a> &rsaquo; <a href="%s">%s</a></nav>'
          '<h1>%s</h1>%s<div class="art-meta"><span class="by">%s</span>%s<time datetime="%s">%s</time></div>%s%s'
          '<div class="art-body">%s</div>%s%s<p class="back"><a href="index.html">&lsaquo; Back to home</a></p></article>'
          '<aside class="col-side">%s%s</aside></div>%s') % (s['cat'].lower() + '.html', s['cat'], esc(s['title']), dek, by, badge(s), iso(s), fdate(s), share_bar(s, 'top'), fig,
          article_body(s), srcs + author_box(s.get('w')), share_bar(s, 'end'), trending(ctx, s), follow_box(), rel)
    return page('%s | Mirror Lilong' % s['title'], s['summary'] or s['title'], s['cat'], main, ctx, s['img'],
                og_type='article', head=article_head(s, url(s), news=True))

# ---------- About / Contact / Privacy / Terms ----------
def info_page(title, desc, h1, body, ctx):
    main = ('<div class="two-col article-wrap"><article class="article info-page"><nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a> &rsaquo; %s</nav>'
            '<h1>%s</h1><div class="art-body info-body">%s</div></article><aside class="col-side">%s%s</aside></div>') % (h1, h1, body, trending(ctx), follow_box())
    return page(title, desc, None, main, ctx)

def build_info(ctx):
    fb, ig, yt = ext(FBPAGE, 'Facebook page'), ext(IG, 'Instagram (@mirrorlilong)'), ext(YT, 'YouTube channel')
    about = (
        '<p>Mirror Lilong is an independent local news outlet from Lilong, Manipur. We report on what matters to people in Lilong and across Manipur, and we keep readers up to date on the Northeast, India and the world.</p>'
        '<h2>What we cover</h2><ul><li><a href="manipur.html">Manipur</a>: local news, community events and ground reports</li><li><a href="northeast.html">Northeast</a>: stories from the neighbouring states</li>'
        '<li><a href="india.html">India</a> and <a href="world.html">World</a>: the national and international news our readers follow</li><li><a href="sports.html">Sports</a> and <a href="entertainment.html">Entertainment</a></li>'
        '<li><a href="videos.html">Videos</a>: interviews, podcasts and ground reports</li></ul>'
        '<h2>Our mission</h2><p>We want people in Lilong and Manipur to have quick, clear and fair news about their own community, in one place. We aim to be accurate, to be fair to everyone in a story, and to correct mistakes when we make them.</p>'
        '<h2>How our stories work</h2><p>Stories marked <b>Mirror Lilong</b> are reported by the Mirror Lilong desk. Other stories are short summaries written by us, and each one links to the publisher that first reported it. Photos are credited on each story.</p>'
        '<h2>Who we are</h2><p>Mirror Lilong is run by the Mirror Lilong team. Our Facebook community has grown to around 194,000 followers, and we also share news and videos on Instagram and YouTube.</p>'
        '<p>Have a story, a correction or a question? See our <a href="contact.html">Contact</a> page.</p>')
    contact = (
        '<p>We would love to hear from you, whether you have a news tip, a correction, a question about a story, or an advertising enquiry.</p>'
        '<h2>Email us</h2><p><b>Email:</b> <a href="mailto:mirrorlilong@gmail.com">mirrorlilong@gmail.com</a></p><h2>Message us</h2><p>You can also send us a message on our %s. We read every message.</p>'
        '<ul><li>Facebook: %s</li><li>Instagram: %s</li><li>YouTube: %s</li></ul>'
        '<h2>Corrections</h2><p>If you think something in one of our stories is wrong, email us or message us on Facebook with the story link and what needs fixing. We will check it and correct the story if needed.</p>'
        '<h2>News tips</h2><p>Seen something in Lilong or anywhere in Manipur that people should know about? Send us the details, and photos or videos if you have them.</p>'
        '<p>Based in Lilong, Manipur, India.</p>') % (fb, ext(FBPAGE, 'facebook.com/mirrorlilong'), ext(IG, '@mirrorlilong'), ext(YT, '@teammirrormanipur'))
    privacy = (
        '<p><i>Last updated: 29 October 2026</i></p>'
        '<p>This Privacy Policy explains what information is collected when you visit mirrorlilong.com (the &ldquo;Site&rdquo;), run by the Mirror Lilong team (&ldquo;we&rdquo;, &ldquo;us&rdquo;), and how it is used. By using the Site you agree to this policy.</p>'
        '<h2>Information we collect</h2><p>You can read the Site without creating an account or giving us any personal information. We do not run sign-up forms or comment sections on the Site. If you message us on Facebook, Instagram or YouTube, those platforms handle your message under their own privacy policies, and we only use what you send us to reply to you.</p>'
        '<p>Like most websites, our hosting provider may automatically record basic technical information when you visit, such as your IP address, browser type, the pages you request and the time of your visit. This is used to deliver and secure the Site.</p>'
        '<h2>Cookies</h2><p>Cookies are small text files stored on your device by your web browser. We do not set our own tracking cookies. However, third parties that serve advertising on the Site, including Google, use cookies as described below.</p>'
        '<h2>Advertising and Google AdSense</h2><p>We use Google AdSense to show advertisements on the Site. Google is a third-party vendor that uses cookies to serve ads on this Site.</p>'
        '<ul><li>Third-party vendors, including Google, use cookies to serve ads based on your previous visits to this website or other websites.</li>'
        '<li>Google&rsquo;s use of advertising cookies, including the DoubleClick cookie, enables it and its partners to serve ads to you based on your visits to this Site and/or other sites on the Internet.</li>'
        '<li>You may opt out of personalised advertising by visiting <a href="https://www.google.com/settings/ads" target="_blank" rel="noopener">Google Ads Settings</a>. You can also opt out of some third-party vendors&rsquo; use of cookies for personalised advertising at <a href="https://www.aboutads.info/choices/" target="_blank" rel="noopener">www.aboutads.info</a>.</li>'
        '<li>To learn how Google uses information from sites that use its services, see <a href="https://policies.google.com/technologies/ads" target="_blank" rel="noopener">How Google uses cookies in advertising</a> and <a href="https://policies.google.com/technologies/partner-sites" target="_blank" rel="noopener">How Google uses information from sites or apps that use its services</a>.</li></ul>'
        '<p>If you do not opt out, you may still see ads, but they will not be personalised. You can also block or delete cookies in your browser settings; some parts of the Site may then work differently.</p>'
        '<h2>Analytics</h2><p>We use Google Analytics to understand how many people visit the Site and which pages they read. Google Analytics uses cookies to collect information such as the pages you visit, how long you stay, the type of device and browser you use, and your approximate location (city or region). This information is collected in aggregate and is not used to identify you personally. Learn more at <a href="https://policies.google.com/technologies/partner-sites" rel="noopener" target="_blank">How Google uses information from sites that use its services</a>. You can opt out of Google Analytics with the <a href="https://tools.google.com/dlpage/gaoptout" rel="noopener" target="_blank">Google Analytics opt-out browser add-on</a>.</p>'
        '<h2>Links to other websites</h2><p>Our stories link to other websites, such as the publishers that first reported a story, and to our social media pages. We are not responsible for the content or privacy practices of those sites.</p>'
        '<h2>Children</h2><p>The Site is a general news site and is not directed at children under 13. We do not knowingly collect personal information from children.</p>'
        '<h2>Your choices</h2><p>You can control cookies through your browser settings and the opt-out links above. If you have contacted us and want us to delete your messages or any information you sent us, let us know.</p>'
        '<h2>Changes to this policy</h2><p>We may update this policy from time to time. The date at the top shows when it was last changed.</p>'
        '<h2>Governing law</h2><p>This policy is governed by the laws of India.</p>'
        '<h2>Contact</h2><p>For any questions about this Privacy Policy, email us at <a href="mailto:mirrorlilong@gmail.com">mirrorlilong@gmail.com</a> or message us on our %s or see our <a href="contact.html">Contact</a> page.</p>') % fb
    terms = (
        '<p><i>Last updated: 29 October 2026</i></p>'
        '<p>By using mirrorlilong.com (the &ldquo;Site&rdquo;) you agree to these terms. If you do not agree, please do not use the Site.</p>'
        '<h2>Content</h2><p>The stories, photos and videos on the Site are for general information only. We work to keep our reporting accurate and up to date, but we cannot guarantee that every detail is complete or free of errors, and news can change after a story is published. Please do not rely on the Site as your only source for important decisions.</p>'
        '<h2>Copyright</h2><p>Original Mirror Lilong stories, photos and videos belong to Mirror Lilong unless credited otherwise. You are welcome to share links to our stories. Please do not copy or republish our original content in full without permission. Photos and material from other publishers belong to their owners and are credited on each story.</p>'
        '<h2>Other websites</h2><p>The Site links to other websites, including the publishers that first reported a story and social media platforms. We do not control those sites and are not responsible for their content.</p>'
        '<h2>Advertising</h2><p>The Site shows advertisements served by Google AdSense. Ads are provided by third parties, and showing an ad does not mean we endorse the product or service. See our <a href="privacy-policy.html">Privacy Policy</a> for how advertising cookies work.</p>'
        '<h2>Liability</h2><p>To the extent allowed by law, Mirror Lilong is not liable for any loss or damage arising from the use of the Site or reliance on its content.</p>'
        '<h2>Changes</h2><p>We may update these terms at any time. The date at the top shows when they were last changed.</p>'
        '<h2>Governing law</h2><p>These terms are governed by the laws of India.</p>'
        '<h2>Contact</h2><p>Questions about these terms? Email us at <a href="mailto:mirrorlilong@gmail.com">mirrorlilong@gmail.com</a> or message us on our %s or see our <a href="contact.html">Contact</a> page.</p>') % fb
    return [
        ('about.html', info_page('About Us | Mirror Lilong', 'About Mirror Lilong, independent local news from Lilong and Manipur.', 'About Mirror Lilong', about, ctx)),
        ('contact.html', info_page('Contact Us | Mirror Lilong', 'How to contact the Mirror Lilong team with news tips, corrections and questions.', 'Contact Us', contact, ctx)),
        ('privacy-policy.html', info_page('Privacy Policy | Mirror Lilong', 'How Mirror Lilong handles information, cookies and Google AdSense advertising.', 'Privacy Policy', privacy, ctx)),
        ('terms.html', info_page('Terms of Use | Mirror Lilong', 'Terms of use and disclaimer for mirrorlilong.com.', 'Terms of Use', terms, ctx)),
    ]

def build_search(ctx):
    main = ('<div class="cat-head"><h1>Search</h1><p id="srCount"></p></div>'
            '<form class="sr-form" action="/search" method="get" role="search"><input class="sr-input" id="srInput" type="search" name="q" placeholder="Search Mirror Lilong news" autocomplete="off" enterkeyhint="search" aria-label="Search news"><button type="submit">Search</button></form>'
            '<div class="two-col"><div class="col-main"><div id="srResults" class="sr-results" aria-live="polite"><noscript><p class="note">Search needs JavaScript turned on.</p></noscript></div></div><aside class="col-side">%s%s</aside></div>') % (trending(ctx), follow_box())
    return page('Search | Mirror Lilong', 'Search all Mirror Lilong news stories.', None, main, ctx)

def build_404(stories, ctx):
    """Branded 'page not found' page. GitHub Pages serves /404.html for any missing URL, at any depth,
    so main() turns every relative link/asset in it into a root path (see root_paths)."""
    latest = ''.join(card(s, 'm', True) for s in stories[:6])
    main = ('<section class="e404"><p class="e404-code" aria-hidden="true">404</p><h1>Page not found</h1>'
            '<p class="e404-msg">The story you&rsquo;re looking for may have moved or been removed.</p>'
            '<form class="sr-form e404-form" action="/search" method="get" role="search"><input class="sr-input" type="search" name="q" placeholder="Search Mirror Lilong news" autocomplete="off" enterkeyhint="search" aria-label="Search news"><button type="submit">Search</button></form>'
            '<a class="e404-home" href="index.html">Go to homepage</a></section>'
            '%s<div class="grid g3">%s</div>') % (sec_title('Latest stories', 'index.html'), latest)
    return page('Page not found | Mirror Lilong', 'This page could not be found on Mirror Lilong.', None, main, ctx,
                head='<meta name="robots" content="noindex">')

def root_paths(text):
    """Relative href/src/srcset -> root paths ('styles.css' -> '/styles.css'), for pages served at any depth."""
    return re.sub(r'(\s(?:href|src|srcset)=")(?!(?:https?:|//|/|#|mailto:|tel:|data:|javascript:))([^"]+)"', r'\1/\2"', text)

def search_index(stories):
    return json.dumps([{'t': s['title'], 's': s['summary'], 'c': s['cat'], 'a': s.get('also_in') or '', 'st': s.get('states', []),
                        'd': iso(s), 'df': fdate(s), 'u': '/' + url(s)[:-5], 'i': s['img'] if s['img'].startswith('http') else '/' + s['img']} for s in stories],
                      ensure_ascii=False, separators=(',', ':'))


# ---------- Writers: Opinion, Prose & Verse ----------
# content/writers/<slug>.json  : one file per writer (Pages CMS "Writers")
# content/writings/<slug>.json : one file per piece (Pages CMS "Writings (Opinion, Prose & Verse, Story, Article)"),
#                                category "Opinion", "Prose & Verse", "Story" or "Article"
# A news story may also name a writer ("writer" field) to get a byline and an author box.
# These pages are English only: translate_inject.py only touches news-*.html.
WRITER_ROLES = ['Journalist', 'Correspondent', 'Columnist', 'Guest Writer', 'Blogger', 'Poet', 'Author', 'Editor']
# (category name, css key, listing page); a piece's page is <listing page name>-<slug>.html
WR_CATS = [('Opinion', 'opinion', 'opinion.html'), ('Prose & Verse', 'pv', 'prose-verse.html'),
           ('Story', 'story', 'story.html'), ('Article', 'article', 'article.html')]
WR_CAT_INFO = {
    'Opinion': ('Opinion', 'Views, columns and analysis from the writers of Mirror Lilong.'),
    'Prose & Verse': ('Prose &amp; Verse', 'Prose and poems from the writers of Mirror Lilong.'),
    'Story': ('Story', 'Short stories and fiction from the writers of Mirror Lilong.'),
    'Article': ('Article', 'Articles, features and essays from the writers of Mirror Lilong.'),
}
WR_PLURAL = {'Story': 'Stories', 'Article': 'Articles'}  # 'All Stories', 'No stories yet.'
X_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><path fill="currentColor" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>'
IG_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke="currentColor" stroke-width="2.2"/><circle cx="12" cy="12" r="4.2" fill="none" stroke="currentColor" stroke-width="2.2"/><circle cx="17.4" cy="6.6" r="1.3" fill="currentColor"/></svg>'
MAIL_SVG = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><rect x="2.5" y="5" width="19" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="2.2"/><path d="m3.5 6.5 8.5 7 8.5-7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round"/></svg>'
QUOTE_SVG = '<svg viewBox="0 0 32 32" width="34" height="34" aria-hidden="true" focusable="false"><path fill="currentColor" d="M13 7C7.5 8.6 4 13 4 18.6 4 22.6 6.4 25 9.6 25c2.9 0 5-2.1 5-4.9 0-2.7-1.9-4.6-4.5-4.6-.5 0-1 .1-1.3.2.6-2.9 3-5.4 6.2-6.6zm14 0c-5.5 1.6-9 6-9 11.6 0 4 2.4 6.4 5.6 6.4 2.9 0 5-2.1 5-4.9 0-2.7-1.9-4.6-4.5-4.6-.5 0-1 .1-1.3.2.6-2.9 3-5.4 6.2-6.6z"/></svg>'


def _slug(t): return re.sub(r'[^a-z0-9]+', '-', str(t or '').lower()).strip('-')

def wr_cat(v):
    """'Opinion', 'Prose & Verse', 'Story' or 'Article' (also accepts 'prose', 'verse', 'poem', 'stories', 'articles' ...)."""
    v = str(v or '').strip().lower()
    if v in ('story', 'stories', 'short story', 'fiction'):
        return 'Story'
    if v in ('article', 'articles', 'feature', 'essay'):
        return 'Article'
    if v and (v.startswith('prose') or v in ('verse', 'poem', 'poetry', 'poems')):
        return 'Prose & Verse'
    return 'Opinion'

def wr_cat_key(c): return {n: k for n, k, _ in WR_CATS}.get(c, 'opinion')
def wr_cat_page(c): return {n: p for n, _, p in WR_CATS}.get(c, 'opinion.html')

def load_writers():
    folder = os.path.join(CONTENT, 'writers')
    out = {}
    if not os.path.isdir(folder):
        return out
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith('.json'):
            continue
        try:
            w = json.load(open(os.path.join(folder, fn), encoding='utf-8'))
        except Exception as e:
            warn('skipped writer %s: not valid JSON (%s)' % (fn, e)); continue
        if not isinstance(w, dict) or not str(w.get('name') or '').strip() or w.get('hidden'):
            continue
        w['name'] = str(w['name']).strip()
        w['slug'] = _slug(fn[:-5]) or _slug(w['name'])
        if not w['slug']:
            continue
        w['role'] = w.get('role') if w.get('role') in WRITER_ROLES else 'Writer'
        w['bio'] = str(w.get('bio') or '').strip()
        w['photo_src'] = asset(w.get('photo')) if str(w.get('photo') or '').strip() else ''
        w['posts'] = []
        out[w['slug']] = w
    return out

def find_writer(writers, ref):
    """A writer reference from the CMS: 'content/writers/x.json', 'x.json', 'x' or the writer's name."""
    r = str(ref or '').strip()
    if not r:
        return None
    key = _slug(os.path.basename(r)[:-5] if r.endswith('.json') else r)
    if key in writers:
        return writers[key]
    for w in writers.values():
        if _slug(w['name']) == key:
            return w
    return None

def load_writings(writers):
    folder = os.path.join(CONTENT, 'writings')
    out = []
    if not os.path.isdir(folder):
        return out
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith('.json'):
            continue
        try:
            s = json.load(open(os.path.join(folder, fn), encoding='utf-8'))
        except Exception as e:
            warn('skipped writing %s: not valid JSON (%s)' % (fn, e)); continue
        if not isinstance(s, dict) or not str(s.get('title') or '').strip() or s.get('hidden'):
            continue
        s['slug'] = _slug(fn[:-5]) or _slug(s['title'])
        if not s['slug']:
            continue
        s['category'] = wr_cat(s.get('category'))
        s['type'] = s['category']
        s['ck'] = wr_cat_key(s['category'])
        s['_page'] = '%s-%s.html' % (wr_cat_page(s['category'])[:-5], s['slug'])
        s['title'] = str(s['title']).strip()
        s['dt'] = parse_date(s.get('date')) or datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(folder, fn)), IST)
        s['cat'] = s['category']
        s['summary'] = str(s.get('summary') or '').strip()
        s['img'] = asset(s.get('image')) if str(s.get('image') or '').strip() else ''
        s['full'] = s['img']
        s['w'] = find_writer(writers, s.get('writer'))
        if s.get('writer') and not s['w']:
            warn('%s: writer %r not found in content/writers' % (fn, s.get('writer')))
        out.append(s)
    out.sort(key=lambda s: (s['dt'], s['slug']), reverse=True)
    for s in out:
        if s['w']:
            s['w']['posts'].append(s)
    return out

def initials(name):
    parts = [p for p in re.split(r'[\s.]+', name) if p and p[0].isalnum()]
    return ((parts[0][0] + (parts[-1][0] if len(parts) > 1 else '')) if parts else '?').upper()

def avatar(w, size='m'):
    if not w:
        return '<span class="av av-%s av-desk" aria-hidden="true"><img src="favicon-192.png" alt=""></span>' % size
    if w['photo_src']:
        return '<span class="av av-%s"><img src="%s" alt="%s" loading="lazy"></span>' % (size, esc(w['photo_src']), esc(w['name']))
    hue = sum(map(ord, w['slug'])) % 4
    return '<span class="av av-%s av-ini av-c%d" aria-hidden="true">%s</span>' % (size, hue, esc(initials(w['name'])))

def wurl(w): return 'writer-%s.html' % w['slug']

def socials(w):
    out = []
    if w.get('facebook'): out.append('<a class="so so-fb" href="%s" target="_blank" rel="noopener" aria-label="Facebook">%s</a>' % (esc(w['facebook']), FB_SVG))
    if w.get('instagram'): out.append('<a class="so so-ig" href="%s" target="_blank" rel="noopener" aria-label="Instagram">%s</a>' % (esc(w['instagram']), IG_SVG))
    if w.get('x'): out.append('<a class="so so-x" href="%s" target="_blank" rel="noopener" aria-label="X (Twitter)">%s</a>' % (esc(w['x']), X_SVG))
    if w.get('email'): out.append('<a class="so so-em" href="mailto:%s" aria-label="Email">%s</a>' % (esc(w['email']), MAIL_SVG))
    return '<div class="socials">%s</div>' % ''.join(out) if out else ''

def wcount(w):
    n = len(w['posts']) + len(w.get('news', []))
    return '%d piece%s' % (n, '' if n == 1 else 's')

def writer_card(w):
    bio = w['bio'] if len(w['bio']) <= 140 else w['bio'][:137].rsplit(' ', 1)[0] + '…'
    return ('<article class="wcard"><a href="%s" class="wcard-link">%s<div class="wcard-body"><span class="wrole">%s</span><h3>%s</h3><p>%s</p>'
            '<span class="wcount">%s &rsaquo;</span></div></a></article>') % (wurl(w), avatar(w, 'l'), esc(w['role']), esc(w['name']), esc(bio), wcount(w))

def op_item(s, show_author=True):
    w = s['w']
    who = ('<span class="op-by">%s<span><b>%s</b>%s</span></span>' % (avatar(w, 's'), esc(w['name']) if w else 'Mirror Lilong', (' &middot; ' + esc(w['role'])) if w else '')) if show_author else ''
    dek = '<p class="dek">%s</p>' % esc(s['summary']) if s['summary'] else ''
    return ('<article class="op-item"><a href="%s"><span class="op-type op-%s">%s</span><h3>%s</h3>%s<div class="op-foot">%s<time datetime="%s">%s</time></div></a></article>') % (
            s['_page'], s['ck'], esc(s['category']), esc(s['title']), dek, who, iso(s), fdate(s))

def wr_chips(current=None):
    """Writers / Opinion / Prose & Verse tabs at the top of the section pages."""
    tabs = [('All', 'writers.html', None)] + [(n, p, n) for n, _, p in WR_CATS]
    return '<nav class="chips wr-chips" aria-label="Writers sections">%s</nav>' % ''.join(
        '<a href="%s"%s>%s</a>' % (p, ' aria-current="page"' if c == current else '', esc(n)) for n, p, c in tabs)

def write_for_us():
    return ('<section class="wfu"><h2>Write for Mirror Lilong</h2><p>Writers, poets and columnists from Lilong, Manipur and the Northeast are welcome. '
            'Send us your opinion piece, article, story or poem.</p><a class="wfu-btn" href="contact.html">Send your writing &rsaquo;</a></section>')

def wr_empty(text):
    return '<div class="empty-state wr-empty"><p class="es-big">%s</p><p>New pieces from our writers will appear here.</p></div>' % text

def build_writers(writers, writings, ctx):
    ws = sorted(writers.values(), key=lambda w: (-(len(w['posts']) + len(w.get('news', []))), w['name']))
    grid = '<section class="block">%s<div class="wgrid">%s</div></section>' % (sec_title('Our Writers'), ''.join(writer_card(w) for w in ws)) if ws else ''
    lst = '<div class="op-list">%s</div>' % ''.join(op_item(s) for s in writings[:20]) if writings else wr_empty('Coming soon.')
    main = ('<nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a> &rsaquo; Writers</nav>'
            '<div class="cat-head wr-head"><h1>Writers</h1><p>Opinion, prose &amp; verse, stories and articles from the writers of Mirror Lilong</p></div>%s%s'
            '<div class="two-col"><div class="col-main"><section class="block">%s%s</section></div>'
            '<aside class="col-side">%s%s</aside></div>') % (wr_chips(), grid, sec_title('Latest from our writers'), lst, write_for_us(), follow_box())
    return page('Writers | Mirror Lilong', 'Opinion, prose & verse, stories and articles from the writers of Mirror Lilong.', 'Writers', main, ctx)

def build_wr_cat(writings, cat, ctx):
    h, desc = WR_CAT_INFO[cat]
    items = [s for s in writings if s['category'] == cat]
    lst = '<div class="op-list">%s</div>' % ''.join(op_item(s) for s in items) if items else wr_empty('No %s yet.' % WR_PLURAL[cat].lower() if cat in WR_PLURAL else 'No %s pieces yet.' % h)
    main = ('<nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a> &rsaquo; <a href="writers.html">Writers</a> &rsaquo; %s</nav>'
            '<div class="cat-head wr-head"><h1>%s</h1><p>%s</p></div>%s'
            '<div class="two-col"><div class="col-main"><section class="block">%s</section></div>'
            '<aside class="col-side">%s%s</aside></div>') % (h, h, esc(desc), wr_chips(cat), lst, write_for_us(), follow_box())
    return page('%s | Writers | Mirror Lilong' % cat, desc, 'Writers', main, ctx)

def build_writer(w, writings, ctx):
    items = ''.join(op_item(s, False) for s in w['posts'])
    news = w.get('news', [])
    if news:
        items += '<div class="grid g2 w-news">%s</div>' % ''.join(card(s) for s in news[:12])
    if not items:
        items = '<p class="note">No pieces yet.</p>'
    bio = markdown(w['bio']) if w['bio'] else ''
    loc = '<span class="wloc">%s</span>' % esc(w['location']) if w.get('location') else ''
    others = [x for x in writings if x['w'] is not w][:4]
    more = '<section class="block">%s<div class="op-list">%s</div></section>' % (sec_title('More from our writers', 'writers.html'), ''.join(op_item(s) for s in others)) if others else ''
    main = ('<nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a> &rsaquo; <a href="writers.html">Writers</a> &rsaquo; %s</nav>'
            '<section class="wprof"><div class="wprof-band"></div><div class="wprof-in">%s<div class="wprof-txt"><span class="wrole">%s</span><h1>%s</h1>%s'
            '<div class="wstats"><b>%s</b></div></div></div><div class="wprof-bio">%s%s</div></section>'
            '<div class="two-col"><div class="col-main"><section class="block">%s<div class="op-list">%s</div></section>%s</div>'
            '<aside class="col-side">%s%s</aside></div>') % (
            esc(w['name']), avatar(w, 'xl'), esc(w['role']), esc(w['name']), loc, wcount(w), bio, socials(w),
            sec_title('By ' + esc(w['name'])), items, more, write_for_us(), follow_box())
    return page('%s, %s | Mirror Lilong' % (w['name'], w['role']), w['bio'][:160] or ('%s at Mirror Lilong' % w['role']), 'Writers', main, ctx, w['photo_src'] or None)

def author_box(w, top=False):
    if not w:
        return ''
    if top:
        return ('<div class="op-author"><a href="%s">%s</a><div><a class="oa-name" href="%s">%s</a><span class="oa-role">%s</span></div></div>') % (
                wurl(w), avatar(w, 'm'), wurl(w), esc(w['name']), esc(w['role']))
    return ('<aside class="abox"><span class="abox-lab">About the writer</span><div class="abox-in"><a href="%s">%s</a><div><a class="oa-name" href="%s">%s</a>'
            '<span class="oa-role">%s</span><p>%s</p>%s<a class="abox-more" href="%s">All pieces by %s &rsaquo;</a></div></div></aside>') % (
            wurl(w), avatar(w, 'l'), wurl(w), esc(w['name']), esc(w['role']), esc(w['bio']), socials(w), wurl(w), esc(w['name']))

def build_writing(writings, s, ctx):
    w = s['w']
    pv = s['ck'] == 'pv'
    story = s['ck'] == 'story'
    # Prose & Verse and Story keep the author's single line breaks (poems, dialogue)
    body = article_body(s, keep_lines=pv or story)
    pq = str(s.get('pull_quote') or '').strip()
    if pq and not pv and not story:
        quote_html = '<blockquote class="pullq">%s<p>%s</p></blockquote>' % (QUOTE_SVG, esc(pq))
        k = [m.end() for m in re.finditer(r'</p>', body)]
        body = body[:k[1]] + quote_html + body[k[1]:] if len(k) > 3 else body + quote_html
    fig = ''
    if s['img']:
        cap = s.get('image_credit') or ''
        fig = '<figure class="art-fig"><img src="%s" alt="%s">%s</figure>' % (esc(s['img']), esc(s['title']), '<figcaption>%s</figcaption>' % inline(cap) if cap else '')
    dek = '<p class="art-dek">%s</p>' % esc(s['summary']) if s['summary'] else ''
    if pv or story:
        disc = '<p class="op-disc pv-note">&copy; %s. Published on Mirror Lilong with the author&#8217;s permission.</p>' % (esc(w['name']) if w else 'The author')
    else:
        disc = '<p class="op-disc"><b>Disclaimer:</b> The views expressed in this article are the author&#8217;s own and do not necessarily reflect those of Mirror Lilong.</p>'
    h, _ = WR_CAT_INFO[s['category']]
    cpage = wr_cat_page(s['category'])
    same = [x for x in writings if x is not s and x['category'] == s['category']]
    more = (same + [x for x in writings if x is not s and x['category'] != s['category']])[:4]
    rel = '<section class="block">%s<div class="op-list op-list-2">%s</div></section>' % (sec_title('More from our writers', 'writers.html'), ''.join(op_item(x) for x in more)) if more else ''
    main = ('<div class="two-col article-wrap"><article class="article op-article%s"><nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a> &rsaquo; <a href="writers.html">Writers</a> &rsaquo; <a href="%s">%s</a></nav>'
            '<span class="op-label op-%s">%s</span><h1>%s</h1>%s<div class="art-meta op-meta">%s<time datetime="%s">%s</time></div>%s%s'
            '<div class="art-body%s">%s</div>%s%s%s<p class="back"><a href="%s">&lsaquo; All %s</a></p></article>'
            '<aside class="col-side">%s%s%s</aside></div>%s') % (
            {'pv': ' pv-article', 'story': ' story-article'}.get(s['ck'], ''), cpage, h,
            s['ck'], h, esc(s['title']), dek, author_box(w, True), iso(s), fdate(s), share_bar(s, 'top'), fig,
            {'pv': ' pv-body', 'story': ' story-body'}.get(s['ck'], ''), body, disc, author_box(w), share_bar(s, 'end'), cpage, WR_PLURAL.get(s['category'], h),
            write_for_us(), trending(ctx, s), follow_box(), rel)
    by = (' by ' + w['name']) if w else ''
    return page('%s%s | Mirror Lilong' % (s['title'], by), s['summary'] or s['title'], 'Writers', main, ctx, s['img'] or None,
                og_type='article', head=article_head(s, s['_page'], news=False))

def main():
    stories = load_stories()
    if not stories:
        sys.exit('No stories found in content/stories/')
    videos = load_videos()
    writers = load_writers()
    writings = load_writings(writers)
    for s in stories:  # optional byline on news stories
        s['w'] = find_writer(writers, s.get('writer'))
        if s['w']:
            s['w'].setdefault('news', []).append(s)
    now = datetime.datetime.now(IST)
    slides = flagged(stories, 'lead', 5)  # homepage slider: 5 newest lead stories, topped up with newest others
    lead = slides[0]
    ctx = dict(today=now.strftime('%A, ') + str(now.day) + now.strftime(' %B %Y'), year=now.year, lead=lead, slides=slides)
    ctx['top'] = flagged(stories, 'top', 5)  # 5 newest Top-Story-flagged stories, even if also in the slider
    ctx['tick'] = flagged(stories, 'breaking', 7)
    ctx['now'] = datetime.datetime.now(datetime.timezone.utc)
    # Admin-flagged Trending posts show only for 12 hours after their publish time (Hemat, 4 Nov 2026)
    def _fresh12(s):
        try:
            d = s['dt']
            if d.tzinfo is None:
                d = d.replace(tzinfo=IST)
            return (ctx['now'] - d).total_seconds() <= 12 * 3600
        except Exception:
            return False
    _tf = [s for s in stories if s.get('trending') and _fresh12(s)][:8]
    ctx['trend'] = _tf + [s for s in stories if s not in _tf and not s.get('trending')][:8 - len(_tf)]
    ctx['trend_own'] = [s for s in stories if s.get('trending') and _fresh12(s)]  # switched to Trending AND under 12h old, newest first
    # Trending: the latest real news (Manipur > Northeast > India > World) read from publishers' feeds at
    # build time; the workflow rebuilds every 3 hours. Any failure keeps the last good list or the old box.
    ctx['news'] = None
    if os.environ.get('TRENDING', '1') != '0':
        try:
            import trending as trending_feed
            ctx['news'] = trending_feed.get_trending()
        except Exception as e:
            warn('trending news skipped (%s)' % e)
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT, ignore=shutil.ignore_patterns('.gitkeep', '.DS_Store'))
    def w(name, text):
        # clean URLs: home -> '/', other pages without '.html' (GitHub Pages serves both)
        text = re.sub(r'href="index\.html"', 'href="/"', text)
        text = re.sub(r'href="([a-z0-9][a-z0-9-]*)\.html"', r'href="/\1"', text)
        # SEO: canonical URL (+ og:url) and, on pages without article data, Organization/WebSite JSON-LD
        if name != '404.html' and '</head>' in text and 'rel="canonical"' not in text:
            cu = page_url(name)
            extra = '<link rel="canonical" href="%s"><meta property="og:url" content="%s">' % (cu, cu)
            if 'application/ld+json' not in text:
                extra += site_ld(home=(name == 'index.html'))
            text = text.replace('</head>', extra + '</head>', 1)
        if name == '404.html':
            text = root_paths(text)  # served for missing URLs at any depth
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
            f.write(text)
    w('index.html', build_index(stories, ctx))
    for c in CATS:
        w(c.lower() + '.html', build_cat(stories, c, ctx))
    w('videos.html', build_videos(stories, videos, ctx))
    for st in NE_NAMES:
        w(state_page(st), build_state(stories, st, ctx))
    w('search.html', build_search(ctx))
    w('404.html', build_404(stories, ctx))  # custom 'page not found' (no GitHub page)
    with open(os.path.join(OUT, 'search.json'), 'w', encoding='utf-8') as f:
        f.write(search_index(stories))
    for name, text in build_info(ctx):
        w(name, text)
    if ctx['news']:
        with open(os.path.join(OUT, 'trending.json'), 'w', encoding='utf-8') as f:
            json.dump(ctx['news'], f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'ads.txt'), 'w', encoding='utf-8') as f:
        f.write('google.com, pub-4739495411759158, DIRECT, f08c47fec0942fa0\n')
    # Writers section (English only): /writers, /opinion, /prose-verse, /story, /article, /writer-<slug>, /<category>-<slug>
    w('writers.html', build_writers(writers, writings, ctx))
    for cname, _, cpage in WR_CATS:
        w(cpage, build_wr_cat(writings, cname, ctx))
    for wr in writers.values():
        w(wurl(wr), build_writer(wr, writings, ctx))
    for s in writings:
        w(s['_page'], build_writing(writings, s, ctx))
    for s in stories:
        w(url(s), build_article(stories, s, ctx))
        for p in (s['img'], s['full']):
            if not p.startswith('http') and not os.path.exists(os.path.join(OUT, p)):
                warn('%s: image %s is missing' % (s['slug'], p))
    # sitemap.xml + robots.txt for Google
    import datetime as _dt
    _today = _dt.date.today().isoformat()
    _urls = []
    _mod = {}  # story/writing page -> its own date (lastmod)
    for _s in list(stories) + list(writings):
        _d = (parse_date(_s.get('updated') or _s.get('modified')) or _s['dt']).replace(microsecond=0)
        _mod[_s.get('_page') or url(_s)] = max(_d, _s['dt'].replace(microsecond=0)).isoformat()
    for _fn in sorted(os.listdir(OUT)):
        if _fn.endswith('.html') and _fn not in ('search.html', '404.html'):
            _u = SITE + '/' if _fn == 'index.html' else SITE + '/' + _fn[:-5]
            _urls.append('<url><loc>%s</loc><lastmod>%s</lastmod></url>' % (_u, _mod.get(_fn, _today)))
    with open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(_urls) + '\n</urlset>\n')
    with open(os.path.join(OUT, 'robots.txt'), 'w', encoding='utf-8') as f:
        f.write('User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: %s/sitemap.xml\nSitemap: %s/news-sitemap.xml\n' % (SITE, SITE))
    # Google News sitemap: news stories published in the last 2 days (Google's limit), newest first
    _cut = datetime.datetime.now(IST) - datetime.timedelta(days=2)
    _news = []
    for _s in stories:
        if _s['dt'] < _cut or _s['dt'] > datetime.datetime.now(IST) + datetime.timedelta(hours=1):
            continue
        _news.append('<url><loc>%s</loc><news:news><news:publication><news:name>Mirror Lilong</news:name><news:language>en</news:language></news:publication>'
                     '<news:publication_date>%s</news:publication_date><news:title>%s</news:title></news:news></url>' % (
                         page_url(url(_s)), _s['dt'].replace(microsecond=0).isoformat(), html.escape(_s['title'], quote=False)))
    with open(os.path.join(OUT, 'news-sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n'
                + '\n'.join(_news[:1000]) + ('\n' if _news else '') + '</urlset>\n')
    print('Built %d stories into _site/ (lead: %s)' % (len(stories), lead['slug']))

if __name__ == '__main__':
    main()
