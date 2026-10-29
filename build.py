#!/usr/bin/env python3
"""Mirror Lilong site builder.

Reads one JSON file per story from content/stories/ (written by the admin panel at /admin),
plus content/settings/videos.json, and writes the finished static site into _site/.
Standard library only: no packages to install. Run:  python3 build.py
"""
import json, html, datetime, os, re, shutil, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(HERE, 'content')
STATIC = os.path.join(HERE, 'static')
OUT = os.path.join(HERE, '_site')
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
esc = html.escape

FBPAGE = 'https://www.facebook.com/100077335757093/'
IG = 'https://www.instagram.com/mirrorlilong/'
YT = 'https://www.youtube.com/@teammirrormanipur'
CATS = ['Manipur', 'Northeast', 'India', 'World', 'Sports', 'Entertainment']
NAV = [('Home', 'index.html')] + [(c, c.lower() + '.html') for c in CATS] + [('Videos', 'videos.html')]

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

def markdown(text):
    text = str(text or '').replace('\r\n', '\n').replace('\u00a0', ' ').strip()
    out = []
    for block in re.split(r'\n\s*\n', text):
        block = block.strip('\n')
        if not block.strip():
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
        out.append('<p>%s</p>' % inline(block))
    return ''.join(out)

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
def url(s): return 'news-%s.html' % s['slug']
def ext(u, label): return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (esc(u), label)
def badge(s): return '<span class="desk">Mirror Lilong</span>' if s.get('desk') else ''

def card(s, size='m', dek=False):
    play = '<span class="play" aria-hidden="true"></span>' if s.get('video') else ''
    d = '<p class="dek">%s</p>' % esc(s['summary']) if dek and s['summary'] else ''
    return ('<article class="card card-%s"><a href="%s" class="card-link"><div class="thumb"><img src="%s" alt="" loading="lazy" width="1200" height="675">%s</div>'
            '<div class="card-body"><div class="meta-top"><span class="kicker">%s</span>%s</div><h3>%s</h3>%s<time datetime="%s">%s</time></div></a></article>') % (
            size, url(s), esc(s['img']), play, esc(s['cat']), badge(s), esc(s['title']), d, iso(s), fdate(s))

def header(active, ctx):
    nav = ''.join('<li><a href="%s"%s>%s</a></li>' % (h, ' aria-current="page"' if n == active else '', n) for n, h in NAV)
    tick = ' <span class="sep" aria-hidden="true">&#9670;</span> '.join('<a href="%s">%s</a>' % (url(s), esc(s['title'])) for s in ctx['tick'])
    return ('<a class="skip" href="#main">Skip to content</a>'
     '<div class="topbar"><div class="wrap topbar-in"><span id="today" class="today">%s</span><span class="topbar-links">%s%s%s</span></div></div>'
     '<header class="masthead"><div class="wrap mast-in"><button class="menu-btn" id="menuBtn" type="button" aria-controls="mainNav" aria-expanded="false" aria-label="Open sections menu"><span></span><span></span><span></span></button>'
     '<a href="index.html" class="brand"><picture><source srcset="logo.webp" type="image/webp"><img src="logo.png" alt="Mirror Lilong" width="1200" height="197"></picture></a><a class="watch-btn" href="videos.html"><span class="dot" aria-hidden="true"></span>Watch</a></div>'
     '<nav class="mainnav" id="mainNav" aria-label="Sections"><ul class="wrap">%s</ul></nav></header>'
     '<div class="ticker" role="region" aria-label="Breaking news"><div class="wrap ticker-in"><span class="ticker-label">Breaking</span><div class="ticker-track"><div class="ticker-move"><span>%s</span><span aria-hidden="true">%s</span></div></div></div></div>') % (
     ctx['today'], ext(FBPAGE, 'Facebook'), ext(IG, 'Instagram'), ext(YT, 'YouTube'), nav, tick, tick.replace('<a ', '<a tabindex="-1" '))

def footer(ctx):
    cats = ''.join('<li><a href="%s">%s</a></li>' % (h, n) for n, h in NAV[1:])
    return ('<footer class="footer"><div class="wrap foot-in"><div class="foot-brand"><picture><source srcset="logo-white.webp" type="image/webp"><img src="logo-white.png" alt="Mirror Lilong" width="1200" height="197" loading="lazy"></picture>'
     '<p>News, interviews and stories from Lilong, Manipur and the Northeast.</p><p class="social">%s &middot; %s &middot; %s</p></div>'
     '<div><h2 class="foot-h">Sections</h2><ul class="foot-list">%s</ul></div>'
     '<div><h2 class="foot-h">About our stories</h2><p class="small">Stories marked <b>Mirror Lilong</b> come from the Mirror Lilong desk. Other stories are short original summaries, and each one links to the publisher that first reported it. Photos are credited on each story.</p></div></div>'
     '<div class="copy"><div class="wrap copy-in"><span>&copy; %s Mirror Lilong &middot; Imphal, Manipur</span><nav class="foot-legal" aria-label="About Mirror Lilong"><a href="about.html">About</a> &middot; <a href="contact.html">Contact</a> &middot; <a href="privacy-policy.html">Privacy Policy</a> &middot; <a href="terms.html">Terms</a></nav></div></div></footer><script src="script.js" defer></script>') % (
     ext(FBPAGE, 'Facebook'), ext(IG, 'Instagram'), ext(YT, 'YouTube'), cats, ctx['year'])

def page(title, desc, active, main, ctx, og_img=None):
    og = ('<meta property="og:title" content="%s"><meta property="og:description" content="%s"><meta property="og:type" content="website">' % (esc(title), esc(desc)))
    base = os.environ.get('URL', '').rstrip('/')  # Netlify sets URL to the site's address
    if og_img and base:
        og += '<meta property="og:image" content="%s">' % esc(og_img if og_img.startswith('http') else base + '/' + og_img)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
     '<title>%s</title><meta name="description" content="%s">%s<meta name="theme-color" content="#d7141a"><link rel="icon" href="favicon-32.png" sizes="32x32" type="image/png"><link rel="icon" href="favicon-192.png" sizes="192x192" type="image/png"><link rel="apple-touch-icon" href="apple-touch-icon.png"><link rel="stylesheet" href="styles.css"><meta name="google-adsense-account" content="ca-pub-4739495411759158"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-4739495411759158" crossorigin="anonymous"></script></head><body>'
     '%s<main id="main" class="wrap">%s</main>%s</body></html>') % (esc(title), esc(desc), og, header(active, ctx), main, footer(ctx))

def sec_title(t, href=None):
    more = ' <a class="more" href="%s">More &rsaquo;</a>' % href if href else ''
    return '<h2 class="sec-title"><span>%s</span>%s</h2>' % (t, more)

def trending(ctx, exclude=None, n=6):
    lst = [s for s in ctx['trend'] if s is not exclude][:n]
    items = ''.join('<li><a href="%s"><span class="num">%d</span><span class="tt">%s</span></a></li>' % (url(s), i + 1, esc(s['title'])) for i, s in enumerate(lst))
    return '<section class="trending" aria-label="Trending">%s<ol>%s</ol></section>' % (sec_title('Trending'), items)

def follow_box():
    return ('<section class="follow">%s<p>Get Lilong and Manipur news as it happens.</p><div class="follow-btns">%s%s%s</div></section>') % (
        sec_title('Follow Mirror Lilong'), '<a class="fb" href="%s" target="_blank" rel="noopener">Facebook</a>' % FBPAGE,
        '<a class="ig" href="%s" target="_blank" rel="noopener">Instagram</a>' % IG, '<a class="yt" href="%s" target="_blank" rel="noopener">YouTube</a>' % YT)

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
          '<div class="lead-body"><div class="meta-top"><span class="kicker">%s</span>%s</div><%s>%s</%s><p class="dek">%s</p><time datetime="%s">%s</time></div></a></article>') % (
          k + 1, n, url(s), '' if k == 0 else ' tabindex="-1"', esc(s['img']), esc(s['title']), lazy, s['cat'], badge(s), h, esc(s['title']), h, esc(s['summary']), iso(s), fdate(s)))
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
    parts.append('<div class="two-col"><div class="col-main">%s</div><aside class="col-side">%s%s</aside></div>' % (''.join(main_col), trending(ctx), follow_box()))
    return page('Mirror Lilong | Latest news from Lilong, Manipur and the Northeast', 'Mirror Lilong brings the latest news from Lilong, Manipur, the Northeast, India and the world.', 'Home', ''.join(parts), ctx, lead['img'])

def bycat(stories, c): return [s for s in stories if s['cat'] == c or s.get('also_in') == c]

def build_cat(stories, c, ctx):
    lst = bycat(stories, c)
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
    dek = '<p class="art-dek">%s</p>' % esc(s['summary']) if s['summary'] else ''
    main = ('<div class="two-col article-wrap"><article class="article"><nav class="crumbs" aria-label="Breadcrumb"><a href="index.html">Home</a> &rsaquo; <a href="%s">%s</a></nav>'
          '<h1>%s</h1>%s<div class="art-meta"><span class="by">%s</span>%s<time datetime="%s">%s</time></div>%s'
          '<div class="art-body">%s</div>%s<p class="back"><a href="index.html">&lsaquo; Back to home</a></p></article>'
          '<aside class="col-side">%s%s</aside></div>%s') % (s['cat'].lower() + '.html', s['cat'], esc(s['title']), dek, by, badge(s), iso(s), fdate(s), fig,
          markdown(s.get('body')), srcs, trending(ctx, s), follow_box(), rel)
    return page('%s | Mirror Lilong' % s['title'], s['summary'] or s['title'], s['cat'], main, ctx, s['img'])

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
        '<h2>Message us</h2><p>The fastest way to reach the Mirror Lilong team is to send us a message on our %s. We read every message.</p>'
        '<ul><li>Facebook: %s</li><li>Instagram: %s</li><li>YouTube: %s</li></ul>'
        '<h2>Corrections</h2><p>If you think something in one of our stories is wrong, message us on Facebook with the story link and what needs fixing. We will check it and correct the story if needed.</p>'
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
        '<h2>Analytics</h2><p>We do not currently use any analytics or visitor-tracking service on the Site. If we add one in the future, we will update this policy.</p>'
        '<h2>Links to other websites</h2><p>Our stories link to other websites, such as the publishers that first reported a story, and to our social media pages. We are not responsible for the content or privacy practices of those sites.</p>'
        '<h2>Children</h2><p>The Site is a general news site and is not directed at children under 13. We do not knowingly collect personal information from children.</p>'
        '<h2>Your choices</h2><p>You can control cookies through your browser settings and the opt-out links above. If you have contacted us and want us to delete your messages or any information you sent us, let us know.</p>'
        '<h2>Changes to this policy</h2><p>We may update this policy from time to time. The date at the top shows when it was last changed.</p>'
        '<h2>Governing law</h2><p>This policy is governed by the laws of India.</p>'
        '<h2>Contact</h2><p>For any questions about this Privacy Policy, message us on our %s or see our <a href="contact.html">Contact</a> page.</p>') % fb
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
        '<h2>Contact</h2><p>Questions about these terms? Message us on our %s or see our <a href="contact.html">Contact</a> page.</p>') % fb
    return [
        ('about.html', info_page('About Us | Mirror Lilong', 'About Mirror Lilong, independent local news from Lilong and Manipur.', 'About Mirror Lilong', about, ctx)),
        ('contact.html', info_page('Contact Us | Mirror Lilong', 'How to contact the Mirror Lilong team with news tips, corrections and questions.', 'Contact Us', contact, ctx)),
        ('privacy-policy.html', info_page('Privacy Policy | Mirror Lilong', 'How Mirror Lilong handles information, cookies and Google AdSense advertising.', 'Privacy Policy', privacy, ctx)),
        ('terms.html', info_page('Terms of Use | Mirror Lilong', 'Terms of use and disclaimer for mirrorlilong.com.', 'Terms of Use', terms, ctx)),
    ]

def main():
    stories = load_stories()
    if not stories:
        sys.exit('No stories found in content/stories/')
    videos = load_videos()
    now = datetime.datetime.now(IST)
    slides = flagged(stories, 'lead', 5)  # homepage slider: 5 newest lead stories, topped up with newest others
    lead = slides[0]
    ctx = dict(today=now.strftime('%A, ') + str(now.day) + now.strftime(' %B %Y'), year=now.year, lead=lead, slides=slides)
    ctx['top'] = flagged(stories, 'top', 5, exclude=tuple(slides))
    ctx['tick'] = flagged(stories, 'breaking', 7)
    ctx['trend'] = flagged(stories, 'trending', 8)
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT, ignore=shutil.ignore_patterns('.gitkeep', '.DS_Store'))
    def w(name, text):
        # clean URLs: home -> '/', other pages without '.html' (GitHub Pages serves both)
        text = re.sub(r'href="index\.html"', 'href="/"', text)
        text = re.sub(r'href="([a-z0-9][a-z0-9-]*)\.html"', r'href="/\1"', text)
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
            f.write(text)
    w('index.html', build_index(stories, ctx))
    for c in CATS:
        w(c.lower() + '.html', build_cat(stories, c, ctx))
    w('videos.html', build_videos(stories, videos, ctx))
    for name, text in build_info(ctx):
        w(name, text)
    with open(os.path.join(OUT, 'ads.txt'), 'w', encoding='utf-8') as f:
        f.write('google.com, pub-4739495411759158, DIRECT, f08c47fec0942fa0\n')
    for s in stories:
        w(url(s), build_article(stories, s, ctx))
        for p in (s['img'], s['full']):
            if not p.startswith('http') and not os.path.exists(os.path.join(OUT, p)):
                warn('%s: image %s is missing' % (s['slug'], p))
    print('Built %d stories into _site/ (lead: %s)' % (len(stories), lead['slug']))

if __name__ == '__main__':
    main()
