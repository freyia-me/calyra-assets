# Генератор T123-блоков для Tilda из зеркала revolution.bio (Joomla/K2).
# usage: python3 -I gen.py <mirror/revolution.bio> <out dir> <cdn base url>
import sys, os, re, json, hashlib, html, posixpath
from urllib.parse import unquote, urlsplit
from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from PIL import Image

SRC, OUT, CDN = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/')
IMG_DIR = os.path.join(OUT, 'img')
os.makedirs(IMG_DIR, exist_ok=True)
for d in ('tilda', 'tilda-txt'):
    os.makedirs(os.path.join(OUT, d), exist_ok=True)

# ---------------------------------------------------------------- карта страниц
# старый файл зеркала -> (новый адрес в Tilda, тип)
PAGES = {
    'index.html': ('/', 'home'),
    'about.html': ('/about', 'about'),
    'product.html': ('/product', 'catalog'),
    'product/itemlist/category/7-jeuderm.html': ('/jeuderm', 'category'),
    'product/itemlist/category/9-biorevitalizatsiya.html': ('/biorevitalizatsiya', 'category'),
    'product/itemlist/category/5-ekzosomy.html': ('/ekzosomy', 'category'),
    'product/itemlist/category/19-trikhologiya.html': ('/trikhologiya', 'category'),
    'product/itemlist/category/11-pro-skincare.html': ('/kosmecevtika', 'category'),
    'product/item/227-rejusome.html': ('/rejusome', 'product'),
    'product/item/228-rejusome-plus.html': ('/rejusome-plus', 'product'),
    'product/item/229-rejusome-plus-hair.html': ('/rejusome-plus-hair', 'product'),
    'product/item/207-rejusomeboostcream.html': ('/rejusome-exo-boost-cream', 'product'),
    'product/item/230-rejusomeboostserum.html': ('/rejusome-exo-boost-serum', 'product'),
    'product/item/231-rejusomeboostmask.html': ('/rejusome-exo-boost-mask', 'product'),
    'product/item/237-rejusomeboostmist.html': ('/rejusome-exo-boost-mist', 'product'),
    'product/item/59-crystal-pdrn.html': ('/crystal-pdrn', 'product'),
    'product/item/81-jeuderm-homecare.html': ('/jeuderm-homecare', 'product'),
    'product/item/82-jeuderm-pofessional.html': ('/jeuderm-professional', 'product'),
    'product/itemlist/category/93-otzyvy-tovarov.html': ('/otzyvy', 'reviews'),
    'uchebnyj-tsentr.html': ('/uchebnyj-tsentr', 'school'),
    'uchebnyj-tsentr/item/219-study-cosmetology.html': ('/obuchenie-kosmetologov', 'article'),
    'uchebnyj-tsentr/item/210-rejusome-trip-dubrovnik-exosomes-summit.html': ('/exosomes-summit-dubrovnik', 'article'),
    'uchebnyj-tsentr/itemlist/category/18-teachers.html': ('/prepodavateli', 'teachers'),
    'sales.html': ('/akcii', 'sales'),
    'news.html': ('/news', 'news'),
    'news/item/19-news1.html': ('/news-mint-lift', 'article'),
    'news/item/20-news2.html': ('/news-webinar-mint-lift', 'article'),
    'news/item/21-news3.html': ('/news-ekzosomy', 'article'),
    'partners.html': ('/partners', 'partners'),
    'kontakty.html': ('/kontakty', 'contacts'),
    'policy.html': ('/policy', 'article'),
    'soglasie.html': ('/soglasie', 'article'),
}
# старые адреса, которые сливаются в другие страницы (для редиректов и ссылок)
EXTRA = {
    'product/itemlist/category/4-otzyvy.html': '/otzyvy',
    'partners/itemlist/category/93-otzyvy-tovarov.html': '/otzyvy',
    'partners/itemlist/category/16-moscow.html': '/partners',
    'partners/itemlist/category/95-russia.html': '/partners',
    'partners/itemlist/category/98-gruzia.html': '/partners',
    'partners/item/193-mintlift-buy-russia.html': '/partners',
    'partners/item/202-revolution-group.html': '/partners',
    'sales/item/15-sale1.html': '/akcii',
    'sales/item/16-sale2.html': '/akcii',
    'product/item/9-nauchnyj-tsentr-revolution-group.html': '/about',
}
# заполняется при сборке отзывов/преподавателей: старый файл -> адрес с якорем
ANCHORS = {}

# страница со статьёй стороннего автора: переносим только вступление
INTRO_ONLY = {'news/item/21-news3.html'}

NAV = [('О компании', '/about'), ('Продукция', '/product'), ('Учебный центр', '/uchebnyj-tsentr'),
       ('Отзывы', '/otzyvy'), ('Новости', '/news'), ('Контакты', '/kontakty')]
PHONE, PHONE_HREF = '+7 (495) 147-70-40', 'tel:+74951477040'
EMAIL = 'info@revolution.bio'

def soup(rel):
    s = BeautifulSoup(open(os.path.join(SRC, rel), encoding='utf-8'), 'lxml')
    for c in s.find_all(string=lambda x: isinstance(x, Comment)):
        c.extract()
    for t in s(['script', 'style', 'noscript', 'iframe' if False else 'noscript']):
        t.decompose()
    return s

def norm_rel(page_rel, href):
    """относительная ссылка из страницы зеркала -> путь в зеркале"""
    href = unquote(href.split('#')[0].split('?')[0])
    if not href:
        return None
    if href.startswith('https://revolution.bio') or href.startswith('http://revolution.bio'):
        p = urlsplit(href).path.lstrip('/')
        return (p + '.html') if p and not p.endswith('.html') else (p or 'index.html')
    if href.startswith('/'):
        p = href.lstrip('/')
        return (p + '.html') if p and not p.endswith('.html') else (p or 'index.html')
    return posixpath.normpath(posixpath.join(posixpath.dirname(page_rel), href))

def map_link(page_rel, href):
    if not href:
        return None
    h = href.strip()
    if h.startswith(('mailto:', 'tel:')):
        return h
    if re.match(r'https?://', h) and 'revolution.bio' not in urlsplit(h).netloc:
        return h
    if h.startswith('#') or h.endswith('.html#') or h == '':
        return None
    p = norm_rel(page_rel, h)
    if p is None:
        return None
    if p in ANCHORS:
        return ANCHORS[p]
    if p in PAGES:
        return PAGES[p][0]
    if p in EXTRA:
        return EXTRA[p]
    if '/itemlist/tag/' in p or '/itemlist/user/' in p:
        return '/product' if p.startswith('product') else '/partners'
    if p.startswith('component/k2/item/'):
        return '/otzyvy'
    if re.search(r'\.(jpe?g|png|gif|webp|pdf)$', p, re.I):
        return img(page_rel, h)
    return None

# ---------------------------------------------------------------- картинки
IMAGES = {}
def img(page_rel, src, max_w=1600):
    if not src:
        return None
    src = src.strip().strip('\'"')
    if src.startswith('http') and 'revolution.bio' not in src:
        return None  # граватары и прочие внешние — не нужны
    p = norm_rel(page_rel, src)
    path = os.path.join(SRC, p)
    if not os.path.isfile(path):
        # кэш K2: если нет XL, пробуем L/M
        for a, b in (('_XL.', '_L.'), ('_L.', '_M.')):
            if a in path and os.path.isfile(path.replace(a, b)):
                path = path.replace(a, b); break
        else:
            return None
    if path in IMAGES:
        return IMAGES[path]
    base = re.sub(r'[^a-z0-9]+', '-', os.path.splitext(os.path.basename(path))[0].lower()).strip('-')[:40] or 'img'
    h = hashlib.md5(open(path, 'rb').read()).hexdigest()[:6]
    ext = os.path.splitext(path)[1].lower()
    if ext == '.svg' or ext == '.gif':
        name = f'{base}-{h}{ext}'
        with open(path, 'rb') as f, open(os.path.join(IMG_DIR, name), 'wb') as o:
            o.write(f.read())
    else:
        im = Image.open(path)
        im.load()
        if im.mode in ('P', 'LA'):
            im = im.convert('RGBA')
        elif im.mode not in ('RGB', 'RGBA'):
            im = im.convert('RGB')
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        name = f'{base}-{h}.webp'
        im.save(os.path.join(IMG_DIR, name), 'WEBP', quality=84, method=6)
    url = f'{CDN}/img/{name}'
    IMAGES[path] = url
    return url

def bg_url(page_rel, el):
    m = re.search(r"url\(['\"]?([^'\")]+)", (el.get('style') or '') if el else '')
    return img(page_rel, m.group(1)) if m else None

def full_size(u):
    return u.replace('_M.jpg', '_XL.jpg').replace('_L.jpg', '_XL.jpg') if u else u

# ---------------------------------------------------------------- чистка текста
INLINE = {'strong', 'b', 'em', 'i', 'a', 'br', 'u', 'sup', 'sub', 'img'}
KEEP = INLINE | {'p', 'ul', 'ol', 'li', 'h2', 'h3', 'h4', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'hr'}
CLOAK = re.compile(r'Этот адрес электронной почты защищен от спам-ботов\.\s*Для просмотра адреса в вашем браузере должен быть включен Javascript\.?')

def clean(page_rel, el):
    """K2-разметку -> простой семантический HTML"""
    if el is None:
        return ''
    el = BeautifulSoup(str(el), 'lxml')
    root = el.body or el
    for t in root.select('script,style,form,input,select,button,.clr,.itemBackToTop,.k2FeedIcon,[style*="display: none"],[style*="display:none"]'):
        t.decompose()
    for t in list(root.find_all(True)):
        if t.parent is None:
            continue
        name = t.name
        if name == 'h1':
            t.name = 'h2'
        elif name in ('h5', 'h6'):
            t.name = 'h4'
        elif name == 'b':
            t.name = 'strong'
        elif name == 'i':
            t.name = 'em'
        if t.name == 'img':
            u = img(page_rel, t.get('src'))
            if not u or 'quote.png' in (t.get('src') or ''):
                t.decompose(); continue
            t.attrs = {'src': u, 'alt': t.get('alt', '') or '', 'loading': 'lazy'}
            continue
        if t.name == 'a':
            u = map_link(page_rel, t.get('href'))
            if not u:
                t.unwrap(); continue
            t.attrs = {'href': u}
            if u.startswith('http') and not u.startswith(CDN):
                t.attrs.update(target='_blank', rel='noopener')
            continue
        if t.name in KEEP:
            t.attrs = {}
            continue
        if t.name == 'div':
            if t.find(['p', 'ul', 'ol', 'div', 'h2', 'h3', 'h4', 'table', 'blockquote']):
                t.unwrap()
            else:
                t.name = 'p'; t.attrs = {}
            continue
        t.unwrap()  # span, font и прочее
    out = root.decode_contents()
    out = CLOAK.sub(f'<a href="mailto:{EMAIL}">{EMAIL}</a>', out)
    out = out.replace('\xa0', ' ')
    out = re.sub(r'\s+', ' ', out)
    out = re.sub(r'<p>(\s|<br/?>)*</p>', '', out)
    out = re.sub(r'(<br/?>\s*){3,}', '<br/><br/>', out)
    out = re.sub(r'<p>(\s|<br/?>)+', '<p>', out)
    out = re.sub(r'(\s|<br/?>)+</p>', '</p>', out)
    out = re.sub(r'\s*(</?(p|ul|ol|li|h2|h3|h4|table|tr|td|th|blockquote|hr)>)\s*', r'\1', out)
    out = re.sub(r'(<(p|ul|ol|h2|h3|h4|table|blockquote|hr)\b)', r'\n\1', out).strip()
    return out

def text(el):
    return ' '.join(el.get_text(' ', strip=True).split()) if el else ''

def esc(s):
    return html.escape(s or '', quote=True)

def strip_tags(s):
    return ' '.join(re.sub(r'<[^>]+>', ' ', s or '').split())

def shorten(s, n=170):
    s = strip_tags(s)
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0].rstrip('.,;:—-') + '…'

def title_of(s):
    t = s.title.string if s.title else ''
    return (t or '').strip()

def meta(s, name):
    m = s.find('meta', attrs={'name': name})
    return (m.get('content') or '').strip() if m else ''

# ---------------------------------------------------------------- извлечение K2
def k2_item(page_rel, s):
    v = s.select_one('.itemView')
    d = {}
    d['title'] = text(v.select_one('.itemTitle')) if v and v.select_one('.itemTitle') else ''
    if not d['title']:
        d['title'] = title_of(s)
    im = v.select_one('.itemImage img') if v else None
    a = v.select_one('.itemImage a') if v else None
    d['image'] = img(page_rel, a.get('href')) if a and a.get('href') else (img(page_rel, im.get('src')) if im else None)
    d['intro'] = clean(page_rel, v.select_one('.itemIntroText')) if v else ''
    d['full'] = clean(page_rel, v.select_one('.itemFullText')) if v else ''
    fields = []
    for li in (v.select('.itemExtraFields li') if v else []):
        lab = text(li.select_one('.itemExtraFieldsLabel')).rstrip(':')
        val = clean(page_rel, li.select_one('.itemExtraFieldsValue'))
        if lab and strip_tags(val):
            fields.append((lab, val))
    d['fields'] = fields
    d['date'] = text(v.select_one('.itemDateCreated')) if v else ''
    gal = []
    for ga in (v.select('.itemImageGallery a[href], .sigProLink[href]') if v else []):
        u = img(page_rel, ga['href'])
        if u and u not in gal:
            gal.append(u)
    d['gallery'] = gal
    return d

def cat_items(page_rel, s):
    items = []
    for v in s.select('.catItemView'):
        a = v.select_one('.catItemTitle a')
        it = {
            'title': text(v.select_one('.catItemTitle')),
            'href_rel': norm_rel(page_rel, a['href']) if a and a.get('href') else None,
            'intro': clean(page_rel, v.select_one('.catItemIntroText')),
            'date': text(v.select_one('.catItemDateCreated')),
        }
        ia = v.select_one('.catItemImage a[href$=".jpg"], .catItemImage a[href$=".png"]')
        im = v.select_one('.catItemImage img')
        it['image'] = img(page_rel, ia['href']) if ia else (img(page_rel, im['src']) if im else None)
        it['fields'] = [(text(li.select_one('.catItemExtraFieldsLabel')).rstrip(':'),
                         clean(page_rel, li.select_one('.catItemExtraFieldsValue')))
                        for li in v.select('.catItemExtraFields li')]
        items.append(it)
    return items

def cat_description(page_rel, s):
    el = s.select_one('.itemListCategory') or s.select_one('.products-subcategory-description')
    return clean(page_rel, el)

# ---------------------------------------------------------------- вёрстка
FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600&family=PT+Serif:wght@400;700&display=swap" rel="stylesheet">'

def css():
    deco = img('index.html', 'images/custom/inner_bg.png', 1600)
    return """<style>
#rb{--bg:#2b3035;--bg-2:#33393e;--glass:rgba(255,255,255,.055);--glass-2:rgba(255,255,255,.09);--line:rgba(255,255,255,.12);--ink:#fff;--muted:rgba(255,255,255,.7);
  --accent:#36cbe0;--accent-ink:#0d262b;--glow:rgba(54,203,224,.35);--r:18px;--r-sm:12px;
  --serif:'PT Serif',Georgia,'Times New Roman',serif;--sans:'Manrope','Helvetica Neue',Arial,sans-serif;
  font-family:var(--sans);font-weight:300;color:var(--ink);font-size:17px;line-height:1.65;-webkit-font-smoothing:antialiased;
  background:radial-gradient(1200px 600px at 85% -10%,rgba(54,203,224,.10),transparent 60%),radial-gradient(900px 500px at -10% 40%,rgba(255,255,255,.04),transparent 60%),var(--bg);
  overflow-x:hidden;overflow-x:clip;position:relative}
#rb *,#rb *::before,#rb *::after{box-sizing:border-box}
#rb img{max-width:100%;height:auto;display:block}
#rb a{color:inherit}
#rb p{margin:0 0 1em}
#rb ::selection{background:var(--accent);color:var(--accent-ink)}
#rb .rb-wrap{max-width:1200px;margin:0 auto;padding:0 24px}
#rb h1,#rb h2,#rb h3{font-family:var(--serif);font-weight:400;line-height:1.12;margin:0 0 .55em;color:#fff;text-wrap:balance}
#rb h1{font-size:clamp(28px,6.4vw,76px);text-transform:uppercase;letter-spacing:.005em}
#rb h2{font-size:clamp(30px,3.6vw,48px);letter-spacing:-.01em}
#rb h3{font-size:22px}
#rb .rb-rule{width:96px;height:2px;background:#fff;border:0;margin:0 0 36px;opacity:.9}
#rb .rb-kicker{display:inline-flex;align-items:center;gap:12px;font-size:12px;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);margin-bottom:16px}
#rb .rb-kicker::before{content:"";width:28px;height:1px;background:currentColor}
#rb .rb-muted{color:var(--muted)}
#rb .rb-btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;padding:14px 30px;border:1.5px solid var(--accent);border-radius:999px;color:#fff;text-decoration:none;font-family:var(--serif);font-size:16px;line-height:1.2;transition:background .25s,color .25s,box-shadow .25s,transform .25s;cursor:pointer;background:transparent}
#rb .rb-btn:hover{background:rgba(54,203,224,.12);box-shadow:0 10px 30px -12px var(--glow);transform:translateY(-1px)}
#rb .rb-btn--fill{background:var(--accent);color:var(--accent-ink)}
#rb .rb-btn--fill:hover{background:#5fd8e9;color:var(--accent-ink)}
#rb .rb-btns{display:flex;flex-wrap:wrap;gap:14px;margin-top:30px}
/* шапка */
#rb .rb-head{position:sticky;top:0;z-index:50;background:rgba(43,48,53,.72);backdrop-filter:blur(14px) saturate(1.2);-webkit-backdrop-filter:blur(14px) saturate(1.2);border-bottom:1px solid transparent;transition:border-color .3s,background .3s}
#rb .rb-head[data-scrolled]{border-bottom-color:var(--line);background:rgba(43,48,53,.9)}
#rb .rb-head .rb-wrap{display:flex;align-items:center;justify-content:space-between;gap:24px;min-height:88px;transition:min-height .3s}
#rb .rb-head[data-scrolled] .rb-wrap{min-height:70px}
#rb .rb-logo img{height:66px;width:auto;transition:height .3s}
#rb .rb-head[data-scrolled] .rb-logo img{height:52px}
#rb .rb-nav{display:flex;gap:6px;font-size:15px}
#rb .rb-nav a{text-decoration:none;padding:8px 14px;border-radius:999px;color:var(--muted);transition:color .2s,background .2s}
#rb .rb-nav a:hover{color:#fff;background:var(--glass)}
#rb .rb-nav a[aria-current]{color:var(--accent);background:rgba(54,203,224,.1)}
#rb .rb-contact{display:flex;align-items:center;gap:18px}
#rb .rb-phone{font-family:var(--serif);font-size:18px;text-decoration:none;white-space:nowrap}
#rb .rb-phone:hover{color:var(--accent)}
#rb .rb-contact .rb-btn{padding:10px 22px;font-size:15px}
#rb .rb-burger{display:none;background:var(--glass);border:1px solid var(--line);border-radius:999px;color:#fff;padding:9px 18px;font:inherit;font-size:15px;cursor:pointer}
#rb .rb-mnav{display:none}
/* первый экран главной */
#rb .rb-intro{position:relative;min-height:min(calc(100vh - 88px),820px);display:flex;align-items:center;padding:40px 0 60px;overflow:hidden}
#rb .rb-intro .rb-wrap{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);align-items:center;gap:20px;width:100%}
#rb .rb-intro__text{position:relative;z-index:2}
#rb .rb-intro h1{font-size:clamp(30px,4.7vw,66px)}
#rb .rb-intro__lead{font-size:19px;color:var(--muted);max-width:520px}
#rb .rb-intro__face{position:relative;justify-self:end;width:min(100%,560px);aspect-ratio:1100/1028}
#rb .rb-intro__face::before{content:"";position:absolute;inset:8% 6% 10%;border-radius:50%;background:radial-gradient(closest-side,rgba(54,203,224,.32),rgba(54,203,224,.08) 60%,transparent);filter:blur(10px)}
#rb .rb-intro__face::after{content:"";position:absolute;inset:4% 2% 6%;border-radius:50%;border:1px solid rgba(54,203,224,.35)}
#rb .rb-intro__face img{position:relative;width:100%;height:100%;object-fit:contain;
  -webkit-mask-image:radial-gradient(ellipse 50% 52% at 50% 46%,#000 62%,transparent 100%);mask-image:radial-gradient(ellipse 50% 52% at 50% 46%,#000 62%,transparent 100%)}
#rb .rb-chips{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:40px;max-width:580px}
#rb .rb-chip{hyphens:auto;-webkit-hyphens:auto;overflow-wrap:break-word;background:var(--glass);border:1px solid var(--line);border-radius:var(--r-sm);padding:12px 18px;font-size:13px;color:var(--muted);line-height:1.35}
#rb .rb-chip b{display:block;font-family:var(--serif);font-weight:400;font-size:22px;color:var(--accent)}
/* заголовок внутренних страниц */
#rb .rb-hero{position:relative;padding:48px 0 20px;isolation:isolate}
#rb .rb-hero::before{content:"";position:absolute;inset:0 0 -120px;z-index:-1;background:url('""" + deco + """') center/cover no-repeat;opacity:.12;
  -webkit-mask-image:linear-gradient(180deg,#000 10%,transparent 100%);mask-image:linear-gradient(180deg,#000 10%,transparent 100%)}
#rb .rb-crumbs{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.12em;margin-bottom:26px;color:var(--muted)}
#rb .rb-crumbs a{text-decoration:none}
#rb .rb-crumbs a:hover{color:var(--accent)}
#rb .rb-crumbs span{margin:0 10px;opacity:.5}
#rb .rb-sec{padding:56px 0 88px}
#rb .rb-panel{background:linear-gradient(180deg,var(--glass-2),var(--glass));border:1px solid var(--line);border-radius:28px;padding:clamp(28px,5vw,64px)}
#rb .rb-lead{font-size:19px;max-width:820px;color:var(--muted)}
#rb .rb-rich{max-width:860px}
#rb .rb-rich h2,#rb .rb-rich h3{margin-top:1.4em}
#rb .rb-rich ul,#rb .rb-rich ol{padding-left:1.2em;margin:0 0 1em}
#rb .rb-rich li{margin-bottom:.35em}
#rb .rb-rich li::marker{color:var(--accent)}
#rb .rb-rich li p{margin:0}
#rb .rb-rich a{color:var(--accent)}
#rb .rb-rich img{margin:20px 0;border-radius:var(--r)}
#rb .rb-rich table{border-collapse:collapse;width:100%;margin:0 0 1em}
#rb .rb-rich td,#rb .rb-rich th{border:1px solid var(--line);padding:8px 10px;vertical-align:top}
/* карточки */
#rb .rb-grid{display:grid;gap:24px;grid-template-columns:repeat(auto-fill,minmax(250px,1fr))}
#rb .rb-card{display:flex;flex-direction:column;background:var(--glass);border:1px solid var(--line);border-radius:var(--r);padding:10px;text-decoration:none;transition:transform .35s cubic-bezier(.2,.7,.2,1),border-color .3s,box-shadow .35s,background .3s;min-width:0}
#rb a.rb-card:hover{transform:translateY(-6px);border-color:rgba(54,203,224,.6);background:var(--glass-2);box-shadow:0 24px 50px -28px var(--glow)}
#rb .rb-card__img{aspect-ratio:1/1;border-radius:var(--r-sm);background:#fff center/contain no-repeat;overflow:hidden;transition:background-size .5s}
#rb .rb-card__img--cover{background-size:cover}
#rb .rb-card__body{padding:18px 12px 12px;display:flex;flex-direction:column;gap:8px;flex:1}
#rb .rb-card__title{font-family:var(--serif);font-size:21px;line-height:1.2}
#rb .rb-card__text{font-size:15px;color:var(--muted)}
#rb .rb-card__more{margin-top:auto;padding-top:10px;color:var(--accent);font-size:14px;font-weight:600;display:inline-flex;align-items:center;gap:6px}
#rb a.rb-card:hover .rb-card__more{gap:10px}
#rb .rb-card__date{font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
/* товар */
#rb .rb-product{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:56px;align-items:start}
#rb .rb-product>div:first-child{position:sticky;top:96px}
#rb .rb-gal__main{background:#fff;border-radius:var(--r);aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}
#rb .rb-gal__main img{max-height:100%;width:auto;object-fit:contain}
#rb .rb-gal__nav{position:absolute;top:50%;transform:translateY(-50%);width:44px;height:44px;border:0;border-radius:50%;background:rgba(43,48,53,.75);color:#fff;font-size:22px;line-height:1;cursor:pointer;transition:background .2s}
#rb .rb-gal__nav:hover{background:var(--accent);color:var(--accent-ink)}
#rb .rb-gal__nav--prev{left:12px}#rb .rb-gal__nav--next{right:12px}
#rb .rb-gal__thumbs{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
#rb .rb-gal__thumbs button{width:72px;height:72px;padding:0;border:2px solid transparent;border-radius:var(--r-sm);background:#fff center/contain no-repeat;cursor:pointer;opacity:.7;transition:opacity .2s,border-color .2s}
#rb .rb-gal__thumbs button:hover{opacity:1}
#rb .rb-gal__thumbs button[aria-current]{border-color:var(--accent);opacity:1}
#rb .rb-fields{margin-top:28px;border-bottom:1px solid var(--line)}
#rb .rb-field{border-top:1px solid var(--line)}
#rb .rb-field summary{cursor:pointer;list-style:none;padding:18px 0;font-family:var(--serif);font-size:20px;display:flex;justify-content:space-between;align-items:center}
#rb .rb-field summary::-webkit-details-marker{display:none}
#rb .rb-field summary::after{content:"+";display:grid;place-items:center;width:32px;height:32px;border-radius:50%;border:1px solid var(--line);color:var(--accent);font-size:20px;line-height:1;transition:transform .3s}
#rb .rb-field[open] summary::after{transform:rotate(45deg)}
#rb .rb-field__val{color:var(--muted);padding-bottom:20px;font-size:15px}
/* отзывы */
#rb .rb-reviews{display:grid;gap:24px;grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}
#rb .rb-review{background:var(--glass);border:1px solid var(--line);border-radius:var(--r);padding:30px;display:flex;flex-direction:column;gap:12px;scroll-margin-top:110px;min-width:0}
#rb .rb-review::before{content:"\\201C";font-family:var(--serif);font-size:64px;line-height:.6;color:var(--accent)}
#rb .rb-review__author{font-family:var(--serif);font-size:19px;margin-top:auto;padding-top:14px;border-top:1px solid var(--line)}
#rb .rb-review__text{font-size:15px;color:var(--muted)}
#rb .rb-review__img{max-height:260px;width:auto;margin:6px 0;border-radius:var(--r-sm)}
#rb .rb-review details summary{cursor:pointer;color:var(--accent);font-size:14px;font-weight:600}
/* статистика, преимущества */
#rb .rb-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;margin:36px 0}
#rb .rb-stats>div{background:var(--glass);border:1px solid var(--line);border-radius:var(--r);padding:28px}
#rb .rb-stat__num{font-family:var(--serif);font-size:clamp(36px,4.5vw,56px);color:var(--accent);line-height:1}
#rb .rb-stat__txt{color:var(--muted);font-size:15px;margin-top:10px}
#rb .rb-adv{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;margin:30px 0 50px;text-align:center}
#rb .rb-adv figure{background:var(--glass);border:1px solid var(--line);border-radius:var(--r);padding:30px 20px}
#rb .rb-adv img{width:72px;height:72px;object-fit:contain;margin:0 auto 14px}
#rb .rb-adv div{font-family:var(--serif);font-size:20px}
/* расписание, список */
#rb .rb-list{display:flex;flex-direction:column;gap:20px}
#rb .rb-row{display:grid;grid-template-columns:260px minmax(0,1fr);gap:30px;border:1px solid var(--line);border-radius:var(--r);background:var(--glass);padding:10px;text-decoration:none;scroll-margin-top:110px;transition:border-color .3s,background .3s,box-shadow .35s}
#rb a.rb-row:hover{border-color:rgba(54,203,224,.6);background:var(--glass-2);box-shadow:0 24px 50px -28px var(--glow)}
#rb .rb-row__img{background:#fff center/cover no-repeat;min-height:200px;border-radius:var(--r-sm)}
#rb .rb-row__body{padding:18px 20px 18px 0}
#rb .rb-row__meta{color:var(--accent);font-size:13px;font-weight:600;margin-bottom:8px}
#rb .rb-logos{display:flex;flex-wrap:wrap;gap:20px;align-items:center;justify-content:center;margin-top:56px}
#rb .rb-logos img{height:72px;width:auto;padding:12px 22px;background:var(--glass);border:1px solid var(--line);border-radius:var(--r-sm)}
/* контакты */
#rb .rb-contacts{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:40px}
#rb .rb-ci{display:flex;gap:16px;margin-bottom:26px}
#rb .rb-ci img{width:44px;height:44px;flex:none;padding:9px;border-radius:50%;background:var(--glass);border:1px solid var(--line)}
#rb .rb-ci b{display:block;font-weight:600;margin-bottom:2px}
#rb .rb-ci a{display:block;text-decoration:none;word-break:break-word}
#rb .rb-ci a:hover{color:var(--accent)}
#rb .rb-map{min-height:420px;border:0;width:100%;height:100%;border-radius:var(--r)}
/* подвал */
#rb .rb-foot{border-top:1px solid var(--line);padding:56px 0 40px;font-size:14px;color:var(--muted);background:rgba(0,0,0,.12)}
#rb .rb-foot .rb-wrap{display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:30px}
#rb .rb-foot a{text-decoration:none}
#rb .rb-foot a:hover{color:var(--accent)}
#rb .rb-foot nav{display:flex;flex-direction:column;gap:8px}
#rb .rb-social{display:flex;gap:10px;flex-wrap:wrap}
#rb .rb-social a{border:1px solid var(--line);border-radius:999px;padding:6px 14px;transition:border-color .2s}
#rb .rb-social a:hover{border-color:var(--accent)}
/* появление при прокрутке (только если работает JS) */
#rb.rb-js .rb-reveal{opacity:0;transform:translateY(28px);transition:opacity .8s cubic-bezier(.2,.7,.2,1),transform .8s cubic-bezier(.2,.7,.2,1)}
#rb.rb-js .rb-reveal.is-in{opacity:1;transform:none}
#rb.rb-js .rb-intro__text>*{animation:rb-up .9s cubic-bezier(.2,.7,.2,1) both}
#rb.rb-js .rb-intro__text>*:nth-child(2){animation-delay:.08s}#rb.rb-js .rb-intro__text>*:nth-child(3){animation-delay:.16s}
#rb.rb-js .rb-intro__text>*:nth-child(4){animation-delay:.24s}#rb.rb-js .rb-intro__text>*:nth-child(5){animation-delay:.32s}
#rb.rb-js .rb-intro__face{animation:rb-fade 1.4s ease .1s both}
@keyframes rb-up{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}
@keyframes rb-fade{from{opacity:0;transform:scale(1.04)}to{opacity:1;transform:none}}
@media (max-width:1100px){#rb .rb-nav{display:none}#rb .rb-burger{display:inline-block}
  #rb .rb-mnav[data-open]{display:flex;flex-direction:column;padding:8px 24px 22px}
  #rb .rb-mnav a{padding:12px 0;text-decoration:none;font-size:18px;border-bottom:1px solid var(--line)}}
@media (max-width:900px){
  #rb .rb-intro{min-height:0;padding:10px 0 50px}
  #rb .rb-intro .rb-wrap{grid-template-columns:minmax(0,1fr)}
  #rb .rb-intro__face{order:-1;justify-self:center;width:min(86%,420px);margin-bottom:-30px}
  #rb .rb-intro__face img{-webkit-mask-image:radial-gradient(ellipse 50% 50% at 50% 45%,#000 55%,transparent 100%);mask-image:radial-gradient(ellipse 50% 50% at 50% 45%,#000 55%,transparent 100%)}}
@media (max-width:820px){#rb{font-size:16px}
  #rb .rb-product,#rb .rb-contacts,#rb .rb-foot .rb-wrap{grid-template-columns:minmax(0,1fr)}
  #rb .rb-product{gap:32px}#rb .rb-product>div:first-child{position:static}
  #rb .rb-row{grid-template-columns:minmax(0,1fr)}#rb .rb-row__body{padding:6px 12px 14px}
  #rb .rb-stats,#rb .rb-adv{grid-template-columns:minmax(0,1fr)}
  #rb .rb-reviews{grid-template-columns:minmax(0,1fr)}
  #rb .rb-review{padding:24px}
  #rb .rb-sec{padding:40px 0 64px}
  #rb .rb-phone{display:none}#rb .rb-logo img,#rb .rb-head[data-scrolled] .rb-logo img{height:52px}
  #rb .rb-head .rb-wrap,#rb .rb-head[data-scrolled] .rb-wrap{min-height:68px}#rb .rb-contact{gap:10px}#rb .rb-contact .rb-btn{padding:9px 16px;font-size:14px}}
@media (max-width:440px){#rb .rb-contact .rb-btn{display:none}#rb .rb-chip{padding:10px 12px;font-size:12px}#rb .rb-chip b{font-size:19px}}
@media (prefers-reduced-motion:reduce){#rb *{transition:none!important;animation:none!important}#rb.rb-js .rb-reveal{opacity:1;transform:none}}
</style>"""

def header(alias):
    logo = img('index.html', 'images/custom/logo.svg')
    links = ''.join(f'<a href="{h}"{" aria-current=\"page\"" if h == alias else ""}>{t}</a>' for t, h in NAV)
    return f'''<header class="rb-head"><div class="rb-wrap">
<a class="rb-logo" href="/" aria-label="Революшн Био — на главную"><img src="{logo}" alt="Революшн Био"></a>
<nav class="rb-nav" aria-label="Меню">{links}</nav>
<div class="rb-contact"><a class="rb-phone" href="{PHONE_HREF}">{PHONE}</a><a class="rb-btn" href="#popup:callback">Заказать звонок</a>
<button class="rb-burger" type="button" aria-expanded="false" aria-controls="rb-mnav">Меню</button></div>
</div><nav class="rb-mnav" id="rb-mnav" aria-label="Мобильное меню">{links}<a href="{PHONE_HREF}">{PHONE}</a></nav></header>'''

def footer():
    links = ''.join(f'<a href="{h}">{t}</a>' for t, h in NAV)
    return f'''<footer class="rb-foot"><div class="rb-wrap">
<div><p>© <span data-rb-year>2026</span> ООО «Революшн Био» — все права защищены.<br>ИНН: 9709100594 · КПП: 770901001</p>
<p><a href="/policy">Политика обработки персональных данных</a><br><a href="/soglasie">Согласие на обработку персональных данных</a></p></div>
<nav aria-label="Разделы">{links}<a href="/akcii">Акции</a><a href="/partners">Партнёры</a></nav>
<div><p><a href="{PHONE_HREF}">{PHONE}</a><br><a href="mailto:{EMAIL}">{EMAIL}</a><br>Москва, Земляной Вал 7, офис 408</p>
<div class="rb-social"><a href="https://t.me/revolutionbio" target="_blank" rel="noopener">Telegram</a><a href="https://wa.me/79250843090" target="_blank" rel="noopener">WhatsApp</a><a href="https://vk.com/revolutionbio" target="_blank" rel="noopener">ВКонтакте</a><a href="https://dzen.ru/revolutionbio" target="_blank" rel="noopener">Дзен</a></div>
<p style="margin-top:18px"><a class="rb-btn" href="#popup:feedback">Обратная связь</a></p></div>
</div></footer>'''

JS = '''<script>
(function(){var r=document.getElementById('rb');if(!r)return;
var b=r.querySelector('.rb-burger'),m=r.querySelector('.rb-mnav');
if(b&&m)b.addEventListener('click',function(){var o=m.hasAttribute('data-open');if(o)m.removeAttribute('data-open');else m.setAttribute('data-open','');b.setAttribute('aria-expanded',String(!o));});
var y=r.querySelector('[data-rb-year]');if(y)y.textContent=new Date().getFullYear();
r.querySelectorAll('.rb-gal').forEach(function(g){var im=g.querySelector('.rb-gal__main img'),th=[].slice.call(g.querySelectorAll('.rb-gal__thumbs button')),i=0;
 function go(n){if(!th.length)return;i=(n+th.length)%th.length;im.src=th[i].getAttribute('data-src');th.forEach(function(t,k){if(k===i)t.setAttribute('aria-current','true');else t.removeAttribute('aria-current');});}
 th.forEach(function(t,k){t.addEventListener('click',function(){go(k);});});
 var p=g.querySelector('.rb-gal__nav--prev'),n=g.querySelector('.rb-gal__nav--next');
 if(p)p.addEventListener('click',function(){go(i-1);});if(n)n.addEventListener('click',function(){go(i+1);});});
var h=r.querySelector('.rb-head');function sc(){if(!h)return;if(window.scrollY>10)h.setAttribute('data-scrolled','');else h.removeAttribute('data-scrolled');}
sc();window.addEventListener('scroll',sc,{passive:true});
if('IntersectionObserver' in window&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
 r.classList.add('rb-js');
 var els=r.querySelectorAll('.rb-sec h2,.rb-kicker,.rb-card,.rb-review,.rb-row,.rb-stats>div,.rb-adv figure,.rb-panel,.rb-gal,.rb-fields');
 var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('is-in');io.unobserve(e.target);}});},{rootMargin:'0px 0px -8% 0px'});
 els.forEach(function(el,k){el.classList.add('rb-reveal');el.style.transitionDelay=(k%4)*70+'ms';io.observe(el);});
}
})();
</script>'''

def crumbs(items):
    parts = ['<a href="/">Главная</a>'] + [f'<a href="{h}">{esc(t)}</a>' if h else esc(t) for t, h in items]
    return '<nav class="rb-crumbs" aria-label="Навигация">' + '<span>—</span>'.join(parts) + '</nav>'

def hero(h1, crumb_items, lead=''):
    return f'''<section class="rb-hero"><div class="rb-wrap">{crumbs(crumb_items)}
<h1>{esc(h1)}</h1><hr class="rb-rule">{f'<div class="rb-lead rb-rich">{lead}</div>' if lead else ''}</div></section>'''

def card(href, image, title, txt='', more='Подробнее', date='', cover=False):
    tag = 'a' if href else 'div'
    hr = f' href="{href}"' if href else ''
    im = f'<div class="rb-card__img{" rb-card__img--cover" if cover else ""}" style="background-image:url(\'{image}\')" role="img" aria-label="{esc(title)}"></div>' if image else ''
    return f'''<{tag} class="rb-card"{hr}>{im}<div class="rb-card__body">{f'<div class="rb-card__date">{esc(date)}</div>' if date else ''}<div class="rb-card__title">{esc(title)}</div>{f'<div class="rb-card__text">{esc(txt)}</div>' if txt else ''}{f'<span class="rb-card__more">{more} →</span>' if href and more else ''}</div></{tag}>'''

def gallery(images, alt):
    if not images:
        return ''
    th = ''.join(f'<button type="button" data-src="{u}" style="background-image:url(\'{u}\')" aria-label="Фото {k + 1}"{" aria-current=\"true\"" if k == 0 else ""}></button>' for k, u in enumerate(images))
    nav = '<button class="rb-gal__nav rb-gal__nav--prev" type="button" aria-label="Предыдущее фото">‹</button><button class="rb-gal__nav rb-gal__nav--next" type="button" aria-label="Следующее фото">›</button>' if len(images) > 1 else ''
    return f'''<div class="rb-gal"><div class="rb-gal__main"><img src="{images[0]}" alt="{esc(alt)}">{nav}</div>{f'<div class="rb-gal__thumbs">{th}</div>' if len(images) > 1 else ''}</div>'''

def review_html(r, anchor=True):
    body = r['text']
    short = shorten(body, 420)
    if len(strip_tags(body)) > 440:
        inner = f'<div class="rb-review__text">{esc(short)}</div><details><summary>Читать полностью</summary><div class="rb-review__text rb-rich" style="margin-top:10px">{body}</div></details>'
    else:
        inner = f'<div class="rb-review__text rb-rich">{body}</div>'
    pic = f'<img class="rb-review__img" src="{r["image"]}" alt="Отзыв: {esc(r["author"])}" loading="lazy">' if r.get('image') else ''
    return f'<article class="rb-review"{f" id=\"{r["id"]}\"" if anchor else ""}>{pic}{inner}<div class="rb-review__author">{esc(r["author"])}</div></article>'

def page(alias, title, body, seo):
    head = f'''<!-- REVOLUTION BIO — {esc(title)} ({alias})
     Вставлять целиком в блок T123 «HTML-код» на странице Tilda с адресом {alias}.
     SEO (Настройки страницы → SEO): title: {esc(seo.get("title", ""))}
     description: {esc(seo.get("description", ""))}
     Формы: создайте на странице блок «Форма в попапе» (BF502N) со ссылкой #popup:callback
     и второй с #popup:feedback — см. README.md. -->
'''
    doc = head + FONTS + '\n' + css() + f'\n<div id="rb" lang="ru">\n{header(alias)}\n<main>\n{body}\n</main>\n{footer()}\n</div>\n' + JS + '\n'
    name = 'home' if alias == '/' else alias.strip('/')
    for d, ext in (('tilda', '.html'), ('tilda-txt', '.txt')):
        with open(os.path.join(OUT, d, name + ext), 'w', encoding='utf-8') as f:
            f.write(doc)
    SEO.append((alias, name, seo.get('title', ''), seo.get('description', ''), seo.get('keywords', '')))

SEO = []
REPORT = []

def seo_of(s, fallback_title):
    t = title_of(s) or fallback_title
    if t and 'Революшн' not in t and 'Revolution' not in t:
        t = f'{t} — Революшн Био'
    return {'title': t, 'description': meta(s, 'description'), 'keywords': meta(s, 'keywords')}

# ---------------------------------------------------------------- сбор отзывов и преподавателей (нужно до вёрстки ссылок)
def collect_reviews():
    seen, out = set(), []
    for rel in ('product/itemlist/category/93-otzyvy-tovarov.html', 'product/itemlist/category/4-otzyvy.html'):
        s = soup(rel)
        for it in cat_items(rel, s):
            ir = it['href_rel']
            if not ir:
                continue
            m = re.search(r'/(\d+)-[^/]+\.html$', ir)
            iid = m.group(1) if m else ir
            if iid in seen:
                continue
            seen.add(iid)
            path = ir if os.path.isfile(os.path.join(SRC, ir)) else None
            if path:
                d = k2_item(path, soup(path))
                txt = (d['intro'] or '') + ('\n' + d['full'] if d['full'] else '')
                image = d['image']
            else:
                txt, image = it['intro'], it['image']
            out.append({'id': f'otzyv-{iid}', 'author': it['title'], 'text': txt, 'image': image, 'rel': ir})
    for r in out:
        for pref in ('product/item/', 'partners/item/'):
            ANCHORS[pref + os.path.basename(r['rel'])] = f'/otzyvy#{r["id"]}'
    # отзывы из модуля главной ссылаются на /component/k2/item/7-..., 8-...
    return out

def collect_teachers():
    rel = 'uchebnyj-tsentr/itemlist/category/18-teachers.html'
    s = soup(rel)
    out = []
    for it in cat_items(rel, s):
        ir = it['href_rel']
        m = re.search(r'/(\d+)-[^/]+\.html$', ir or '')
        iid = m.group(1) if m else str(len(out))
        if any(t['name'] == it['title'] for t in out):
            ANCHORS[ir] = f'/prepodavateli#{next(t for t in out if t["name"] == it["title"])["id"]}'
            continue
        d = k2_item(ir, soup(ir)) if ir and os.path.isfile(os.path.join(SRC, ir)) else None
        out.append({'id': f'trener-{iid}', 'name': it['title'], 'image': (d and d['image']) or it['image'],
                    'text': ((d['intro'] + '\n' + d['full']) if d else it['intro'])})
        if ir:
            ANCHORS[ir] = f'/prepodavateli#trener-{iid}'
    return out

REVIEWS = collect_reviews()
TEACHERS = collect_teachers()

# ---------------------------------------------------------------- страницы
def build_home(rel):
    s = soup(rel)
    lis = s.select('.custom-slider ul.slides > li')
    sub = text(lis[0].select_one('.main-page-subtitle'))
    # продукция
    cat_desc = {norm_rel('product.html', a['href']): text(a.select_one('.product-description')) for a in soup('product.html').select('.products-category a.product')}
    cats = ''
    for a in lis[1].select('a.product'):
        cats += card(map_link(rel, a['href']), bg_url(rel, a), text(a.select_one('.product-title')), shorten(cat_desc.get(norm_rel(rel, a['href']), ''), 140))
    # учебный центр
    teach_desc = clean(rel, lis[2].select_one('.teaching-description'))
    events = ''
    for a in lis[2].select('a.teaching-event'):
        when = text(a.select_one('.teaching-event-date'))
        events += card(map_link(rel, a['href']), bg_url(rel, a.select_one('.teaching-event-left')),
                       text(a.select_one('.teaching-event-right-title')), shorten(text(a.select_one('.teaching-event-right-text')), 150), date=when, cover=True)
    # о компании
    about_desc = clean(rel, lis[3].select_one('.about-description'))
    stats = ''.join(f'<div><div class="rb-stat__num">{esc(text(t.select_one(".about-testimnial-number")))}</div><div class="rb-stat__txt">{esc(text(t.select_one(".about-testimnial-decription")))}</div></div>' for t in lis[3].select('.about-testimnial'))
    # отзывы — первые три с главной
    revs = ''
    for rv in lis[4].select('.review')[:3]:
        revs += review_html({'author': text(rv.select_one('.review-author')), 'text': clean(rel, rv.select_one('.review-text')), 'image': None}, anchor=False)
    logos = ''.join(f'<img src="{img(rel, im["src"])}" alt="Партнёр" loading="lazy">' for im in lis[4].select('img[src*="partner"]'))
    face = img(rel, 'images/custom/main_bg.png', 1100)
    chips = ''.join(f'<div class="rb-chip"><b>{esc(text(t.select_one(".about-testimnial-number")))}</b>{esc(text(t.select_one(".about-testimnial-decription")).split("(")[0].strip())}</div>' for t in lis[3].select('.about-testimnial'))
    body = f'''<section class="rb-intro"><div class="rb-wrap">
<div class="rb-intro__text"><span class="rb-kicker">Революшн Био · для косметологов</span>
<h1>Инновационные<br>решения для красоты</h1><hr class="rb-rule">
<p class="rb-intro__lead">{esc(sub)}</p>
<div class="rb-btns"><a class="rb-btn rb-btn--fill" href="#popup:callback">Получить консультацию</a><a class="rb-btn" href="/product">Каталог продукции</a></div>
<div class="rb-chips">{chips}</div></div>
<div class="rb-intro__face"><img src="{face}" alt="Сияющая кожа — результат профессионального ухода" fetchpriority="high"></div>
</div></section>
<section class="rb-sec"><div class="rb-wrap"><span class="rb-kicker">Каталог</span><h2>Продукция</h2><hr class="rb-rule"><div class="rb-grid">{cats}</div>
<div class="rb-btns"><a class="rb-btn" href="/product">Весь каталог</a></div></div></section>
<section class="rb-sec"><div class="rb-wrap"><span class="rb-kicker">Обучение</span><h2>Учебный центр</h2><hr class="rb-rule"><div class="rb-rich" style="margin-bottom:34px">{teach_desc}</div>
<div class="rb-grid">{events}</div><div class="rb-btns"><a class="rb-btn" href="/uchebnyj-tsentr">Все программы обучения</a></div></div></section>
<section class="rb-sec"><div class="rb-wrap"><div class="rb-panel"><span class="rb-kicker">О компании</span><h2>Революшн Био</h2><hr class="rb-rule"><div class="rb-rich">{about_desc}</div>
<div class="rb-stats">{stats}</div><a class="rb-btn" href="/about">Подробнее о компании</a></div></div></section>
<section class="rb-sec"><div class="rb-wrap"><span class="rb-kicker">Нам доверяют</span><h2>Отзывы</h2><hr class="rb-rule"><div class="rb-reviews">{revs}</div>
<div class="rb-btns"><a class="rb-btn" href="/otzyvy">Все отзывы</a></div><div class="rb-logos">{logos}</div></div></section>
{contacts_section(rel, s, h='h2')}'''
    seo = seo_of(s, 'Революшн Био')
    seo['title'] = 'Революшн Био — инновационные препараты для косметологов' if seo['title'] in ('Home — Революшн Био', '') else seo['title']
    page('/', 'Главная', body, seo)

def contacts_section(rel, s, h='h1'):
    el = s.select_one('.contact-info') or soup('kontakty.html').select_one('.contact-info')
    icons = {k: img('kontakty.html', f'images/custom/{k}.png') for k in ('address', 'mail', 'phone')}
    tg = '\n'.join(f'<a href="{u}" target="_blank" rel="noopener">{lab}</a>' for lab, u in (
        ('WhatsApp: +7 925 084-30-90', 'https://wa.me/79250843090'), ('WhatsApp: +7 925 342-82-02', 'https://wa.me/79253428202'),
        ('Telegram: @revolution_bio', 'https://t.me/revolution_bio'), ('Telegram: +7 925 084-30-90', 'https://t.me/+79250843090')))
    addr = text(el.select_one('.contact-address .text')).replace('Адрес:', '').strip() if el else 'Земляной Вал 7, офис 408'
    title = f'<span class="rb-kicker">Связаться с нами</span><{h}>Контакты</{h}><hr class="rb-rule">' if h == 'h2' else ''
    return f'''<section class="rb-sec" id="kontakty"><div class="rb-wrap">{title}<div class="rb-contacts"><div>
<div class="rb-ci"><img src="{icons['address']}" alt=""><div><b>Адрес</b>Москва, {esc(addr)}</div></div>
<div class="rb-ci"><img src="{icons['mail']}" alt=""><div><b>E-mail</b><a href="mailto:{EMAIL}">{EMAIL}</a></div></div>
<div class="rb-ci"><img src="{icons['phone']}" alt=""><div><b>Телефоны и мессенджеры</b><a href="{PHONE_HREF}">{PHONE}</a>{tg}</div></div>
<div class="rb-btns"><a class="rb-btn rb-btn--fill" href="#popup:feedback">Написать нам</a></div></div>
<iframe class="rb-map" title="Карта: Революшн Био" loading="lazy" src="https://yandex.ru/map-widget/v1/?um=constructor%3A6803285ddfeb9e98a988d37f868485f1206350bc7beb3cbd2119804af2401e11&amp;source=constructor"></iframe>
</div></div></section>'''

def build_contacts(rel):
    s = soup(rel)
    page('/kontakty', 'Контакты', hero('Контакты', [('Контакты', None)]) + contacts_section(rel, s), seo_of(s, 'Контакты'))

def build_about(rel):
    s = soup(rel)
    a = s.select_one('.about-custom .about-custom') or s.select_one('.about-custom')
    parts = []
    adv = ''
    for ch in a.find_all(recursive=False):
        cl = ' '.join(ch.get('class') or [])
        if 'about-inner-advantages' in cl:
            adv = '<div class="rb-adv">' + ''.join(f'<figure style="margin:0"><img src="{img(rel, x.find("img")["src"])}" alt=""><div>{esc(text(x.select_one(".about-inner-advantage-description")).replace(" ", "", 1) if False else x.select_one(".about-inner-advantage-description").get_text("", strip=True))}</div></figure>' for x in ch.select('.about-inner-advantage')) + '</div>'
            parts.append(adv)
        elif 'about-inner-title' in cl:
            parts.append(f'<h2>{esc(text(ch))}</h2>')
        elif 'about-inner-subtitle' in cl:
            parts.append(f'<h3>{esc(text(ch))}</h3>')
        else:
            c = clean(rel, ch)
            if strip_tags(c):
                parts.append(c if c.lstrip().startswith('<') else f'<p>{c}</p>')
    title = strip_tags(parts.pop(0)) if parts and parts[0].startswith('<h2>') else 'О компании'
    sub = [('Акции', '/akcii'), ('Партнёры', '/partners'), ('Новости', '/news')]
    btns = ''.join(f'<a class="rb-btn" href="{h}">{t}</a>' for t, h in sub)
    body = hero('О компании', [('О компании', None)]) + f'''<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><h2>{esc(title)}</h2><div class="rb-rich">{''.join(parts)}</div><div class="rb-btns">{btns}</div></div></section>'''
    page('/about', 'О компании', body, seo_of(s, 'О компании'))

def build_catalog(rel):
    s = soup(rel)
    desc = clean(rel, s.select_one('.products-category-description'))
    cards = ''
    for a in s.select('.products-category a.product'):
        cards += card(map_link(rel, a['href']), bg_url(rel, a), text(a.select_one('.product-title')), shorten(text(a.select_one('.product-description')), 160))
    body = hero('Продукция', [('Продукция', None)], desc) + f'<section class="rb-sec"><div class="rb-wrap"><div class="rb-grid">{cards}</div></div></section>'
    page('/product', 'Продукция', body, seo_of(s, 'Продукция'))

def build_category(rel, alias):
    s = soup(rel)
    name = title_of(s)
    desc = clean(rel, s.select_one('.products-subcategory-description'))
    cards = ''
    for it in s.select('.products-list > .product-item'):
        a = it.select_one('a.product')
        cards += card(map_link(rel, a['href']), bg_url(rel, a), text(a.select_one('.product-title')), shorten(text(a.select_one('.product-description')), 150))
    body = hero(name, [('Продукция', '/product'), (name, None)]) + f'''<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><div class="rb-grid">{cards}</div></div></section>
{f'<section class="rb-sec"><div class="rb-wrap"><div class="rb-rich">{desc}</div></div></section>' if strip_tags(desc) else ''}
<section class="rb-sec"><div class="rb-wrap"><div class="rb-panel"><span class="rb-kicker">Обратная связь</span><h2>Подберём препараты под ваши задачи</h2><p class="rb-muted">Оставьте заявку — менеджер подберёт препараты и расскажет об условиях для специалистов.</p><a class="rb-btn rb-btn--fill" href="#popup:feedback">Оставить заявку</a></div></div></section>'''
    page(alias, name, body, seo_of(s, name))
    return name

CAT_OF = {}
def build_product(rel, alias):
    s = soup(rel)
    d = k2_item(rel, s)
    pp = s.select_one('.product-page')
    main = pp.select_one('.main-product-photo a.product-photo')
    imgs = []
    if main and main.get('href'):
        u = img(rel, main['href'])
        if u: imgs.append(u)
    for g in pp.select('.main-product-photo .sigProLink[href]'):
        u = img(rel, g['href'])
        if u and u not in imgs: imgs.append(u)
    short = ''.join(clean(rel, x) for x in pp.select('.product-page-right > .product-page-description:not(:has(.itemFullText))'))
    full = clean(rel, pp.select_one('.product-page-right .itemFullText'))
    fields = []
    for t in pp.select('.product-ex-title'):
        v = t.find_next_sibling(class_='product-ex-value')
        val = clean(rel, v)
        if strip_tags(val):
            fields.append((text(t), val))
    fhtml = ''.join(f'<details class="rb-field"{" open" if k == 0 else ""}><summary>{esc(l)}</summary><div class="rb-field__val rb-rich">{v}</div></details>' for k, (l, v) in enumerate(fields))
    # отзывы и рекомендации
    revs = ''
    for rv in s.select('.product-page-reviews .review'):
        btn = rv.select_one('.review-btn')
        link = map_link(rel, btn['href']) if btn else None
        rid = link.split('#')[1] if link and '#' in link else None
        full_r = next((r for r in REVIEWS if r['id'] == rid), None)
        revs += review_html(full_r or {'author': text(rv.select_one('.review-author')), 'text': clean(rel, rv.select_one('.review-text')), 'image': None}, anchor=False)
    recs = ''
    for a in s.select('.recomended-products a.product'):
        recs += card(map_link(rel, a['href']), bg_url(rel, a), text(a.select_one('.product-title')), shorten(text(a.select_one('.product-description')), 120))
    bc = s.select('.breadcrumb a, .breadcrumbs a, ul.breadcrumb li a')
    cat = CAT_OF.get(rel)
    crumb = [('Продукция', '/product')] + ([cat] if cat else []) + [(d['title'], None)]
    body = hero(d['title'], crumb) + f'''<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><div class="rb-product">
<div>{gallery(imgs, d['title'])}<div class="rb-btns"><a class="rb-btn rb-btn--fill" href="#popup:order">Заказать товар</a><a class="rb-btn" href="#popup:callback">Получить консультацию</a></div></div>
<div class="rb-rich">{short}<div class="rb-fields">{fhtml}</div>{f'<div style="margin-top:26px">{full}</div>' if strip_tags(full) else ''}</div>
</div></div></section>
{f'<section class="rb-sec"><div class="rb-wrap"><h2>Отзывы о продукции</h2><p class="rb-muted">Вот что говорят люди, которые уже пользовались этим средством</p><div class="rb-reviews">{revs}</div></div></section>' if revs else ''}
{f'<section class="rb-sec"><div class="rb-wrap"><h2>Рекомендованные товары</h2><p class="rb-muted">Эти товары могут вас заинтересовать</p><div class="rb-grid">{recs}</div></div></section>' if recs else ''}'''
    page(alias, d['title'], body, seo_of(s, d['title']))

def build_article(rel, alias):
    s = soup(rel)
    d = k2_item(rel, s)
    v = s.select_one('.itemView')
    custom = v.select_one('.item-new-custom') if v else None
    if custom:
        im = custom.select_one('.item-new-custom-img img')
        d['image'] = d['image'] or (img(rel, im['src']) if im else None)
    if rel in INTRO_ONLY:
        d['full'] = ''
        REPORT.append(f'{alias}: перенесено только вступление (полный текст — перепечатка сторонней статьи)')
    section = {'news': [('Новости', '/news')], 'uchebnyj-tsentr': [('Учебный центр', '/uchebnyj-tsentr')]}.get(rel.split('/')[0], [])
    fields = ''.join(f'<p><strong>{esc(l)}:</strong> {strip_tags(v_) if len(strip_tags(v_)) < 80 else v_}</p>' for l, v_ in d['fields'])
    pic = f'<img src="{d["image"]}" alt="{esc(d["title"])}" style="max-width:640px;width:100%;margin:0 0 30px">' if d['image'] else ''
    gal = ''.join(f'<img src="{u}" alt="" loading="lazy">' for u in d['gallery'])
    extra = ''
    if alias in ('/obuchenie-kosmetologov', '/exosomes-summit-dubrovnik'):
        extra = '<div class="rb-btns"><a class="rb-btn rb-btn--fill" href="#popup:signup">Записаться</a><a class="rb-btn" href="/uchebnyj-tsentr">Все программы</a></div>'
    if rel in INTRO_ONLY:
        extra = '<p class="rb-muted">Полный текст статьи доступен по запросу — напишите нам.</p>'
    body = hero(d['title'], section + [(d['title'], None)]) + f'''<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><div class="rb-rich">{pic}{fields}{d['intro']}{d['full']}{gal}</div>{extra}</div></section>'''
    page(alias, d['title'], body, seo_of(s, d['title']))

def build_reviews(rel):
    s = soup(rel)
    body = hero('Отзывы', [('Отзывы', None)], '<p>Отзывы косметологов, пациентов и партнёров о препаратах и обучении Революшн Био.</p>') + \
        f'<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><div class="rb-reviews">{"".join(review_html(r) for r in REVIEWS)}</div></div></section>'
    page('/otzyvy', 'Отзывы', body, seo_of(s, 'Отзывы'))

def build_school(rel):
    s = soup(rel)
    intro = clean(rel, s.select_one('.intrduction'))
    rows = ''
    for ev in s.select('.schedule-event'):
        a = ev.select_one('a.schedule-event-title')
        href = map_link(rel, a['href']) if a else None
        cv = ev.select_one('.catItemView')
        ci = cat_items(rel, BeautifulSoup(f'<div>{cv}</div>', 'lxml')) if cv else []
        when = text(ev.select_one('.teachingnormdate')) or 'По запросу'
        teacher = text(ev.select_one('.schedule-event-teacher')).replace('Преподаватель:', '').strip()
        title = text(a)
        ir = norm_rel(rel, a['href']) if a else None
        d = k2_item(ir, soup(ir)) if ir and os.path.isfile(os.path.join(SRC, ir)) else None
        image = (ci[0]['image'] if ci else None) or (d and d['image'])
        intro_ev = shorten((ci[0]['intro'] if ci else '') or (d and (d['intro'] or d['full'])) or '', 260)
        rows += f'''<a class="rb-row" href="{href or '#popup:signup'}"><div class="rb-row__img" style="{f"background-image:url('{image}')" if image else ''}"></div><div class="rb-row__body">
<div class="rb-row__meta">Дата проведения: {esc(when)}{f' · Преподаватель: {esc(teacher)}' if teacher else ''}</div><h3>{esc(title)}</h3><p class="rb-muted">{esc(intro_ev)}</p><span class="rb-card__more">Подробнее →</span></div></a>'''
    directions = [text(o) for o in s.select('select option')][1:8]
    tcards = ''.join(card(f'/prepodavateli#{t["id"]}', t['image'], t['name'], shorten(t['text'], 120), cover=True) for t in TEACHERS)
    body = hero('Учебный центр', [('Учебный центр', None)], intro) + f'''<section class="rb-sec" style="padding-top:0"><div class="rb-wrap">
<div class="rb-btns" style="margin:0 0 50px"><a class="rb-btn rb-btn--fill" href="#popup:signup">Записаться на обучение</a><a class="rb-btn" href="#popup:callback">Стать моделью</a><a class="rb-btn" href="#popup:callback">Стать тренером</a></div>
<h2>Расписание</h2><hr class="rb-rule"><p class="rb-muted">Мы проводим обучение по всем тематическим направлениям косметологии: {esc(', '.join(directions).lower())}.</p>
<div class="rb-list">{rows}</div></div></section>
<section class="rb-sec"><div class="rb-wrap"><h2>Преподаватели</h2><hr class="rb-rule"><div class="rb-grid">{tcards}</div></div></section>'''
    page('/uchebnyj-tsentr', 'Учебный центр', body, seo_of(s, 'Учебный центр'))

def build_teachers(rel):
    s = soup(rel)
    rows = ''.join(f'''<article class="rb-row" id="{t['id']}"><div class="rb-row__img" style="{f"background-image:url('{t['image']}')" if t['image'] else ''}"></div><div class="rb-row__body"><h3>{esc(t['name'])}</h3><div class="rb-rich">{t['text']}</div></div></article>''' for t in TEACHERS)
    body = hero('Преподаватели', [('Учебный центр', '/uchebnyj-tsentr'), ('Преподаватели', None)]) + f'<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><div class="rb-list">{rows}</div><div class="rb-btns"><a class="rb-btn rb-btn--fill" href="#popup:signup">Записаться на обучение</a></div></div></section>'
    page('/prepodavateli', 'Преподаватели', body, seo_of(s, 'Преподаватели'))

def build_sales(rel):
    s = soup(rel)
    rows = ''
    for sale in s.select('.sales-list > .sale'):
        a = sale.select_one('.sale-title a')
        ir = norm_rel(rel, a['href']) if a else None
        d = k2_item(ir, soup(ir)) if ir and os.path.isfile(os.path.join(SRC, ir)) else None
        image = (d and d['image']) or bg_url(rel, sale.select_one('.sale-img'))
        txt = (d['intro'] + d['full']) if d else clean(rel, sale.select_one('.sale-description'))
        when = text(sale.select_one('.salesdate'))
        rows += f'''<article class="rb-row"><div class="rb-row__img" style="{f"background-image:url('{image}')" if image else ''}"></div><div class="rb-row__body">{f'<div class="rb-row__meta">Действует с {esc(when)}</div>' if when else ''}<h3>{esc(text(a))}</h3><div class="rb-rich">{txt}</div><a class="rb-btn" href="#popup:discount">Получить скидку</a></div></article>'''
    body = hero('Акции и спецпредложения', [('О компании', '/about'), ('Акции', None)], '<p>Всегда рады предложить нашим клиентам интересные условия.</p>') + f'<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><div class="rb-list">{rows}</div></div></section>'
    page('/akcii', 'Акции', body, seo_of(s, 'Акции'))

def build_news(rel):
    s = soup(rel)
    cards = ''
    for n in s.select('.news-list > .new'):
        a = n.select_one('.read-more a')
        cards += card(map_link(rel, a['href']) if a else None, bg_url(rel, n.select_one('.new-img')), text(n.select_one('.new-title')),
                      shorten(text(n.select_one('.new-description')), 160), date=text(n.select_one('.news-date-create')), cover=True)
    body = hero('Новости', [('О компании', '/about'), ('Новости', None)], '<p>Последние новости компании.</p>') + f'<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><div class="rb-grid">{cards}</div></div></section>'
    page('/news', 'Новости', body, seo_of(s, 'Новости'))

def build_partners(rel):
    s = soup(rel)
    blocks = ''
    for crel, city in (('partners/itemlist/category/16-moscow.html', 'Москва'), ('partners/itemlist/category/95-russia.html', 'Россия'), ('partners/itemlist/category/98-gruzia.html', 'Грузия')):
        cs = soup(crel)
        items = ''
        for p in cs.select('.partners-list > .partner'):
            items += f'<div class="rb-card"><div class="rb-card__body"><div class="rb-card__title">{esc(text(p.select_one(".partner-title")))}</div><div class="rb-card__text rb-rich">{clean(crel, p.select_one(".partner-description"))}</div></div></div>'
        if items:
            blocks += f'<h3 style="margin-top:40px">{city}</h3><div class="rb-grid">{items}</div>'
    buy = s.select_one('.itemListCategory a[href*="taplink"]')
    body = hero('Партнёры', [('О компании', '/about'), ('Партнёры', None)]) + f'''<section class="rb-sec" style="padding-top:0"><div class="rb-wrap">
<div class="rb-btns" style="margin:0 0 20px"><a class="rb-btn rb-btn--fill" href="#popup:callback">Начать бизнес с Революшн Био</a>{f'<a class="rb-btn" href="{buy["href"]}" target="_blank" rel="noopener">Купить →</a>' if buy else ''}</div>
<h2>Список партнёров</h2><hr class="rb-rule">{blocks}</div></section>'''
    page('/partners', 'Партнёры', body, seo_of(s, 'Партнёры'))

# категории товаров -> чтобы в крошках товара была категория
for rel, (alias, kind) in PAGES.items():
    if kind == 'category':
        cs = soup(rel)
        for a in cs.select('.products-list a.product'):
            CAT_OF.setdefault(norm_rel(rel, a['href']), (title_of(cs), alias))

for rel, (alias, kind) in PAGES.items():
    f = {'home': build_home, 'about': build_about, 'catalog': build_catalog, 'contacts': build_contacts,
         'reviews': build_reviews, 'school': build_school, 'teachers': build_teachers, 'sales': build_sales,
         'news': build_news, 'partners': build_partners}.get(kind)
    if f:
        f(rel)
    elif kind == 'category':
        build_category(rel, alias)
    elif kind == 'product':
        build_product(rel, alias)
    elif kind == 'article':
        build_article(rel, alias)

# ---------------------------------------------------------------- редиректы и SEO
redirects = []
def old_url(rel):
    return '/' if rel == 'index.html' else '/' + rel[:-5]
for rel, (alias, _) in PAGES.items():
    if old_url(rel) != alias:
        redirects.append((old_url(rel), alias))
for rel, alias in EXTRA.items():
    redirects.append((old_url(rel), alias))
for rel, a in ANCHORS.items():
    redirects.append((old_url(rel), a.split('#')[0]))
redirects.append(('/component/k2/item/7-doktor-vasilenko-elina', '/otzyvy'))
redirects.append(('/component/k2/item/8-irina', '/otzyvy'))
redirects = sorted(set(redirects))
with open(os.path.join(OUT, 'redirects.txt'), 'w', encoding='utf-8') as f:
    f.write('# 301-редиректы: старый адрес (Joomla) -> новый адрес (Tilda)\n# Tilda: Настройки сайта → Ещё → Редиректы (301)\n')
    for a, b in redirects:
        f.write(f'{a}\t{b}\n')
with open(os.path.join(OUT, 'seo-pages.txt'), 'w', encoding='utf-8') as f:
    for alias, name, t, dsc, kw in SEO:
        f.write(f'{alias}  (файл tilda/{name}.html)\n  Title: {t}\n  Description: {dsc}\n  Keywords: {kw}\n\n')
json.dump({'pages': [s[0] for s in SEO], 'images': len(IMAGES), 'redirects': len(redirects), 'report': REPORT,
           'reviews': len(REVIEWS), 'teachers': len(TEACHERS)}, sys.stdout, ensure_ascii=False, indent=1)
