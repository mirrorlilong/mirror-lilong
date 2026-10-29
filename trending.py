"""Trending news for Mirror Lilong: fetched from publishers' RSS feeds at build time.

Priority: Manipur > Northeast > India > World. Each item keeps its own article photo
(feed media/enclosure, else the article page's og:image); items without one are skipped.
Standard library only. Never raises: on any failure the caller falls back to the last good list.
"""
import concurrent.futures as cf, datetime, email.utils, html, json, re, sys, time, urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 MirrorLilongBot/1.0 (+https://mirrorlilong.com)'
LIVE_JSON = 'https://mirrorlilong.com/trending.json'
TIERS = ['Manipur', 'Northeast', 'India', 'World']
QUOTA = {'Manipur': 5, 'Northeast': 3, 'India': 2, 'World': 2}
TOTAL = sum(QUOTA.values())

# (source name, feed url, default tier). Keywords in the headline/summary can move an item up a tier.
FEEDS = [
    ('Imphal Times', 'https://www.imphaltimes.com/feed/', 'Manipur'),
    ('Ukhrul Times', 'https://ukhrultimes.com/feed/', 'Northeast'),
    ('Kangla Online', 'https://kanglaonline.com/feed/', 'Manipur'),
    ('Impact TV', 'https://www.impactnews.in/feed', 'Manipur'),
    ('The Frontier Manipur', 'https://thefrontiermanipur.com/feed/', 'Manipur'),
    ('India Today NE', 'https://www.indiatodayne.in/rss/manipur', 'Northeast'),
    ('EastMojo', 'https://www.eastmojo.com/manipur/feed/', 'Northeast'),
    ('Northeast Now', 'https://nenow.in/north-east/manipur/feed', 'Northeast'),
    ('EastMojo', 'https://www.eastmojo.com/feed/', 'Northeast'),
    ('Northeast Now', 'https://nenow.in/feed', 'Northeast'),
    ('The Sentinel', 'https://www.sentinelassam.com/feed', 'Northeast'),
    ('Nagaland Post', 'https://nagalandpost.com/feed/', 'Northeast'),
    ('Hub Network', 'https://www.hubnetwork.in/feed/', 'Northeast'),
    ('The Hindu', 'https://www.thehindu.com/news/national/feeder/default.rss', 'India'),
    ('Indian Express', 'https://indianexpress.com/section/india/feed/', 'India'),
    ('NDTV', 'https://feeds.feedburner.com/ndtvnews-india-news', 'India'),
    ('BBC News', 'https://feeds.bbci.co.uk/news/world/rss.xml', 'World'),
    ('The Hindu', 'https://www.thehindu.com/news/international/feeder/default.rss', 'World'),
    ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml', 'World'),
    ('Hindustan Times', 'https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml', 'India'),
    # read only as signals: a story these editors also lead with ranks higher
    ('Times of India', 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms', None),
    ('NDTV', 'https://feeds.feedburner.com/ndtvnews-top-stories', None),
]
# feeds whose order is the editors' own order of importance
EDITORIAL = {'https://feeds.bbci.co.uk/news/world/rss.xml', 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
             'https://feeds.feedburner.com/ndtvnews-top-stories'}
ROUTINE = re.compile(r'\b(rupee|sensex|nifty|share price|stocks?|gold (?:price|rate)|silver (?:price|rate)|weather|rain alert|horoscope|lottery|petrol|diesel price|ipo|quarterly|q[1-4] (?:results|profit)|net profit|box office|wordle)\b', re.I)

MANIPUR_KW = ['manipur', 'manipuri', 'imphal', 'churachandpur', 'bishnupur', 'thoubal', 'ukhrul', 'kangpokpi', 'senapati', 'jiribam',
              'moreh', 'lilong', 'tamenglong', 'chandel', 'kakching', 'tengnoupal', 'noney', 'pherzawl', 'kamjong', 'moirang', 'meitei',
              'meetei', 'kuki-zo', 'kuki zo', 'pangal', 'loktak', 'biren singh', 'sanajaoba']
NE_KW = ['northeast', 'north east', 'north-east', 'arunachal', 'itanagar', 'tawang', 'assam', 'assamese', 'guwahati', 'dispur',
         'dibrugarh', 'jorhat', 'silchar', 'tezpur', 'kaziranga', 'bodoland', 'himanta', 'meghalaya', 'shillong', 'tura', 'mizoram',
         'aizawl', 'lunglei', 'nagaland', 'kohima', 'dimapur', 'tripura', 'agartala', 'sikkim', 'gangtok']
INDIA_KW = ['india', 'indian', 'delhi', 'modi', 'lok sabha', 'rajya sabha', 'supreme court', 'mumbai']
SKIP = re.compile(r'/(opinion|editorial|editorials|letters|op-ed|lifestyle|entertainment|horoscope|podcast|video|videos|photos?|gallery|web-stories|live-updates?)/|\b(horoscope|quiz|crossword|podcast|in pictures|live updates?|live:|watch:|news brief|top news|morning brief|evening brief|news wrap|highlights)\b', re.I)
BAD_IMG = re.compile(r'logo|default|placeholder|no[-_]?image|blank|favicon|cropped-.*icon|/icon|sprite|grey-placeholder|1x1|gravatar', re.I)
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

def log(msg): print('trending: ' + msg, file=sys.stderr)

def fetch(url, timeout=10, limit=3_000_000):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*', 'Accept-Language': 'en-IN,en;q=0.9'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit), r.geturl(), r.headers.get('Content-Type', '')

def strip_tags(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()

def kw_hit(text, words):
    return any(re.search(r'(?<![a-z])' + re.escape(w) + r'(?![a-z])', text) for w in words)

def classify(title, summary, default):
    t = (title + ' ' + summary[:300]).lower()
    tl = title.lower()
    local_feed = default in ('Manipur', 'Northeast')
    if kw_hit(tl, MANIPUR_KW) or (default == 'Manipur' and not kw_hit(tl, NE_KW)) or (local_feed and kw_hit(t, MANIPUR_KW[:3])):
        return 'Manipur'
    if kw_hit(tl, NE_KW) or local_feed:
        return 'Northeast'
    if default == 'World' and kw_hit(tl, INDIA_KW):
        return 'India'
    return default

def parse_dt(s):
    s = (s or '').strip()
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    return d

def local(tag): return tag.rsplit('}', 1)[-1].lower()

def find_img(el):
    """Image URL from media:content / media:thumbnail / enclosure / an <img> in the description."""
    best = None
    for c in el.iter():
        n = local(c.tag)
        if n in ('content', 'thumbnail') and c.get('url') and (c.get('medium') == 'image' or n == 'thumbnail' or re.search(r'\.(jpe?g|png|webp)', c.get('url'), re.I) or 'image' in (c.get('type') or '')):
            w = int(c.get('width') or 0)
            if best is None or w > best[1]:
                best = (c.get('url'), w)
        elif n == 'enclosure' and 'image' in (c.get('type') or '') and c.get('url'):
            best = best or (c.get('url'), 0)
    if best:
        return best[0], True
    for c in el:
        if local(c.tag) in ('description', 'encoded', 'content', 'summary') and c.text:
            m = re.search(r'<img[^>]+src=["\']([^"\']+)', c.text)
            if m:  # an <img> inside the text may be an ad or a logo: the page's og:image is tried first
                return html.unescape(m.group(1)), False
    return None, False

def parse_feed(data, source, default, editorial=False):
    data = re.sub(rb'^[^<]+', b'', data)
    root = ET.fromstring(data)
    out = []
    for el in root.iter():
        if local(el.tag) not in ('item', 'entry'):
            continue
        f = {}
        cats = []
        for c in el:
            n = local(c.tag)
            if n == 'link':
                href = c.get('href')
                if href and c.get('rel', 'alternate') == 'alternate':
                    f['link'] = href
                elif (c.text or '').strip():
                    f['link'] = c.text.strip()
            elif n == 'category':
                cats.append((c.text or c.get('term') or '').strip().lower())
            elif n in ('title', 'description', 'summary', 'pubdate', 'published', 'updated', 'date') and n not in f:
                f[n] = c.text or ''
        title = strip_tags(f.get('title', ''))
        link = (f.get('link') or '').strip()
        if not title or not link.startswith('http'):
            continue
        link = re.sub(r'[?&]utm_[^#]*$', '', link)
        summary = strip_tags(f.get('description') or f.get('summary') or '')
        summary = re.sub(r'The post .* appeared first on .*$', '', summary).strip()
        dt = parse_dt(f.get('pubdate') or f.get('published') or f.get('updated') or f.get('date'))
        if not dt or SKIP.search(link) or SKIP.search(title) or any(c in ('opinion', 'editorial', 'letters to editor', 'horoscope') for c in cats):
            continue
        img, media = find_img(el)
        if img:
            img = html.unescape(img.strip())
            img = re.sub(r'(ichef\.bbci\.co\.uk/(?:ace/standard|news))/\d+/', r'\1/800/', img)
        out.append(dict(title=title, url=link, source=source, dt=dt, img=img, summary=summary, media=media, pos=len(out), ed=editorial,
                        signal=default is None, cat=classify(title, summary, default or 'India')))
    return out

class OG(HTMLParser):
    def __init__(self):
        super().__init__(); self.img = None
    def handle_starttag(self, tag, attrs):
        if tag == 'meta' and not self.img:
            a = dict(attrs)
            if (a.get('property') or a.get('name') or '').lower() in ('og:image', 'og:image:url', 'og:image:secure_url', 'twitter:image') and a.get('content'):
                self.img = a['content'].strip()

def og_image(url):
    data, final, _ = fetch(url, timeout=8, limit=600_000)
    head = data.split(b'</head>', 1)[0].decode('utf-8', 'replace')
    p = OG(); p.feed(head)
    if p.img:
        return urllib.request.urljoin(final, html.unescape(p.img))
    return None

def stale_img(url, dt):
    """True when the image path is dated well before the article (a file photo from years ago)."""
    m = re.search(r'(?:/|%2f)(20[0-3]\d)(?:/|-|%2f)(0[1-9]|1[0-2])(?:/|-|%2f)', url, re.I)
    if not m:
        return False
    return (dt.year * 12 + dt.month) - (int(m.group(1)) * 12 + int(m.group(2))) > 2

def image_ok(url):
    if not url or not url.startswith('http') or BAD_IMG.search(url.split('?')[0].rstrip('/').rsplit('/', 1)[-1]):
        return False
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Range': 'bytes=0-2047', 'Referer': ''})
        with urllib.request.urlopen(req, timeout=8) as r:
            ct = r.headers.get('Content-Type', '')
            head = r.read(2048)
        return ct.startswith('image/') or head[:3] == b'\xff\xd8\xff' or head[:8] == b'\x89PNG\r\n\x1a\n' or head[8:12] == b'WEBP'
    except Exception:
        return False

WORD = re.compile(r'[a-z0-9]+')
STOP = set('a an the of in on at to for and or with by from as is are was were be after over amid into its it his her their says said new news latest'.split())
def stem(w):
    for suf in ('i', 'es', 's'):
        if w.endswith(suf) and len(w) > 4:
            return w[:-len(suf)]
    return w
def tokens(t): return {stem(w) for w in WORD.findall(t.lower().replace(',', '')) if w not in STOP and len(w) > 2}
def similar(a, b):
    if not a or not b: return False
    j = len(a & b) / float(len(a | b))
    return j >= 0.45 or (len(a & b) >= 4 and len(a & b) / float(min(len(a), len(b))) >= 0.55)

def collect(budget=55):
    t0 = time.time()
    items, ok = [], 0
    with cf.ThreadPoolExecutor(10) as ex:
        futs = {ex.submit(fetch, u, 10): (src, u, d) for src, u, d in FEEDS}
        try:
            for fu in cf.as_completed(futs, timeout=budget):
                src, u, d = futs[fu]
                try:
                    got = parse_feed(fu.result()[0], src, d, u in EDITORIAL); ok += 1; items += got
                except Exception as e:
                    log('feed failed %s (%s)' % (u, str(e)[:80]))
        except cf.TimeoutError:
            log('feed budget ran out after %ds' % (time.time() - t0))
    log('%d of %d feeds read, %d items' % (ok, len(FEEDS), len(items)))
    return items, ok

def pick(items, now):
    # de-duplicate across feeds (same link or similar headline); count coverage as a signal of importance
    items.sort(key=lambda x: x['dt'], reverse=True)
    groups = []
    for it in items:
        it['tok'] = tokens(it['title'])
        for g in groups:
            h = g[0]
            if h['url'] == it['url'] or similar(h['tok'], it['tok']):
                g.append(it); break
        else:
            groups.append([it])
    cands = []
    for g in groups:
        h = next((x for x in g if not x['signal']), None)
        if h is None:
            continue
        if not h['img']:
            o = next((x for x in g if x['img'] and x['source'] == h['source']), None)
            if o: h['img'], h['media'] = o['img'], o['media']
        # an item counts for the highest-priority tier any of its copies landed in
        h['cat'] = min((x['cat'] for x in g if not x['signal']), key=TIERS.index)
        h['ed_pos'] = min([x['pos'] for x in g if x['ed']] or [99])
        h['srcs'] = {x['source'] for x in g}
        age = (now - h['dt']).total_seconds() / 3600.0
        if -1 <= age <= 48:
            h['age'] = max(age, 0)
            cands.append(h)
    # coverage: how many other outlets carry a headline sharing several key words
    for h in cands:
        others = set(h['srcs'])
        for x in items:
            if x['source'] not in others and len(h['tok'] & x['tok']) >= 3:
                others.add(x['source'])
        h['cover'] = min(len(others), 4)
    def rank(x):  # fresher first; a story several outlets carry, or editors lead with, ranks higher; routine items lower
        r = x['age'] - 5 * (x['cover'] - 1) - max(0, 8 - x['ed_pos']) * 0.75
        if ROUTINE.search(x['title']):
            r += 8
        return r
    by = {t: sorted([c for c in cands if c['cat'] == t and (c['age'] <= 24 or t in ('Manipur', 'Northeast'))], key=rank) for t in TIERS}
    return by

GENERIC = {'manipur', 'assam', 'meghalaya', 'mizoram', 'nagaland', 'tripura', 'arunachal', 'india', 'indian', 'northeast',
           'govt', 'government', 'state', 'police', 'minister', 'chief', 'district', 'people', 'two', 'three', 'year', 'day'}
def same_story(a, b):
    return similar(a['tok'], b['tok']) or len((a['tok'] & b['tok']) - GENERIC) >= 2

def with_images(lst, need, seen_imgs, chosen=()):
    """Walk lst in order, keep items whose own image loads (and that are not the same story as one already
    chosen), until `need` are found."""
    out = []
    picked = list(chosen)
    lst = [x for x in lst if not any(same_story(x, c) for c in picked)]
    def resolve(it):
        img = it.get('img') if it.get('media') else None
        if not img or stale_img(img, it['dt']) or not image_ok(img):
            try:
                img = og_image(it['url'])
            except Exception:
                img = None
            if (not img or stale_img(img, it['dt']) or not image_ok(img)) and not it.get('media'):
                img = it.get('img')  # last resort: the picture inside the feed text
            if not img or stale_img(img, it['dt']) or not image_ok(img):
                return None
        return img
    i = 0
    with cf.ThreadPoolExecutor(6) as ex:
        while len(out) < need and i < len(lst):
            batch = lst[i:i + max(need - len(out) + 2, 3)]; i += len(batch)
            for it, img in zip(batch, ex.map(resolve, batch)):
                if img and img not in seen_imgs and len(out) < need and not any(same_story(it, c) for c in picked):
                    seen_imgs.add(img); it['img'] = img; out.append(it); picked.append(it)
    return out

def per_source_cap(lst, cap=2):
    n, out, rest = {}, [], []
    for x in lst:
        if n.get(x['source'], 0) < cap:
            n[x['source']] = n.get(x['source'], 0) + 1; out.append(x)
        else:
            rest.append(x)
    return out + rest

def build_list(now=None):
    now = now or datetime.datetime.now(datetime.timezone.utc)
    items, ok = collect()
    if ok == 0 or not items:
        return None
    by = pick(items, now)
    chosen, seen, carry = [], set(), 0
    for t in TIERS:
        need = QUOTA[t] + carry
        got = with_images(per_source_cap(by[t]), need, seen, chosen)
        chosen += got
        carry = need - len(got)
    if len(chosen) < TOTAL:  # top up from whatever is left, in priority order
        left = [x for t in TIERS for x in by[t] if x not in chosen]
        chosen += with_images(left, TOTAL - len(chosen), seen, chosen)
    chosen.sort(key=lambda x: (TIERS.index(x['cat']), -x['dt'].timestamp()) )
    # keep tier order but within a tier newest-first
    return [dict(title=x['title'], url=x['url'], source=x['source'], category=x['cat'], image=x['img'],
                 published=x['dt'].astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')) for x in chosen]

def previous():
    try:
        data, _, _ = fetch(LIVE_JSON, timeout=10)
        d = json.loads(data.decode('utf-8'))
        if isinstance(d, dict) and isinstance(d.get('items'), list):
            return d
    except Exception as e:
        log('no previous list (%s)' % str(e)[:80])
    return None

def get_trending():
    """Returns {'updated': iso, 'items': [...]} or None. Never raises."""
    now = datetime.datetime.now(datetime.timezone.utc)
    prev = None
    try:
        prev = previous()
    except Exception:
        pass
    fresh = None
    try:
        fresh = build_list(now)
    except Exception as e:
        log('build failed (%s)' % e)
    if fresh and len(fresh) >= 6:
        if prev and len(fresh) < TOTAL:  # top up from the last good list
            have = {x['url'] for x in fresh}
            for x in prev['items']:
                if len(fresh) >= TOTAL: break
                if x.get('url') not in have: fresh.append(x)
            fresh.sort(key=lambda x: TIERS.index(x['category']) if x.get('category') in TIERS else 9)
        return {'updated': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'items': fresh}
    if prev and prev.get('items'):
        log('using the last good list from the live site')
        return prev
    if fresh:
        return {'updated': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'items': fresh}
    return None

if __name__ == '__main__':
    d = get_trending()
    for x in (d or {}).get('items', []):
        print(x['category'], '|', x['source'], '|', x['published'], '|', x['title'][:80], '|', x['image'][:70])
