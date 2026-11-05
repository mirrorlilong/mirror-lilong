#!/usr/bin/env python3
"""Mirror Lilong: translate NEW stories with Google Gemini, inside GitHub Actions (plain Python 3, no packages).

Runs in .github/workflows/pages.yml BEFORE build.py. For each story in content/stories/*.json that is not
hidden and has no translations/<slug>.json yet (newest first, at most MAX_PER_RUN per run), it asks Gemini
for Manipuri (casual English letters, Meitei Mayek, Bengali script) and Hindi, checks the answer, and writes
translations/<slug>.json in the shape translate_inject.py reads. The workflow then commits the new files.

Safe by design: no GEMINI_API_KEY secret, a Gemini error, a quota limit or a bad answer only logs a warning
and skips that story; the site still builds and publishes exactly as before. Existing translation files are
never touched, and content/ is only read.

Settings (environment): GEMINI_API_KEY (repo secret, required), GEMINI_MODEL (default gemini-flash-latest),
GEMINI_MAX_PER_RUN (default 3), GEMINI_TIMEOUT (seconds per call, default 180).
"""
import datetime, json, os, re, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
STORIES = os.path.join(ROOT, 'content', 'stories')
TR = os.path.join(ROOT, 'translations')
API = os.environ.get('GEMINI_ENDPOINT') or 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
# 'gemini-flash-latest' always points at Google's current Flash model (older names like gemini-2.5-flash are
# closed to new keys). The free tier allows about 20 Flash requests a day; Flash-Lite has a much bigger allowance
# and is the fallback when Flash is over its limit.
MODELS = []
for m in [os.environ.get('GEMINI_MODEL', '').strip(), 'gemini-flash-latest', 'gemini-3.8-flash', 'gemini-flash-lite-latest']:
    if m and m not in MODELS: MODELS.append(m)
MAX_PER_RUN = int(os.environ.get('GEMINI_MAX_PER_RUN') or 3)
TIMEOUT = int(os.environ.get('GEMINI_TIMEOUT') or 180)
LANGS = [('mni_latn', 'mni-Latn'), ('mni_mtei', 'mni-Mtei'), ('mni_beng', 'mni-Beng'), ('hi', 'hi')]


def log(msg): print('gemini-translate: ' + msg, flush=True)
def warn(msg): print('::warning::gemini-translate: ' + msg, flush=True)  # yellow note in the Actions log


class Quota(Exception): pass      # 429 / quota: stop this run, next run tries again
class NoModel(Exception): pass    # 404: try the next model
class BadKey(Exception): pass     # key wrong/blocked: stop this run


# ---- the same paragraph rules as build.py / translate_inject.py ----
MEDIA_RE = re.compile(r'^(\[\s*photo\s*\d+\s*\]|!\[[^\]\n]*\]\([^)\n]+\))$', re.I)
def paras(t): return [p.strip() for p in (t or '').split('\n\n') if p.strip()]
def cap_paras(t): return [p.strip() for p in re.split(r'\n\s*\n|\n|\s{2,}', t or '') if p.strip()]

# Spellings already used on the site, so names stay the same in every story.
GLOSSARY = """English | Manipuri (English letters) | Meitei Mayek | Bengali script | Hindi
Manipur | Manipur | ꯃꯅꯤꯄꯨꯔ | মণিপুর | मणिपुर
Imphal | Imphal | ꯏꯝꯐꯥꯜ | ইম্ফাল | इंफाल
COCOMI | COCOMI | ꯀꯣꯀꯣꯃꯤ | কোকোমি | कोकोमी
Kangpokpi | Kangpokpi | ꯀꯥꯡꯄꯣꯛꯄꯤ | কাংপোকপি | कांगपोकपी
Kuki-Zo | Kuki-Zo | ꯀꯨꯀꯤ-ꯖꯣ | কুকি-জো | कुकी-जो
Meitei | Meitei | ꯃꯤꯇꯩ | মীতৈ | मैतेई
Naga | Naga | ꯅꯥꯒꯥ | নাগা | नगा
Churachandpur | Churachandpur | ꯆꯨꯔꯥꯆꯥꯟꯗꯄꯨꯔ | চূরাচান্দপুর | चुराचांदपुर
Thoubal | Thoubal | ꯊꯧꯕꯥꯜ | থৌবাল | थौबल
MLA | MLA | ꯑꯦꯝ.ꯑꯦꯜ.ꯑꯦ. | এম.এল.এ. | विधायक
Chief Minister / CM | CM | ꯃꯨꯈ꯭ꯌ ꯃꯟꯇ꯭ꯔꯤ | মুখ্য মন্ত্রী | मुख्यमंत्री
Deputy Chief Minister | Deputy CM | ꯗꯦꯄꯨꯇꯤ ꯃꯨꯈ꯭ꯌ ꯃꯟꯇ꯭ꯔꯤ | ডেপুটি মুখ্য মন্ত্রী | उपमुख्यमंत्री
CoTU | CoTU | ꯁꯤ.ꯑꯣ.ꯇꯤ.ꯌꯨ. | সী.ও.টী.য়ু. | सीओटीयू
police | police | ꯄꯨꯂꯤꯁ | পুলিশ | पुलिस
government | sarkar | ꯁꯔꯀꯥꯔ | সরকার | सरकार
India | India | ꯏꯟꯗꯤꯌꯥ | ইন্ডিয়া | भारत
Assam Rifles | Assam Rifles | ꯑꯥꯁꯥꯝ ꯔꯥꯏꯐꯜꯁ | আসাম রাইফলস | असम राइफल्स
district | district | ꯗꯤꯁ꯭ꯇ꯭ꯔꯤꯀ꯭ꯠ | ডিস্ট্রিক্ট | जिला"""

RULES = """You are the translation desk of Mirror Lilong, a news website from Manipur, India.
Translate the English news story in the input JSON into four versions, as a news reporter would write them:
- mni_latn: Manipuri (Meiteilon) written casually in English letters, the way people in Manipur type it on Facebook
  and WhatsApp (e.g. "Magi sel-thumgi khongchat adu ningsinduna ..."). Names, places and common English words
  (police, government office names, app names) stay in normal English spelling. ASCII letters only.
- mni_mtei: the same Manipuri text in Meitei Mayek script ONLY (Unicode block U+ABC0 to U+ABFF). Use the Meitei
  Mayek full stop ꯫ at the end of sentences and Meitei Mayek digits ꯰ ꯱ ꯲ ꯳ ꯴ ꯵ ꯶ ꯷ ꯸ ꯹. Names and abbreviations are
  written in Meitei Mayek too. NO Latin, Bengali or other letters at all. Commas, hyphens, quotes and brackets are fine.
- mni_beng: the same Manipuri text in Bengali script (as Manipuri newspapers print it), sentence end ।
  Names and abbreviations in Bengali script. NO Latin letters. Bengali or ASCII digits are fine.
- hi: Hindi in Devanagari, natural Hindi news style (like Dainik Jagran / Amar Ujala). Abbreviations and names in
  Devanagari (e.g. "CM" -> मुख्यमंत्री). NO Latin letters at all; digits are fine. Sentence end ।
Every version must be complete: title, summary, every body paragraph and every caption paragraph.
STRUCTURE RULES (they are checked by a program):
- body: exactly the same number of paragraphs as the English "body" list, same order, one translated paragraph per
  English paragraph. Never merge or split paragraphs. A paragraph like [photo1] is copied exactly as it is.
- A paragraph wrapped in **double asterisks** (a bold heading) keeps the ** around its translation.
- captions: one entry per English caption, same order; each entry has exactly as many paragraphs as the English one
  (an empty English caption gives an empty list).
- Keep numbers, dates and amounts correct (write "Rs" amounts as e.g. "Rs 5 lakh" -> Hindi "5 लाख रुपये").
- Do not add or drop facts. Do not add notes.
Use these spellings already used on the site:
""" + GLOSSARY


def schema():
    s = {'type': 'ARRAY', 'items': {'type': 'STRING'}}
    one = {'type': 'OBJECT', 'properties': {'title': {'type': 'STRING'}, 'summary': {'type': 'STRING'}, 'body': s,
           'captions': {'type': 'ARRAY', 'items': s}}, 'required': ['title', 'summary', 'body', 'captions']}
    return {'type': 'OBJECT', 'properties': {k: one for k, _ in LANGS}, 'required': [k for k, _ in LANGS]}


THINKING = {}
VERSION = {}


class Busy(Exception):
    pass


def call_gemini(model, key, prompt, _try=0):
    cfg = {'temperature': 0.2, 'responseMimeType': 'application/json', 'responseSchema': schema(), 'maxOutputTokens': 65536}
    if model.startswith('gemini-2.5'):
        cfg['thinkingConfig'] = {'thinkingBudget': 0}
    elif THINKING.get(model, True):
        cfg['thinkingConfig'] = {'thinkingLevel': os.environ.get('GEMINI_THINKING') or 'low'}
    body = json.dumps({'contents': [{'role': 'user', 'parts': [{'text': prompt}]}], 'generationConfig': cfg}).encode()
    req = urllib.request.Request(API.format(model=model), data=body, method='POST',
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': key,
                                          'User-Agent': 'mirrorlilong-translate/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        msg = e.read().decode('utf-8', 'replace')[:300]
        if e.code == 400 and 'thinking' in msg.lower() and 'thinkingConfig' in cfg and THINKING.get(model, True):
            THINKING[model] = False  # this model has no thinking setting: ask again without it
            return call_gemini(model, key, prompt)
        if e.code == 404: raise NoModel('%s: %s' % (model, msg))
        if e.code == 429: raise Quota(msg)
        if e.code in (500, 502, 503, 504):
            if _try < 3:  # Google busy: wait and ask the same model again
                time.sleep((10, 25, 45)[_try])
                return call_gemini(model, key, prompt, _try + 1)
            raise Busy('%s busy (HTTP %s)' % (model, e.code))
        if e.code in (401, 403) or 'API_KEY' in msg: raise BadKey('HTTP %s: %s' % (e.code, msg))
        raise RuntimeError('HTTP %s from Gemini: %s' % (e.code, msg))
    VERSION[model] = data.get('modelVersion') or model
    cands = data.get('candidates') or []
    if not cands: raise RuntimeError('no answer (%s)' % json.dumps(data.get('promptFeedback', data))[:200])
    c = cands[0]
    text = ''.join(p.get('text', '') for p in (c.get('content') or {}).get('parts', []) if not p.get('thought'))
    if c.get('finishReason') not in (None, 'STOP'): raise RuntimeError('answer cut off (%s)' % c.get('finishReason'))
    text = text.strip()
    if text.startswith('```'): text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
    return json.loads(text)


# ---- checks ----
OK_PUNCT = set(' \u00a0.,:;!?\'"()[]{}-/%&+*#@|\u2018\u2019\u201c\u201d\u2013\u2014\u2026')
def bad_chars(lang, s):
    bad = set()
    for ch in s:
        o = ord(ch)
        if ch in OK_PUNCT or ch.isdigit() and o < 128 or ch in '\n': continue
        if lang == 'mni-Mtei' and 0xABC0 <= o <= 0xABFF: continue
        if lang == 'mni-Beng' and 0x0980 <= o <= 0x09FF: continue
        if lang == 'hi' and (0x0900 <= o <= 0x097F or o in (0x200c, 0x200d)): continue
        if lang == 'mni-Latn' and o < 128: continue
        if lang in ('mni-Beng', 'hi') and ch == '\u0964': continue
        bad.add(ch)
    return bad


def build_file(story, ans, model):
    en_body = paras(story.get('body', ''))
    en_caps = [(p.get('caption') or '').strip() if isinstance(p, dict) else '' for p in (story.get('photos') or [])]
    out = {'en': {'title': story['title'], 'summary': story.get('summary', ''), 'body': story['body']}}
    errs = []
    for key, lang in LANGS:
        x = ans.get(key) if isinstance(ans, dict) else None
        if not isinstance(x, dict): errs.append('%s missing' % lang); continue
        title, summ = (x.get('title') or '').strip(), (x.get('summary') or '').strip()
        body = [str(p).strip() for p in (x.get('body') or []) if str(p).strip()]
        if not title: errs.append('%s title empty' % lang)
        if story.get('summary') and not summ: errs.append('%s summary empty' % lang)
        if len(body) != len(en_body): errs.append('%s body has %d paragraphs, English has %d' % (lang, len(body), len(en_body))); continue
        body = [en_body[i] if MEDIA_RE.match(en_body[i]) else re.sub(r'\s*\n\s*', ' ', p) for i, p in enumerate(body)]
        rec = {'title': title, 'summary': summ, 'body': '\n\n'.join(body)}
        text = ' '.join([title, summ] + [p for i, p in enumerate(body) if not MEDIA_RE.match(en_body[i])])
        if any(c.strip() for c in en_caps):
            caps_in = x.get('captions') or []
            caps = []
            for i, ec in enumerate(en_caps):
                n = len(cap_paras(ec))
                got = [str(p).strip() for p in (caps_in[i] if i < len(caps_in) and isinstance(caps_in[i], list) else []) if str(p).strip()]
                got = [re.sub(r'\s*\n\s*', ' ', re.sub(r' {2,}', ' ', p)) for p in got]
                if n and len(got) != n: errs.append('%s caption %d has %d paragraphs, English has %d' % (lang, i + 1, len(got), n))
                caps.append('\n\n'.join(got) if n else '')
                text += ' ' + ' '.join(got)
            rec['captions'] = caps
        b = bad_chars(lang, text)
        if b: errs.append('%s has wrong characters: %s' % (lang, ''.join(sorted(b))[:40]))
        if lang == 'mni-Mtei' and len(re.findall('[\uabc0-\uabff]', text)) < 20: errs.append('mni-Mtei has almost no Meitei Mayek')
        out[lang] = rec
    out['_meta'] = {'engine': 'gemini', 'model': VERSION.get(model, model), 'source_lang': 'en',
                    'generated': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
                    'method': 'Translated automatically by Google Gemini in GitHub Actions (translate_gemini.py), checked for paragraph counts and scripts',
                    'hi': 'Hindi: Google Gemini'}
    return out, errs


def prompt_for(story, errors=None):
    inp = {'title': story['title'], 'summary': story.get('summary', ''), 'body': paras(story.get('body', '')),
           'captions': [cap_paras(p.get('caption') or '') if isinstance(p, dict) else [] for p in (story.get('photos') or [])]}
    p = RULES + '\n\nINPUT JSON:\n' + json.dumps(inp, ensure_ascii=False, indent=1)
    p += '\n\nThe English body has %d paragraphs, so every "body" list must have exactly %d items.' % (len(inp['body']), len(inp['body']))
    if errors: p += '\n\nYour previous answer was rejected for these problems, fix them: ' + '; '.join(errors)
    return p


def translate(slug, story, key):
    errors = None
    for attempt in (1, 2):
        last = None
        for model in list(MODELS):
            try:
                t0 = time.time()
                ans = call_gemini(model, key, prompt_for(story, errors))
                log('%s: answer from %s in %.0f s' % (slug, model, time.time() - t0))
                break
            except NoModel as e:
                log('model not available, trying the next one (%s)' % e); MODELS.remove(model); last = e; continue
            except Busy as e:
                log('%s; trying the next model' % e); last = e; continue
            except Quota as e:
                if model != MODELS[-1]:
                    log('%s quota reached, trying the next model' % model); last = e; continue
                raise
        else:
            raise RuntimeError('no model answered (%s)' % last)
        out, errors = build_file(story, ans, model)
        if not errors: return out
        log('%s: attempt %d rejected: %s' % (slug, attempt, '; '.join(errors)))
    raise RuntimeError('answer failed the checks twice: ' + '; '.join(errors))


def missing_stories():
    have = set(f[:-5] for f in os.listdir(TR) if f.endswith('.json')) if os.path.isdir(TR) else set()
    todo = []
    for fn in os.listdir(STORIES):
        if not fn.endswith('.json'): continue
        slug = fn[:-5]
        if slug in have: continue
        try:
            s = json.load(open(os.path.join(STORIES, fn), encoding='utf-8'))
        except Exception as e:
            log('cannot read %s (%s)' % (fn, e)); continue
        if not isinstance(s, dict) or s.get('hidden') or not s.get('title') or not s.get('body'): continue
        todo.append((str(s.get('date') or ''), slug, s))
    todo.sort(reverse=True)
    return todo


def main():
    todo = missing_stories()
    if not todo:
        log('every story already has a translation'); return
    key = (os.environ.get('GEMINI_API_KEY') or '').strip()
    if not key:
        warn('%d new stor%s without translation, but the GEMINI_API_KEY secret is not set; skipping (site publishes in English only for those)' % (len(todo), 'y' if len(todo) == 1 else 'ies'))
        return
    os.makedirs(TR, exist_ok=True)
    done = 0
    for _, slug, story in todo[:MAX_PER_RUN]:
        try:
            out = translate(slug, story, key)
        except Quota as e:
            warn('Gemini quota/rate limit reached, stopping for this run (%s)' % str(e)[:200]); break
        except BadKey as e:
            warn('the GEMINI_API_KEY secret was refused by Google, check it (%s)' % str(e)[:200]); break
        except Exception as e:
            warn('%s skipped: %s' % (slug, str(e)[:300])); continue
        path = os.path.join(TR, slug + '.json')
        if os.path.exists(path): continue  # never overwrite
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2); f.write('\n')
        json.load(open(path, encoding='utf-8'))
        done += 1
        log('wrote translations/%s.json' % slug)
    left = len(todo) - done
    log('translated %d stor%s%s' % (done, 'y' if done == 1 else 'ies', ', %d still waiting' % left if left else ''))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:  # never break the site build
        warn('step failed, site builds without new translations (%s)' % e)
    sys.exit(0)
