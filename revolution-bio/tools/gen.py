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
# новый сайт строится заново; ссылки внутри старых текстов на старые страницы снимаются
PAGES = {}
EXTRA = {}
# заполняется при сборке отзывов/преподавателей: старый файл -> адрес с якорем
ANCHORS = {}

# страница со статьёй стороннего автора: переносим только вступление
INTRO_ONLY = {'news/item/21-news3.html'}

# Бренды компании: название, подпись, ссылка (строка брендов на первом экране главной)
BRANDS = [
    # название, подпись в карточке, ссылка, фото продукции (из старого сайта или source/), фото вписано в круг?
    ('JeuDérm', 'Пептидные технологии', '/jeuderm', 'source/round-jeuderm.webp', True),
    ('Rejusome', 'Экзосомальные технологии', '/rejusome', 'source/round-rejusome.webp', True),
    ('Calyra Lux\u00a05', 'Теломерная защита и долголетие', '/calyra-lux-5', 'source/round-calyra.webp', True),
    ('Crystal PDRN', 'Полинуклеотиды и регенерация', '/jeuderm?line=pdrn', 'source/round-pdrn.webp', True),
]
# Карточки направлений (готовые изображения с текстом): файл в source/, заголовок, подпись, ссылка.
# Заголовок и подпись повторяют текст на картинке — они идут в alt и для поиска.
PRODUCT_CARDS = [
    ('source/card-pdrn.webp', 'JeuDérm PDRN', 'Восстановление качества кожи. PDRN + HA 3%', '/jeuderm?line=pdrn'),
    ('source/card-serums.webp', 'Стерильные сыворотки', 'Rejusome Plus — готовый раствор, Rejusome — 20 мг + 5 мл', '/rejusome?type=serum'),
    ('source/card-calyra.webp', 'Теломерная защита', 'Calyra Lux 5: PN 2% и CAP Peptide 5', '/calyra-lux-5'),
    ('source/card-exo-care.webp', 'Экзосомный уход', 'Профессиональный и домашний уход Rejusome', '/rejusome?type=cosmetics'),
    ('source/card-trichology.webp', 'Трихология', 'Rejusome Plus + Crystal PDRN: решения для кожи головы и волос', '/rejusome?type=hair'),
    ('source/card-jeuderm.webp', 'Пептидная космецевтика JeuDérm', 'Всё, что нужно для кабинета косметолога', '/jeuderm'),
]
# «Шторки» линеек на странице JeuDérm: фото, цвет линейки, подпись, бренд · линейка, заголовок, текст, ссылка (фильтр каталога)
CATALOG_PANELS = [
    ('source/panel-reform.webp', '#cd555b', 'Возрастной уход', 'JeuDérm · Reform Age', 'Возрастной уход 30+',
     'Пептидный уход для упругости и плотности кожи — в кабинете и дома.', '/jeuderm?line=reformage'),
    ('source/panel-acno.webp', '#ab0a3d', 'Проблемная кожа', 'JeuDérm · Acno Active', 'Жирная и проблемная кожа',
     'Пептиды и кислоты против высыпаний и воспалений, для матовой и чистой кожи.', '/jeuderm?line=acno'),
    ('source/panel-ato.webp', '#76bc21', 'Чувствительная кожа', 'JeuDérm · Ato Care', 'Чувствительная и реактивная кожа',
     'Мягкий пептидный уход для кожи, склонной к раздражению и дерматитам.', '/jeuderm?line=atocare'),
    ('source/panel-hair.webp', '#ae57b9', 'Кожа головы', 'JeuDérm · Hair Genesis', 'Кожа головы и волосы',
     'Стерильный концентрат для процедур и пептидный спрей для дома — для роста и плотности волос.', '/jeuderm?line=hair'),
    ('source/panel-nova.webp', '#9aa3ab', 'Обновление', 'JeuDérm · Nova · Zymo', 'Обновление кожи',
     'Кислотные и энзимные системы обновления без агрессивного повреждения и долгой реабилитации.', '/jeuderm?line=novazymo'),
    ('source/panel-pro.webp', '#65666b', 'ПРО-уход', 'JeuDérm · ПРО', 'Средства для кабинета',
     'Маски, массажное масло, эксфолиант и дренажный гель — косметолог подбирает их под задачу процедуры.', '/jeuderm?line=pro'),
    ('source/panel-pdrn.webp', '#e0457b', 'Восстановление', 'JeuDérm · Crystal PDRN', 'PDRN + HA 3%',
     'Полинуклеотиды, факторы роста и пептиды — восстановление качества кожи, увлажнение и регенерация.', '/jeuderm?line=pdrn'),
]
# Круглые картинки-«пузыри» в шапке разделов и товаров: адрес страницы -> файл в source/
PAGE_ART = {
    '/jeuderm': ('source/round-jeuderm.webp', 'Пептидная космецевтика JeuDérm Expert'),
    '/rejusome': ('source/round-rejusome.webp', 'Rejusome Plus и Rejusome'),
    '/calyra-lux-5': ('source/round-calyra.webp', 'Calyra Lux 5'),
}
# Текст раскрытой карточки бренда на первом экране (по порядку BRANDS)
BRAND_DESC = [
    'Профессиональная пептидная космецевтика из Южной Кореи — всё, что нужно для кабинета косметолога.',
    'Стерильные сыворотки и экзосомальная космецевтика для глубокого восстановления кожи.',
    'PN 2% и CAP Пептид 5 в одном шприце — теломерная защита и долголетие кожи.',
    'PDRN + HA 3% — восстановление качества кожи, увлажнение и регенерация.',
]
# Линейные иконки (24×24) для «голограмм» на лице: пептиды, флакон, ДНК, щит
BRAND_ICON = [
    '<circle cx="6" cy="7" r="2.5"/><circle cx="18" cy="7" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M8.5 7h7M7.3 9.2l3.4 6.6M16.7 9.2l-3.4 6.6"/>',
    '<path d="M9 2.5h6M10 2.5v4L6.5 12v8a1.5 1.5 0 0 0 1.5 1.5h8a1.5 1.5 0 0 0 1.5-1.5v-8L14 6.5v-4M6.5 14h11"/>',
    '<path d="M7 2c0 5 10 5 10 10S7 17 7 22M17 2c0 5-10 5-10 10s10 5 10 10M8.5 5h7M8.5 19h7M10 9.5h4M10 14.5h4"/>',
    '<path d="M12 2.5l7.5 3v6c0 4.6-3.2 8.4-7.5 10-4.3-1.6-7.5-5.4-7.5-10v-6z"/><path d="M8.8 12l2.2 2.2 4.2-4.4"/>',
]
# Полоса преимуществ под первым экраном: иконка, крупно, мелко
TRUST = [
    ('<path d="M6 3h12l4 6-10 12L2 9z"/><path d="M2 9h20M9 3l3 6 3-6M12 21L9 9M12 21l3-12"/>', '100%', 'оригинальная продукция'),
    ('<path d="M6 2.5h9l5 5V21.5H6z"/><path d="M15 2.5v5h5M9 14.5l2 2 4-4"/>', '', 'Официальный дистрибьютор в России'),
    ('<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/>', '15 000', 'клиентов в нашей базе'),
    ('<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c0 1.2 2.7 3 6 3s6-1.8 6-3v-5M22 9v6"/>', '', 'Поддержка и обучение специалистов'),
]
# Кадры первого экрана главной: по одному на бренд.
# Файл в source/ (лица выровнены по размеру), номер бренда из BRANDS,
# точки на коже в процентах кадра (x, y): лоб, скула, подбородок, и три подписи к ним.
HERO_SLIDES = [
    ('source/face-a.webp', 0, [(55, 29), (36, 54), (58, 72)], ['Пептидные<br>технологии', 'Для всех<br>типов кожи', 'Клинические<br>исследования в Корее']),
    ('source/face-b.webp', 1, [(63, 28), (44, 53), (66, 70)], ['Экзосомальные<br>технологии', 'Стерильные сыворотки<br>и космецевтика', 'Улучшение<br>качества кожи']),
    ('source/face-c.webp', 2, [(56, 29), (36, 54), (58, 72)], ['Теломерная защита<br>и долголетие', 'PN и CAP<br>Пептид 5', 'Результат после<br>1 процедуры']),
    ('source/face-d.webp', 3, [(57, 29), (38, 54), (60, 72)], ['PDRN-<br>технологии', 'Полинуклеотиды<br>и факторы роста', 'Увлажнение<br>и регенерация']),
]
# упоминания бренда, который компания больше не продаёт
DROPPED = re.compile(r'mint\s*lift', re.I)

NAV = [('JeuDérm', '/jeuderm'), ('Rejusome', '/rejusome'), ('Calyra Lux 5', '/calyra-lux-5'),
       ('Косметологам', '/kosmetologam'), ('Пациентам', '/pacientam'), ('О компании', '/about'), ('Контакты', '/kontakty')]
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
        return '/product' if p.startswith('product') else '/jeuderm'
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
    # файлы, присланные отдельно (папка source/ рядом с tools/)
    own = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', src)
    path = os.path.normpath(own) if src.startswith('source/') else os.path.join(SRC, norm_rel(page_rel, src))
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
  background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .05 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"),radial-gradient(1200px 600px at 85% -10%,rgba(54,203,224,.10),transparent 60%),radial-gradient(900px 500px at -10% 40%,rgba(255,255,255,.04),transparent 60%),var(--bg);
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
#rb .rb-head .rb-wrap{display:flex;align-items:center;justify-content:space-between;gap:24px;min-height:88px}
#rb .rb-logo img{height:66px;width:auto}
#rb .rb-nav{display:flex;gap:2px;font-size:14.5px}
#rb .rb-nav a{text-decoration:none;padding:8px 11px;white-space:nowrap;border-radius:999px;color:var(--muted);transition:color .2s,background .2s}
#rb .rb-nav a:hover{color:#fff;background:var(--glass)}
#rb .rb-nav a[aria-current]{color:var(--accent);background:rgba(54,203,224,.1)}
#rb .rb-contact{display:flex;align-items:center;gap:18px}
#rb .rb-phone{font-family:var(--serif);font-size:18px;text-decoration:none;white-space:nowrap}
#rb .rb-phone:hover{color:var(--accent)}
#rb .rb-contact .rb-btn{padding:10px 22px;font-size:15px}
#rb .rb-burger{display:none;background:var(--glass);border:1px solid var(--line);border-radius:999px;color:#fff;padding:9px 18px;font:inherit;font-size:15px;cursor:pointer}
#rb .rb-mnav{display:none}
/* первый экран главной: бренды — лицо — текст */
#rb .rb-intro{position:relative;overflow:hidden;min-height:min(calc(100vh - 88px),820px);display:flex;align-items:center;padding:28px 0 44px}
#rb .rb-intro>.rb-wrap{position:relative;z-index:1;width:100%;display:grid;grid-template-columns:250px minmax(340px,440px) minmax(0,1fr);gap:clamp(24px,3.4vw,56px);align-items:center}
#rb .rb-intro__deco{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:0}
#rb .rb-intro__deco path{fill:none;stroke-width:1}
#rb .rb-intro__glow{position:absolute;z-index:0;left:50%;top:50%;width:min(70vw,900px);aspect-ratio:1;transform:translate(-50%,-50%);border-radius:50%;background:radial-gradient(closest-side,rgba(54,203,224,.12),transparent 70%);pointer-events:none}
/* бренды слева: карточки раскрываются как на сайте JeuDérm */
#rb .rb-bcol{display:flex;flex-direction:column;gap:12px;position:relative;z-index:3}
#rb .rb-brand{border-radius:16px;background:linear-gradient(145deg,rgba(255,255,255,.07),rgba(255,255,255,.02));border:1px solid var(--line);
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);transition:border-color .6s,box-shadow .6s,background .6s}
#rb .rb-brand__head{display:grid;grid-template-columns:56px minmax(0,1fr) 26px;gap:12px;align-items:center;width:100%;padding:10px 12px;border:0;background:none;color:inherit;font:inherit;text-align:left;cursor:pointer}
#rb .rb-brand__head img{width:56px;height:56px;object-fit:contain;filter:drop-shadow(0 6px 12px rgba(0,0,0,.45))}
#rb .rb-brand b{display:block;font-family:var(--serif);font-weight:400;font-size:19px;line-height:1.1;color:#fff;transition:color .6s}
#rb .rb-brand__head span{display:block;margin-top:5px;font-size:9.5px;font-weight:600;letter-spacing:.15em;text-transform:uppercase;color:var(--muted);line-height:1.5}
#rb .rb-brand__head i{width:26px;height:26px;border-radius:50%;border:1px solid var(--line);position:relative;transition:background .4s,border-color .4s}
#rb .rb-brand__head i::before,#rb .rb-brand__head i::after{content:"";position:absolute;left:50%;top:50%;width:10px;height:1.4px;background:var(--accent);transform:translate(-50%,-50%);transition:opacity .3s,background .3s}
#rb .rb-brand__head i::after{transform:translate(-50%,-50%) rotate(90deg)}
#rb .rb-brand__body{display:grid;grid-template-rows:0fr;transition:grid-template-rows .6s cubic-bezier(.2,.7,.2,1)}
#rb .rb-brand__body>div{overflow:hidden;min-height:0}
#rb .rb-brand__body p{margin:0;padding:0 14px 8px 80px;font-size:13px;line-height:1.5;color:var(--muted)}
#rb .rb-brand__body a{display:inline-block;margin:0 0 14px 80px;font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);text-decoration:none}
#rb .rb-brand__body a:hover{text-decoration:underline}
#rb .rb-brand:hover{border-color:rgba(54,203,224,.45)}
#rb .rb-brand.is-active{border-color:rgba(54,203,224,.7);background:linear-gradient(145deg,rgba(54,203,224,.15),rgba(255,255,255,.03));box-shadow:0 0 0 1px rgba(54,203,224,.2),0 18px 40px -22px rgba(54,203,224,.6)}
#rb .rb-brand.is-active b{color:var(--accent)}
#rb .rb-brand.is-active .rb-brand__body{grid-template-rows:1fr}
#rb .rb-brand.is-active .rb-brand__head i{background:var(--accent);border-color:var(--accent)}
#rb .rb-brand.is-active .rb-brand__head i::before{background:var(--accent-ink)}
#rb .rb-brand.is-active .rb-brand__head i::after{opacity:0}
/* пульсирующие точки на маске */
#rb .rb-pt{position:absolute;z-index:3;width:28px;height:28px;margin:-14px 0 0 -14px;padding:0;border:0;background:none;cursor:pointer;border-radius:50%}
#rb .rb-pt::before{content:"";position:absolute;left:50%;top:50%;width:7px;height:7px;margin:-3.5px 0 0 -3.5px;border-radius:50%;background:#dffbff;box-shadow:0 0 8px 2px var(--accent)}
#rb .rb-pt::after{content:"";position:absolute;left:50%;top:50%;width:7px;height:7px;margin:-3.5px 0 0 -3.5px;border-radius:50%;border:1px solid rgba(143,240,255,.8);animation:rb-ring 2.4s ease-out infinite}
#rb .rb-pt.is-active::before{background:#fff;box-shadow:0 0 12px 4px var(--accent)}
#rb .rb-pt.is-active::after{animation-duration:1.6s}
#rb .rb-pt:focus-visible{outline:1px solid var(--accent);outline-offset:2px}
@keyframes rb-ring{from{transform:scale(1);opacity:.9}to{transform:scale(3.4);opacity:0}}
/* «голограмма» у активной точки */
#rb .rb-holo{position:absolute;z-index:4;right:-3%;top:9%;width:min(220px,52%);padding:14px 16px 14px;border-radius:14px;pointer-events:none;
  background:linear-gradient(160deg,rgba(54,203,224,.18),rgba(18,28,34,.6));border:1px solid rgba(54,203,224,.5);
  backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);box-shadow:0 0 26px rgba(54,203,224,.22),inset 0 0 22px rgba(54,203,224,.08);
  opacity:0;transform:translateY(8px) scale(.98);transition:opacity .4s ease,transform .5s cubic-bezier(.2,.7,.2,1)}
#rb .rb-holo::after{content:"";position:absolute;inset:0;border-radius:inherit;background:repeating-linear-gradient(0deg,rgba(143,240,255,.07) 0 1px,transparent 1px 3px);pointer-events:none}
#rb .rb-holo.is-active{opacity:1;transform:none;transition-delay:.35s}
#rb.rb-js .rb-holo.is-active{animation:rb-flick .9s steps(1) .35s both}
@keyframes rb-flick{0%{opacity:0}12%{opacity:.7}20%{opacity:.2}32%{opacity:.9}40%{opacity:.5}52%,100%{opacity:1}}
#rb .rb-holo__top{display:flex;align-items:center;gap:10px;margin-bottom:8px}
#rb .rb-holo svg{flex:none;width:34px;height:34px;padding:7px;border-radius:50%;border:1px solid rgba(54,203,224,.55);fill:none;stroke:var(--accent);stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}
#rb .rb-holo b{font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;line-height:1.35;color:#fff}
#rb .rb-holo ul{margin:0;padding:0;list-style:none}
#rb .rb-holo li{position:relative;padding-left:12px;font-size:12.5px;line-height:1.45;color:rgba(214,235,240,.85)}
#rb .rb-holo li::before{content:"";position:absolute;left:0;top:.6em;width:4px;height:4px;border-radius:50%;background:var(--accent)}
#rb .rb-link__holo{stroke:rgba(143,240,255,.6);stroke-width:1;stroke-dasharray:3 3}
/* лицо по центру */
#rb .rb-stage{position:relative;width:100%;aspect-ratio:1122/1402;z-index:1}
#rb .rb-stage__img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;object-position:bottom;opacity:0;transition:opacity 1.4s ease;
  -webkit-mask-image:linear-gradient(180deg,transparent 0,#000 8%,#000 72%,transparent 97%),linear-gradient(90deg,transparent 0,#000 12%,#000 88%,transparent 100%);-webkit-mask-composite:source-in;
  mask-image:linear-gradient(180deg,transparent 0,#000 8%,#000 72%,transparent 97%),linear-gradient(90deg,transparent 0,#000 12%,#000 88%,transparent 100%);mask-composite:intersect}
#rb .rb-stage__img.is-active{opacity:1}
#rb .rb-stage__cap{position:absolute;z-index:2;left:-10%;right:-10%;bottom:5%;text-align:center;pointer-events:none;transition:opacity .5s ease}
#rb .rb-stage__cap.is-swap{opacity:0}
#rb .rb-stage__name{display:block;white-space:nowrap;font-family:var(--serif);font-size:clamp(30px,3.4vw,50px);line-height:1;letter-spacing:.08em;text-transform:uppercase;color:transparent;
  background:repeating-linear-gradient(180deg,rgba(214,221,226,.62) 0 1px,transparent 1px 4px);-webkit-background-clip:text;background-clip:text;-webkit-text-stroke:.6px rgba(214,221,226,.45)}
#rb .rb-stage__pts{display:none;margin-top:10px;font-size:10px;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:rgba(214,221,226,.7)}
#rb .rb-stage__dots{position:absolute;z-index:3;left:50%;bottom:-22px;transform:translateX(-50%);display:flex;gap:8px}
#rb .rb-stage__dots button{width:30px;height:18px;padding:0;border:0;background:none;cursor:pointer;position:relative}
#rb .rb-stage__dots button::before,#rb .rb-stage__dots button::after{content:"";position:absolute;left:0;top:8px;height:2px;border-radius:2px;background:rgba(255,255,255,.25);width:100%}
#rb .rb-stage__dots button::after{background:var(--accent);width:0}
#rb .rb-stage__dots button.is-done::after{width:100%}
#rb .rb-stage__dots button.is-active::after{animation:rb-prog var(--rb-int,6s) linear both}
#rb .rb-stage[data-paused] .rb-stage__dots button.is-active::after,#rb .rb-stage:not([data-playing]) .rb-stage__dots button.is-active::after{animation:none;width:100%}
@keyframes rb-prog{from{width:0}to{width:100%}}
/* светящиеся линии от карточек брендов к маске на лице */
#rb .rb-links{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:2;overflow:visible}
#rb .rb-links path{fill:none;stroke-linecap:round}
#rb .rb-link__base{stroke:rgba(54,203,224,.2);stroke-width:1;transition:stroke .6s}
#rb .rb-link__pulse{stroke:#8ff0ff;stroke-width:1.3;stroke-dasharray:7 101;stroke-dashoffset:108;opacity:.4;animation:rb-pulse 3.2s linear infinite;filter:drop-shadow(0 0 3px var(--accent))}
#rb .rb-link:nth-child(2) .rb-link__pulse{animation-delay:-.8s}#rb .rb-link:nth-child(3) .rb-link__pulse{animation-delay:-1.6s}#rb .rb-link:nth-child(4) .rb-link__pulse{animation-delay:-2.4s}
#rb .rb-link__x{stroke:#fff;stroke-width:1.1;opacity:.5;filter:drop-shadow(0 0 3px var(--accent));transition:opacity .6s}
#rb .rb-link.is-active .rb-link__base{stroke:rgba(54,203,224,.55)}
#rb .rb-link.is-active .rb-link__pulse{opacity:1;stroke-width:1.7;animation-duration:2.2s}
#rb .rb-link.is-active .rb-link__x{opacity:1}
#rb .rb-link__spark{stroke:#e9fdff;stroke-width:1.6;stroke-dasharray:1 4 3 6 1 3 2 84;opacity:0;filter:drop-shadow(0 0 4px #8ff0ff)}
#rb .rb-link.is-active .rb-link__spark{animation:rb-spark 1.1s linear infinite,rb-zap 2.2s steps(1) infinite}
@keyframes rb-spark{from{stroke-dashoffset:110}to{stroke-dashoffset:0}}
@keyframes rb-zap{0%{opacity:.95}8%{opacity:.2}14%{opacity:1}40%{opacity:.7}46%{opacity:0}60%{opacity:1}100%{opacity:.85}}
@keyframes rb-pulse{to{stroke-dashoffset:0}}
/* текст справа */
#rb .rb-intro__text{position:relative;z-index:3}
#rb .rb-intro h1{font-size:clamp(28px,2.9vw,44px);line-height:1.1;letter-spacing:.01em}
#rb .rb-intro__lead{font-size:17px;color:var(--muted);max-width:420px}
#rb .rb-intro .rb-btns{gap:12px}
#rb .rb-intro .rb-btn{padding:13px 24px}
/* полоса преимуществ */
#rb .rb-trust{position:relative;z-index:2;padding:0 0 24px}
#rb .rb-trust__bar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border-radius:20px;border:1px solid rgba(54,203,224,.28);
  background:linear-gradient(120deg,rgba(54,203,224,.1),rgba(255,255,255,.03) 40%,rgba(54,203,224,.08));box-shadow:inset 0 1px 0 rgba(255,255,255,.08)}
#rb .rb-trust__item{display:flex;align-items:center;gap:16px;padding:22px 24px;position:relative}
#rb .rb-trust__item+.rb-trust__item::before{content:"";position:absolute;left:0;top:22%;bottom:22%;width:1px;background:rgba(54,203,224,.25)}
#rb .rb-trust svg{flex:none;width:52px;height:52px;padding:13px;border-radius:50%;border:1px solid rgba(54,203,224,.45);box-shadow:0 0 18px rgba(54,203,224,.18);fill:none;stroke:var(--accent);stroke-width:1.3;stroke-linecap:round;stroke-linejoin:round}
#rb .rb-trust b{display:block;font-family:var(--serif);font-weight:400;font-size:26px;line-height:1;color:var(--accent);margin-bottom:4px}
#rb .rb-trust span{display:block;font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;line-height:1.5;color:rgba(214,235,240,.85)}
#rb .rb-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
/* заголовок внутренних страниц */
#rb .rb-hero{position:relative;padding:48px 0 20px;isolation:isolate}
#rb .rb-hero::before{content:"";position:absolute;inset:0 0 -120px;z-index:-1;background:url('""" + deco + """') center/cover no-repeat;opacity:.12;
  -webkit-mask-image:linear-gradient(180deg,#000 10%,transparent 100%);mask-image:linear-gradient(180deg,#000 10%,transparent 100%)}
#rb .rb-hero--art .rb-wrap{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,380px);gap:40px;align-items:center}
#rb .rb-hero__art{width:100%;aspect-ratio:1;object-fit:contain;filter:drop-shadow(0 20px 40px rgba(0,0,0,.45))}
#rb.rb-js .rb-hero__art{animation:rb-float 7s ease-in-out infinite}
@keyframes rb-float{50%{transform:translateY(-10px)}}
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
/* карточки-постеры направлений */
#rb .rb-pcard{display:flex;flex-direction:column;border-radius:20px;overflow:hidden;text-decoration:none;background:#1f2427;border:1px solid var(--line);scroll-snap-align:start;min-width:0;
  transition:transform .45s cubic-bezier(.2,.7,.2,1),border-color .4s,box-shadow .45s}
#rb .rb-pcard>img{display:block;width:100%;aspect-ratio:3/4;object-fit:cover;transition:transform .8s cubic-bezier(.2,.7,.2,1)}
#rb .rb-pcard__more{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;font-size:13px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);border-top:1px solid var(--line);transition:color .3s}
#rb .rb-pcard__more i{font-style:normal;font-size:16px;transition:transform .3s}
#rb .rb-pcard:hover{transform:translateY(-6px);border-color:rgba(54,203,224,.6);box-shadow:0 26px 50px -26px rgba(54,203,224,.5)}
#rb .rb-pcard:hover>img{transform:scale(1.03)}
#rb .rb-pcard:hover .rb-pcard__more{color:var(--accent)}
#rb .rb-pcard:hover .rb-pcard__more i{transform:translateX(4px)}
#rb .rb-pgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}
#rb .rb-railhead{display:flex;justify-content:space-between;align-items:flex-end;gap:20px}
#rb .rb-railnav{display:flex;gap:10px;margin-bottom:36px}
#rb .rb-railnav button{width:48px;height:48px;border-radius:50%;border:1px solid var(--line);background:var(--glass);color:#fff;font-size:18px;cursor:pointer;transition:background .3s,border-color .3s,color .3s}
#rb .rb-railnav button:hover{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
#rb .rb-rail{display:grid;grid-auto-flow:column;grid-auto-columns:calc((100% - 3*20px)/3.4);gap:20px;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;padding:6px 2px 14px;scrollbar-width:none;outline:none}
#rb .rb-rail::-webkit-scrollbar{display:none}
/* каталог товаров с фильтрами и окном (как на сайте JeuDérm) */
#rb .rb-filters{display:flex;flex-wrap:wrap;gap:14px 28px;margin-bottom:26px}
#rb .rb-filter{display:flex;flex-wrap:wrap;align-items:center;gap:10px}
#rb .rb-filter>span{font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
#rb .rb-filter>div{display:flex;flex-wrap:wrap;gap:6px}
#rb .rb-filter button{padding:8px 16px;border-radius:999px;border:1px solid var(--line);background:var(--glass);color:#fff;font:inherit;font-size:14px;cursor:pointer;transition:background .25s,border-color .25s,color .25s}
#rb .rb-filter button:hover{border-color:rgba(54,203,224,.6)}
#rb .rb-filter button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
#rb .rb-prods{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:20px}
#rb .rb-prod{display:flex;flex-direction:column;border-radius:18px;overflow:hidden;text-decoration:none;background:var(--glass);border:1px solid var(--line);transition:transform .4s cubic-bezier(.2,.7,.2,1),border-color .3s,box-shadow .4s;min-width:0}
#rb .rb-prod[hidden]{display:none}
#rb .rb-prod:hover{transform:translateY(-5px);border-color:rgba(54,203,224,.6);box-shadow:0 24px 48px -26px rgba(54,203,224,.5)}
#rb .rb-prod__ph{position:relative;display:block;aspect-ratio:1;background:radial-gradient(closest-side,rgba(54,203,224,.14),transparent),#22272b}
#rb .rb-prod__ph img{width:100%;height:100%;object-fit:contain;padding:8%;transition:transform .6s cubic-bezier(.2,.7,.2,1)}
#rb .rb-prod:hover .rb-prod__ph img{transform:scale(1.04)}
#rb .rb-prod__tags{position:absolute;left:12px;top:12px;display:flex;gap:6px}
#rb .rb-prod__tags span{padding:3px 9px;border-radius:999px;font-size:10px;font-weight:600;letter-spacing:.12em;background:rgba(43,48,53,.8);border:1px solid rgba(54,203,224,.4);color:var(--accent)}
#rb .rb-prod__bd{display:flex;flex-direction:column;gap:6px;padding:16px 18px 18px;flex:1}
#rb .rb-prod__en{font-size:11px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
#rb .rb-prod__bd b{font-family:var(--serif);font-weight:400;font-size:19px;line-height:1.2;color:#fff}
#rb .rb-prod__desc{font-size:14px;color:var(--muted)}
#rb .rb-prod__more{margin-top:auto;padding-top:8px;font-size:12px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
#rb .rb-cat__empty{color:var(--muted)}
#rb .rb-dlg{padding:0;border:1px solid rgba(54,203,224,.35);border-radius:22px;background:#252a2e;color:#fff;width:min(980px,calc(100vw - 32px));max-height:calc(100vh - 40px);box-shadow:0 40px 90px -30px rgba(0,0,0,.8)}
#rb .rb-dlg::backdrop{background:rgba(15,18,20,.72);backdrop-filter:blur(6px)}
#rb .rb-dlg[open]{animation:rb-dlg .45s cubic-bezier(.2,.7,.2,1)}
@keyframes rb-dlg{from{opacity:0;transform:translateY(16px) scale(.98)}}
#rb .rb-dlg__in{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr)}
#rb .rb-dlg__ph{background:radial-gradient(closest-side,rgba(54,203,224,.18),transparent),#1e2326;display:flex;align-items:center;justify-content:center;min-height:320px}
#rb .rb-dlg__ph img{width:100%;height:100%;max-height:560px;object-fit:contain;padding:8%}
#rb .rb-dlg__bd{position:relative;padding:34px 34px 30px;overflow:auto;max-height:calc(100vh - 42px)}
#rb .rb-dlg__bd h3{font-size:26px;margin:8px 40px 10px 0}
#rb .rb-dlg__x{position:absolute;top:16px;right:16px;width:40px;height:40px;border-radius:50%;border:1px solid var(--line);background:var(--glass);color:#fff;font-size:22px;line-height:1;cursor:pointer}
#rb .rb-dlg__x:hover{background:var(--accent);color:var(--accent-ink)}
#rb .rb-dlg__meta{font-size:12px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin-bottom:12px}
#rb .rb-dlg__desc{color:var(--muted)}
#rb .rb-dlg__dl{margin:18px 0 6px;border-top:1px solid var(--line)}
#rb .rb-dl{padding:14px 0;border-bottom:1px solid var(--line)}
#rb .rb-dl dt{font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin-bottom:6px}
#rb .rb-dl dd{margin:0;font-size:14.5px;color:rgba(255,255,255,.85)}
#rb .rb-dl dd p{margin:0 0 .6em}
#rb .rb-dl dd ul{margin:0;padding-left:1.1em}
#rb .rb-dl dd a{color:var(--accent)}
/* общие блоки страниц */
#rb .rb-feats{display:grid;gap:18px;grid-template-columns:repeat(4,minmax(0,1fr))}
#rb .rb-feats--3{grid-template-columns:repeat(3,minmax(0,1fr))}
#rb .rb-feats--2{grid-template-columns:repeat(2,minmax(0,1fr))}
#rb .rb-feat{padding:24px;border-radius:18px;background:var(--glass);border:1px solid var(--line)}
#rb .rb-feat svg{width:48px;height:48px;padding:12px;margin-bottom:16px;border-radius:50%;border:1px solid rgba(54,203,224,.45);fill:none;stroke:var(--accent);stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}
#rb .rb-feat b{display:block;font-family:var(--serif);font-weight:400;font-size:20px;line-height:1.2;margin-bottom:8px}
#rb .rb-feat b a{text-decoration:none}#rb .rb-feat b a:hover{color:var(--accent)}
#rb .rb-feat p{margin:0;font-size:14.5px;color:var(--muted)}
#rb .rb-stats.rb-stats--4{grid-template-columns:repeat(4,minmax(0,1fr))}
#rb .rb-rich a.rb-btn{color:#fff}#rb .rb-rich a.rb-btn--fill{color:var(--accent-ink)}
#rb .rb-split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:48px;align-items:start}
#rb .rb-split .rb-feats{grid-template-columns:repeat(2,minmax(0,1fr))}
#rb .rb-duo{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}
#rb .rb-tile{display:block;text-decoration:none;transition:border-color .3s,transform .4s}
#rb .rb-tile:hover{border-color:rgba(54,203,224,.6);transform:translateY(-4px)}
#rb .rb-tile h3{font-size:clamp(24px,2.4vw,32px)}
#rb .rb-steps{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;counter-reset:st}
#rb .rb-steps li{counter-increment:st;padding:24px;border-radius:18px;border:1px solid var(--line);background:var(--glass)}
#rb .rb-steps li::before{content:"0" counter(st);display:block;font-family:var(--serif);font-size:34px;line-height:1;color:var(--accent);margin-bottom:14px}
#rb .rb-steps b{display:block;font-family:var(--serif);font-weight:400;font-size:20px;margin-bottom:6px}
#rb .rb-steps p{margin:0;font-size:14.5px;color:var(--muted)}
#rb .rb-faq{max-width:900px;border-bottom:1px solid var(--line)}
#rb .rb-qa{border-top:1px solid var(--line)}
#rb .rb-qa summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:20px;padding:20px 0;font-family:var(--serif);font-size:19px}
#rb .rb-qa summary::-webkit-details-marker{display:none}
#rb .rb-qa summary i{flex:0 0 34px;height:34px;border-radius:50%;border:1px solid var(--line);position:relative;transition:background .3s,border-color .3s}
#rb .rb-qa summary i::before,#rb .rb-qa summary i::after{content:"";position:absolute;left:50%;top:50%;width:12px;height:1.4px;background:var(--accent);transform:translate(-50%,-50%)}
#rb .rb-qa summary i::after{transform:translate(-50%,-50%) rotate(90deg);transition:opacity .3s}
#rb .rb-qa[open] summary i{background:var(--accent);border-color:var(--accent)}
#rb .rb-qa[open] summary i::before{background:var(--accent-ink)}
#rb .rb-qa[open] summary i::after{opacity:0}
#rb .rb-qa__a{padding:0 50px 20px 0;color:var(--muted)}
#rb .rb-qa__a a{color:var(--accent)}
#rb .rb-cta{display:flex;justify-content:space-between;align-items:center;gap:30px;flex-wrap:wrap}
#rb .rb-cta h2{margin-bottom:8px}#rb .rb-cta p{margin:0}#rb .rb-cta .rb-btns{margin-top:0}
#rb .rb-events{display:flex;flex-direction:column;gap:14px}
#rb .rb-event{display:grid;grid-template-columns:96px minmax(0,1fr);gap:6px 18px;padding:20px;border-radius:18px;border:1px solid var(--line);background:var(--glass)}
#rb .rb-event__date{grid-row:span 2;font-family:var(--serif);font-size:22px;line-height:1.1;color:var(--accent)}
#rb .rb-event h3{font-size:19px;margin:0 0 6px}#rb .rb-event p{margin:0;font-size:14px}
#rb .rb-event .rb-btn{grid-column:2;justify-self:start;padding:9px 18px;font-size:14px;margin-top:8px}
#rb .rb-videos{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px}
#rb .rb-video{display:flex;flex-direction:column;gap:8px;padding:22px;border-radius:18px;border:1px solid var(--line);background:linear-gradient(160deg,rgba(54,203,224,.1),var(--glass));text-decoration:none;transition:border-color .3s,transform .4s}
#rb .rb-video:hover{border-color:rgba(54,203,224,.6);transform:translateY(-4px)}
#rb .rb-video__n{font-size:11px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
#rb .rb-video b{font-family:var(--serif);font-weight:400;font-size:19px;line-height:1.2}
#rb .rb-video p{margin:0;font-size:14px;color:var(--muted)}
#rb .rb-quote blockquote{margin:0 0 18px;font-family:var(--serif);font-size:clamp(20px,2vw,26px);line-height:1.45}
#rb .rb-letter{display:block;border-radius:18px;overflow:hidden;border:1px solid var(--line);background:#fff;max-width:420px;justify-self:center}
#rb .rb-warn{margin:0 0 30px;padding:14px 18px;border:1px solid var(--line);border-radius:14px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);text-align:center}
#rb .rb-404{padding:90px 0 120px}
/* каталог-«шторки» на главной */
#rb .rb-pans{display:flex;gap:8px;height:clamp(460px,44vw,600px)}
#rb .rb-pan{position:relative;flex:1 1 0;min-width:0;border-radius:18px;overflow:hidden;background:#1d2124;border:1px solid var(--line);transition:flex-grow .7s cubic-bezier(.2,.7,.2,1),border-color .5s}
#rb .rb-pan::before{content:"";position:absolute;z-index:3;left:0;top:0;width:34px;height:3px;background:var(--c)}
#rb .rb-pan>img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:grayscale(1) brightness(.62);transform:scale(1.04);transition:filter .7s,transform 1.2s cubic-bezier(.2,.7,.2,1)}
#rb .rb-pan::after{content:"";position:absolute;inset:0;z-index:1;background:linear-gradient(180deg,rgba(30,34,38,.15) 30%,rgba(30,34,38,.9));transition:background .6s}
#rb .rb-pan__tab{position:absolute;z-index:2;inset:0;width:100%;padding:0 0 26px;border:0;background:none;cursor:pointer;color:#fff;font:inherit;
  display:flex;align-items:flex-end;justify-content:center;font-size:12px;font-weight:600;letter-spacing:.18em;text-transform:uppercase;transition:opacity .4s}
#rb .rb-pan__tab:focus-visible{outline:2px solid var(--accent);outline-offset:-4px;border-radius:18px}
#rb .rb-pan:not(.is-active):hover>img{filter:grayscale(.4) brightness(.75)}
#rb .rb-pan__bd{position:absolute;z-index:2;left:0;right:0;bottom:0;padding:32px 34px;opacity:0;transform:translateY(16px);pointer-events:none;transition:opacity .4s,transform .5s cubic-bezier(.2,.7,.2,1)}
#rb .rb-pan__n{display:block;font-size:11px;font-weight:600;letter-spacing:.18em;text-transform:uppercase;color:var(--accent);margin-bottom:10px}
#rb .rb-pan__bd{text-shadow:0 1px 12px rgba(0,0,0,.45)}
#rb .rb-pan__bd h3{font-size:clamp(24px,2.3vw,34px);margin:0 0 10px;max-width:440px}
#rb .rb-pan__bd p{margin:0 0 18px;font-size:15px;color:rgba(255,255,255,.82);max-width:440px}
#rb .rb-pan__bd a{display:inline-flex;gap:10px;align-items:center;font-size:12px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;text-decoration:none;color:#fff}
#rb .rb-pan__bd a i{font-style:normal;transition:transform .3s}#rb .rb-pan__bd a:hover{color:var(--accent)}#rb .rb-pan__bd a:hover i{transform:translateX(4px)}
#rb .rb-pan.is-active{flex-grow:6;border-color:rgba(54,203,224,.6)}
#rb .rb-pan.is-active>img{filter:none;transform:none}
#rb .rb-pan.is-active::after{background:linear-gradient(180deg,transparent 30%,rgba(22,26,29,.78) 55%,rgba(22,26,29,.97) 80%)}
#rb .rb-pan.is-active .rb-pan__tab{opacity:0;pointer-events:none}
#rb .rb-pan.is-active .rb-pan__bd{opacity:1;transform:none;pointer-events:auto;transition-delay:.25s}
@media (min-width:901px){#rb .rb-pan__tab{writing-mode:vertical-rl;transform:rotate(180deg);align-items:center;justify-content:flex-start;padding:26px 0 0}}
@media (max-width:900px){#rb .rb-railhead{flex-direction:column;align-items:flex-start;gap:0}#rb .rb-railhead p{margin-bottom:24px!important}
  #rb .rb-pans{flex-direction:column;height:auto;gap:8px}
  #rb .rb-pan{flex:none;height:64px;transition:height .6s cubic-bezier(.2,.7,.2,1),border-color .5s}
  #rb .rb-pan.is-active{height:min(110vw,440px)}
  #rb .rb-pan__tab{align-items:center;justify-content:flex-start;padding:0 20px 0 54px;font-size:12px}
  #rb .rb-pan::before{top:50%;left:20px;width:18px;margin-top:-1px;transition:opacity .4s}
  #rb .rb-pan.is-active::before{top:0;left:0;width:34px;margin:0}
  #rb .rb-pan__bd{padding:22px 20px}}
/* товар */
#rb .rb-product{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:56px;align-items:start}
#rb .rb-product>div:first-child{position:sticky;top:96px}
#rb .rb-gal__main{background:radial-gradient(closest-side,rgba(54,203,224,.12),transparent),#22272b;border-radius:var(--r);aspect-ratio:1/1;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}
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
#rb.rb-js .rb-stage,#rb.rb-js .rb-bcol{animation:rb-fade 1.4s ease .1s both}
@keyframes rb-up{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}
@keyframes rb-fade{from{opacity:0;transform:scale(1.04)}to{opacity:1;transform:none}}
@media (max-width:1280px){#rb .rb-holo{right:1%;top:7%}}
@media (max-width:1100px){#rb .rb-feats,#rb .rb-steps,#rb .rb-videos,#rb .rb-stats.rb-stats--4{grid-template-columns:repeat(2,minmax(0,1fr))}#rb .rb-split{grid-template-columns:minmax(0,1fr)}}
@media (max-width:640px){#rb .rb-feats,#rb .rb-feats--3,#rb .rb-steps,#rb .rb-videos,#rb .rb-stats.rb-stats--4,#rb .rb-duo,#rb .rb-split .rb-feats{grid-template-columns:minmax(0,1fr)}
  #rb .rb-dlg__in{grid-template-columns:minmax(0,1fr)}#rb .rb-dlg__ph{min-height:0;max-height:38vh}#rb .rb-dlg__bd{padding:24px 20px;max-height:none}
  #rb .rb-dlg{max-height:calc(100vh - 20px);overflow:auto}#rb .rb-prods{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
  #rb .rb-prod__bd{padding:12px}#rb .rb-prod__bd b{font-size:16px}#rb .rb-prod__desc{display:none}#rb .rb-qa__a{padding-right:0}}
@media (max-width:1024px){
  #rb .rb-intro{min-height:0;padding:6px 0 40px}
  #rb .rb-intro>.rb-wrap{grid-template-columns:minmax(0,1fr);gap:34px}
  #rb .rb-stage{order:-2;width:min(86%,400px);justify-self:center}
  #rb .rb-intro__text{order:-1;text-align:center}#rb .rb-intro__text .rb-rule{margin-left:auto;margin-right:auto}
  #rb .rb-intro__lead{margin-left:auto;margin-right:auto}#rb .rb-intro .rb-btns{justify-content:center}
  #rb .rb-bcol{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  #rb .rb-links,#rb .rb-holo{display:none}
  #rb .rb-stage__pts{display:block}
  #rb .rb-trust__bar{grid-template-columns:repeat(2,minmax(0,1fr))}
  #rb .rb-trust__item:nth-child(3)::before{display:none}
  #rb .rb-stage__name{font-size:clamp(24px,7vw,36px)}#rb .rb-stage__pts{font-size:8.5px;letter-spacing:.12em}}
@media (max-width:520px){#rb .rb-bcol{grid-template-columns:minmax(0,1fr)}#rb .rb-stage__pts{font-size:8px;white-space:normal;max-width:84%;margin:8px auto 0;line-height:1.7}
  #rb .rb-trust__bar{grid-template-columns:minmax(0,1fr)}#rb .rb-trust__item+.rb-trust__item::before{left:22%;right:22%;top:0;bottom:auto;width:auto;height:1px}#rb .rb-trust__item{padding:16px 18px}}
@media (max-width:1100px){#rb .rb-pgrid{grid-template-columns:repeat(2,minmax(0,1fr))}#rb .rb-rail{grid-auto-columns:calc((100% - 20px)/2.3)}}
@media (max-width:1240px){#rb .rb-nav{display:none}#rb .rb-burger{display:inline-block}
  #rb .rb-mnav[data-open]{display:flex;flex-direction:column;padding:8px 24px 22px}
  #rb .rb-mnav a{padding:12px 0;text-decoration:none;font-size:18px;border-bottom:1px solid var(--line)}}
@media (max-width:900px){
  #rb .rb-rail{grid-auto-columns:78%;margin:0 -24px;padding:6px 24px 14px;scroll-padding:0 24px}
  #rb .rb-pgrid{grid-template-columns:minmax(0,1fr);gap:18px}#rb .rb-railnav{display:none}}
@media (max-width:820px){#rb{font-size:16px}
  #rb .rb-product,#rb .rb-contacts,#rb .rb-foot .rb-wrap,#rb .rb-hero--art .rb-wrap{grid-template-columns:minmax(0,1fr)}
  #rb .rb-hero__art{width:min(72%,300px);justify-self:center;order:-1}
  #rb .rb-product{gap:32px}#rb .rb-product>div:first-child{position:static}
  #rb .rb-row{grid-template-columns:minmax(0,1fr)}#rb .rb-row__body{padding:6px 12px 14px}
  #rb .rb-stats,#rb .rb-adv{grid-template-columns:minmax(0,1fr)}
  #rb .rb-reviews{grid-template-columns:minmax(0,1fr)}
  #rb .rb-review{padding:24px}
  #rb .rb-sec{padding:40px 0 64px}
  #rb .rb-phone{display:none}#rb .rb-logo img{height:52px}
  #rb .rb-head .rb-wrap{min-height:68px}#rb .rb-contact{gap:10px}#rb .rb-contact .rb-btn{padding:9px 16px;font-size:14px}}
@media (max-width:440px){#rb .rb-contact .rb-btn{display:none}}
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
<nav aria-label="Разделы">{links}<a href="/proizvoditel">Производитель</a><a href="/distributor">Стать дистрибьютором</a></nav>
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
var rm=matchMedia('(prefers-reduced-motion: reduce)').matches;
r.querySelectorAll('.rb-stage').forEach(function(st){
 var sec=st.closest('.rb-intro'),im=st.querySelectorAll('.rb-stage__img'),dt=st.querySelectorAll('.rb-stage__dots button'),cards=sec.querySelectorAll('.rb-brand'),
  svg=sec.querySelector('.rb-links'),links=svg?svg.querySelectorAll('.rb-link'):[],cap=st.querySelector('.rb-stage__cap'),pv=st.querySelectorAll('.rb-pt'),ho=st.querySelectorAll('.rb-holo'),hl=svg?svg.querySelector('.rb-link__holo'):null,n=im.length,i=0,t=null,ms=+st.getAttribute('data-interval')||6000;
 function pts(k){return (im[k].getAttribute('data-hs')||'').split(';').map(function(p){var c=p.split(',');return [+c[0],+c[1]];});}
 var cur=pts(0),from=cur,to=cur,t0=0,anim=0;
 function draw(){[].forEach.call(pv,function(b,k){if(cur[k]){b.style.left=cur[k][0]+'%';b.style.top=cur[k][1]+'%';}});
  if(!svg||!links.length||getComputedStyle(svg).display==='none')return;var sr=sec.getBoundingClientRect(),fr=st.getBoundingClientRect();
  svg.setAttribute('viewBox','0 0 '+sr.width+' '+sr.height);
  var bi=+im[i].getAttribute('data-brand'),ah=ho[bi];if(hl&&ah&&cur[bi]){var hr=ah.getBoundingClientRect(),px=fr.left-sr.left+cur[bi][0]/100*fr.width,py=fr.top-sr.top+cur[bi][1]/100*fr.height,hx=hr.left-sr.left,hy=hr.top-sr.top+22;hl.setAttribute('d','M'+px+' '+py+'L'+(px+(hx-px)*.55)+' '+hy+'H'+hx);}
  [].forEach.call(links,function(g,k){var c=cards[k]&&cards[k].querySelector('.rb-brand__head');if(!c||!cur[k])return;var cr=c.getBoundingClientRect(),sx=cr.right-sr.left,sy=cr.top+cr.height/2-sr.top,
   ex=fr.left-sr.left+cur[k][0]/100*fr.width,ey=fr.top-sr.top+cur[k][1]/100*fr.height,dx=(ex-sx)*.5,d='M'+sx+' '+sy+'C'+(sx+dx)+' '+sy+' '+(ex-dx)+' '+ey+' '+ex+' '+ey;
   g.querySelector('.rb-link__base').setAttribute('d',d);g.querySelector('.rb-link__pulse').setAttribute('d',d);g.querySelector('.rb-link__spark').setAttribute('d',d);});}
 function tween(ts){if(!t0)t0=ts;var p=Math.min(1,(ts-t0)/1200),e=p<.5?2*p*p:1-Math.pow(-2*p+2,2)/2;
  cur=to.map(function(q,k){var f=from[k]||q;return [f[0]+(q[0]-f[0])*e,f[1]+(q[1]-f[1])*e];});draw();if(p<1)anim=requestAnimationFrame(tween);}
 function show(k){i=(k+n)%n;
  [].forEach.call(im,function(e,j){e.classList.toggle('is-active',j===i);});
  var bi=im[i].getAttribute('data-brand');
  [].forEach.call(cards,function(e){var a=e.getAttribute('data-brand')===bi;e.classList.toggle('is-active',a);var h=e.querySelector('.rb-brand__head');if(h)h.setAttribute('aria-expanded',String(a));});
  [].forEach.call(pv,function(e){e.classList.toggle('is-active',e.getAttribute('data-brand')===bi);});
  [].forEach.call(ho,function(e){e.classList.toggle('is-active',e.getAttribute('data-brand')===bi);});
  [].forEach.call(links,function(e,j){e.classList.toggle('is-active',String(j)===bi);});
  if(cap){var nt=im[i].getAttribute('data-name'),pt=im[i].getAttribute('data-labels');cap.classList.add('is-swap');setTimeout(function(){cap.querySelector('.rb-stage__name').textContent=nt;cap.querySelector('.rb-stage__pts').textContent=pt;cap.classList.remove('is-swap');},rm?0:500);}
  [].forEach.call(dt,function(e,j){e.classList.toggle('is-active',j===i);e.classList.toggle('is-done',j<i);if(j===i)e.setAttribute('aria-current','true');else e.removeAttribute('aria-current');});
  from=cur;to=pts(i);cancelAnimationFrame(anim);t0=0;if(rm){cur=to;draw();setTimeout(draw,650);}else anim=requestAnimationFrame(tween);}
 function brand(b){for(var j=0;j<n;j++){if(im[j].getAttribute('data-brand')===b){if(j!==i)show(j);return;}}}
 function play(){stop();if(rm||n<2)return;st.setAttribute('data-playing','');st.style.setProperty('--rb-int',ms+'ms');t=setInterval(function(){show(i+1);},ms);}
 function stop(){if(t){clearInterval(t);t=null;}st.removeAttribute('data-playing');}
 [].forEach.call(dt,function(e,j){e.addEventListener('click',function(){show(j);play();});});
 [].forEach.call(cards,function(c){var b=c.getAttribute('data-brand'),h=c.querySelector('.rb-brand__head');
  c.addEventListener('mouseenter',function(){brand(b);stop();st.setAttribute('data-paused','');});
  c.addEventListener('mouseleave',function(){st.removeAttribute('data-paused');play();});
  if(h)h.addEventListener('click',function(){brand(b);play();});});
 [].forEach.call(pv,function(p){var b=p.getAttribute('data-brand');
  p.addEventListener('mouseenter',function(){brand(b);stop();st.setAttribute('data-paused','');});
  p.addEventListener('focus',function(){brand(b);stop();});p.addEventListener('click',function(){brand(b);play();});});
 st.addEventListener('mouseenter',function(){st.setAttribute('data-paused','');stop();});
 st.addEventListener('mouseleave',function(){st.removeAttribute('data-paused');play();});
 document.addEventListener('visibilitychange',function(){if(document.hidden)stop();else play();});
 draw();window.addEventListener('resize',draw);window.addEventListener('load',draw);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(draw);
 if('ResizeObserver' in window)new ResizeObserver(draw).observe(sec);
 play();
});
r.querySelectorAll('.rb-cat').forEach(function(cat){
 var cards=[].slice.call(cat.querySelectorAll('.rb-prod')),groups=[].slice.call(cat.querySelectorAll('.rb-filter')),dlg=cat.querySelector('.rb-dlg'),empty=cat.querySelector('.rb-cat__empty'),st={};
 var q=new URLSearchParams(location.search);
 function apply(){var n=0;cards.forEach(function(c){var ok=Object.keys(st).every(function(k){return st[k]==='all'||(c.getAttribute('data-'+k)||'').split(' ').indexOf(st[k])>-1;});c.hidden=!ok;if(ok)n++;});if(empty)empty.hidden=n>0;}
 function set(k,v,push){st[k]=v;groups.forEach(function(g){if(g.getAttribute('data-f')===k)[].forEach.call(g.querySelectorAll('button'),function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-v')===v));});});
  apply();if(push&&history.replaceState){var u=new URLSearchParams(location.search);if(v==='all')u.delete(k);else u.set(k,v);var qs=u.toString();history.replaceState(null,'',location.pathname+(qs?'?'+qs:'')+location.hash);}}
 groups.forEach(function(g){var k=g.getAttribute('data-f'),v=q.get(k);if(v&&!g.querySelector('[data-v="'+v+'"]'))v=null;set(k,v||'all',false);
  [].forEach.call(g.querySelectorAll('button'),function(b){b.addEventListener('click',function(){set(k,b.getAttribute('data-v'),true);});});});
 function open(c){if(!dlg||!c)return;var im=c.querySelector('.rb-prod__ph img'),di=dlg.querySelector('.rb-dlg__ph img');di.src=im.src;di.alt=im.alt;
  dlg.querySelector('.rb-prod__en').textContent=c.querySelector('.rb-prod__en').textContent;dlg.querySelector('h3').textContent=c.querySelector('.rb-prod__bd b').textContent;
  dlg.querySelector('.rb-dlg__desc').textContent=c.querySelector('.rb-prod__desc').textContent;var pd=c.querySelector('.rb-prod__pd');
  dlg.querySelector('.rb-dlg__meta').textContent=pd.querySelector('.rb-prod__meta').textContent;dlg.querySelector('.rb-dlg__dl').innerHTML=[].map.call(pd.querySelectorAll('.rb-dl'),function(x){return x.outerHTML;}).join('');
  if(!dlg.open){if(dlg.showModal)dlg.showModal();else dlg.setAttribute('open','');}dlg.querySelector('.rb-dlg__bd').scrollTop=0;
  if(history.replaceState)history.replaceState(null,'',location.pathname+location.search+'#p-'+c.getAttribute('data-id'));}
 function close(){if(dlg.open){if(dlg.close)dlg.close();else dlg.removeAttribute('open');}}
 if(dlg){dlg.addEventListener('close',function(){if(/^#p-/.test(location.hash)&&history.replaceState)history.replaceState(null,'',location.pathname+location.search);});
  dlg.querySelector('.rb-dlg__x').addEventListener('click',close);dlg.addEventListener('click',function(e){if(e.target===dlg)close();});
  [].forEach.call(dlg.querySelectorAll('[data-close]'),function(a){a.addEventListener('click',close);});}
 cards.forEach(function(c){c.addEventListener('click',function(e){e.preventDefault();open(c);});});
 function fromHash(){var m=location.hash.match(/^#p-([\\w-]+)/);if(!m)return;var c=cat.querySelector('.rb-prod[data-id="'+m[1]+'"]');if(c){if(c.hidden)groups.forEach(function(g){set(g.getAttribute('data-f'),'all',false);});c.scrollIntoView({block:'center'});open(c);}}
 fromHash();window.addEventListener('hashchange',fromHash);
});
r.querySelectorAll('.rb-pans').forEach(function(w){var ps=[].slice.call(w.querySelectorAll('.rb-pan'));
 function act(p){ps.forEach(function(x){var a=x===p;x.classList.toggle('is-active',a);x.querySelector('.rb-pan__tab').setAttribute('aria-expanded',String(a));});}
 [].forEach.call(w.querySelectorAll('[data-filter]'),function(a){a.addEventListener('click',function(e){var f=(a.getAttribute('data-filter')||'').split('='),cat=r.querySelector('.rb-cat');
  if(!cat||f.length<2)return;var b=cat.querySelector('.rb-filter[data-f="'+f[0]+'"] button[data-v="'+f[1]+'"]');if(!b)return;e.preventDefault();
  var all=cat.querySelectorAll('.rb-filter button[data-v="all"]');[].forEach.call(all,function(x){if(x!==b)x.click();});b.click();
  var k=r.querySelector('#katalog');if(k)k.scrollIntoView({behavior:rm?'auto':'smooth'});});});
 ps.forEach(function(p){var t=p.querySelector('.rb-pan__tab');t.addEventListener('click',function(){act(p);});
  if(matchMedia('(hover:hover) and (min-width:901px)').matches)p.addEventListener('mouseenter',function(){act(p);});});});
r.querySelectorAll('.rb-railnav button').forEach(function(bt){bt.addEventListener('click',function(){var sec=bt.closest('.rb-wrap'),rl=sec&&sec.querySelector('.rb-rail');if(!rl)return;var c=rl.querySelector('.rb-pcard');var w=c?c.getBoundingClientRect().width+20:rl.clientWidth*0.8;rl.scrollBy({left:w*(+bt.getAttribute('data-dir')),behavior:rm?'auto':'smooth'});});});
var h=r.querySelector('.rb-head');function sc(){if(!h)return;if(window.scrollY>10)h.setAttribute('data-scrolled','');else h.removeAttribute('data-scrolled');}
sc();window.addEventListener('scroll',sc,{passive:true});
if('IntersectionObserver' in window&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
 r.classList.add('rb-js');
 var els=r.querySelectorAll('.rb-sec h2,.rb-sec .rb-kicker,.rb-card,.rb-review,.rb-row,.rb-stats>div,.rb-adv figure,.rb-panel,.rb-gal,.rb-fields');
 var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('is-in');io.unobserve(e.target);}});},{rootMargin:'0px 0px -8% 0px'});
 els.forEach(function(el,k){el.classList.add('rb-reveal');el.style.transitionDelay=(k%4)*70+'ms';io.observe(el);});
}
})();
</script>'''

def crumbs(items):
    parts = ['<a href="/">Главная</a>'] + [f'<a href="{h}">{esc(t)}</a>' if h else esc(t) for t, h in items]
    return '<nav class="rb-crumbs" aria-label="Навигация">' + '<span>—</span>'.join(parts) + '</nav>'

def hero(h1, crumb_items, lead='', art=None):
    text_html = f'''{crumbs(crumb_items)}<h1>{esc(h1)}</h1><hr class="rb-rule">{f'<div class="rb-lead rb-rich">{lead}</div>' if lead else ''}'''
    if art:
        u = img('index.html', art[0], 900)
        return f'''<section class="rb-hero rb-hero--art"><div class="rb-wrap"><div>{text_html}</div><img class="rb-hero__art" src="{u}" alt="{esc(art[1])}"></div></section>'''
    return f'''<section class="rb-hero"><div class="rb-wrap">{text_html}</div></section>'''

def card(href, image, title, txt='', more='Подробнее', date='', cover=False):
    tag = 'a' if href else 'div'
    hr = f' href="{href}"' if href else ''
    im = f'<div class="rb-card__img{" rb-card__img--cover" if cover else ""}" style="background-image:url(\'{image}\')" role="img" aria-label="{esc(title)}"></div>' if image else ''
    return f'''<{tag} class="rb-card"{hr}>{im}<div class="rb-card__body">{f'<div class="rb-card__date">{esc(date)}</div>' if date else ''}<div class="rb-card__title">{esc(title)}</div>{f'<div class="rb-card__text">{esc(txt)}</div>' if txt else ''}{f'<span class="rb-card__more">{more} →</span>' if href and more else ''}</div></{tag}>'''

def panels(rel):
    items = ''
    for k, (f, col, short, brand, title, txt, href) in enumerate(CATALOG_PANELS):
        act = k == 0
        items += (f'<div class="rb-pan{" is-active" if act else ""}" style="--c:{col}">'
                  f'<img src="{img(rel, f, 1000)}" alt="" loading="lazy">'
                  f'<button class="rb-pan__tab" type="button" aria-expanded="{"true" if act else "false"}" aria-controls="rb-pan-{k}">{esc(short)}</button>'
                  f'<div class="rb-pan__bd" id="rb-pan-{k}"><span class="rb-pan__n">{k + 1:02d} · {esc(brand)}</span><h3>{esc(title)}</h3><p>{esc(txt)}</p>'
                  f'<a href="{href}#katalog" data-filter="{href.split("?")[1] if "?" in href else ""}">Смотреть средства <i aria-hidden="true">→</i></a></div></div>')
    return f'<div class="rb-pans">{items}</div>'

def pcard(rel, f, title, sub, href):
    ext = ' target="_blank" rel="noopener"' if href.startswith('http') else ''
    return (f'<a class="rb-pcard" href="{href}"{ext}><img src="{img(rel, f, 800)}" alt="{esc(title)}. {esc(sub)}" loading="lazy">'
            f'<span class="rb-pcard__more">Подробнее <i aria-hidden="true">→</i></span></a>')

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

# ---------------------------------------------------------------- данные товаров
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
JD_LINES = [  # линейки JeuDérm: ключ, название, подпись
    ('reformage', 'Reform Age', 'Возрастной уход 30+'),
    ('acno', 'Acno Active', 'Жирная и проблемная кожа'),
    ('atocare', 'Ato Care', 'Чувствительная кожа'),
    ('pro', 'ПРО-уход', 'Средства для процедур'),
    ('novazymo', 'Nova · Zymo', 'Обновление кожи'),
    ('hair', 'Hair Genesis', 'Кожа головы и волосы'),
    ('pdrn', 'Crystal PDRN', 'PDRN + HA 3%'),
]
RJ_TYPES = [('serum', 'Стерильные сыворотки'), ('cosmetics', 'Экзосомный уход'), ('hair', 'Трихология')]
CARE_LABEL = {'pro': 'ПРО', 'home': 'Дом'}


def jd_products():
    out = []
    for p in json.load(open(os.path.join(DATA, 'jeuderm-products.json'), encoding='utf-8')):
        out.append(dict(id=p['id'], en=p['en'], title=p['title'], desc=p['desc'], img=p['img'], alt=p.get('alt') or p['title'],
                        care=p['care'].split(), lines=p['lines'], vol=p.get('vol'), care_t=p.get('care_t'),
                        fields=[(k, esc(v)) for k, v in p['fields']]))
    return out


def old_product(rel, pid, en, title=None, **extra):
    """товар со старого сайта: короткое описание, «Состав», «Показания», полный текст, фото"""
    s = soup(rel)
    pp = s.select_one('.product-page')
    main = pp.select_one('.main-product-photo a.product-photo')
    photos = []
    for a in ([main] if main is not None else []) + pp.select('.main-product-photo .sigProLink[href]'):
        u = img(rel, a.get('href'), 1100)
        if u and u not in photos:
            photos.append(u)
    short = ' '.join(strip_tags(clean(rel, x)) for x in pp.select('.product-page-right > .product-page-description:not(:has(.itemFullText))'))
    fields = []
    for t in pp.select('.product-ex-title'):
        v = clean(rel, t.find_next_sibling(class_='product-ex-value'))
        if strip_tags(v):
            fields.append((text(t), v))
    full = clean(rel, pp.select_one('.product-page-right .itemFullText'))
    if strip_tags(full):
        fields.append(('Описание', full))
    h1 = title or title_of(s)
    d = dict(id=pid, en=en, title=h1, desc=shorten(short, 170), img=photos[0] if photos else None, alt=h1, photos=photos,
             care=['pro'], lines=[], vol=None, care_t=None, fields=fields, old=rel)
    d.update(extra)
    return d


def rj_products():
    """товары Rejusome (с сайта rejusome.com): data/rejusome-products.json"""
    out = []
    for p in json.load(open(os.path.join(DATA, 'rejusome-products.json'), encoding='utf-8')):
        fields = [(k, v) for k, v in p['fields']]
        fields.append(('Подробнее', f'<a href="{p["url"]}" target="_blank" rel="noopener">Описание, протоколы и результаты на rejusome.com →</a>'))
        out.append(dict(p, type=' '.join(p['type']), fields=fields))
    return out


def pdrn_product():
    d = old_product('product/item/59-crystal-pdrn.html', 'crystal-pdrn', 'Crystal PDRN + HA 3%', 'Crystal PDRN — восстановление качества кожи', lines=['pdrn'], vol='5 ампул × 5 мл')
    d['img'] = img('index.html', 'source/round-pdrn.webp', 1100)
    return d


CALYRA = dict(id='calyra-lux-5', en='Calyra Lux 5', title='CALYRA LUX 5 — CAP Пептид 5, PN и гиалуронат натрия в одном шприце',
              desc='Комплексная работа с качеством кожи: увлажнённость, плотность, ровный рельеф и сияние.',
              care=['pro'], lines=[], vol='2 шприца × 2,5 мл', care_t='Профессиональный уход',
              fields=[('Состав', 'CAP Пептид 5 (sh-Oligopeptide-104 SP) — 1000 ppm<br>Полинуклеотиды (PN) — 2%<br>Гиалуронат натрия — 1%'),
                      ('Действие', 'Пептид поддерживает клеточный потенциал кожи и процессы теломерной защиты, полинуклеотиды — её естественное обновление, гиалуронат натрия интенсивно увлажняет.'),
                      ('Протоколы', 'Радиочастотный лифтинг (RF), аппаратные процедуры, дермапен.'),
                      ('Производство', 'Корея, корейские и испанские биотехнологии, стандарты ISO · GMP.')])


# ---------------------------------------------------------------- каталог с фильтрами и окном товара
def product_card(p, attrs):
    tags = ''.join(f'<span>{CARE_LABEL[c]}</span>' for c in p['care'] if c in CARE_LABEL)
    meta = ' · '.join(x for x in (p.get('vol'), p.get('care_t')) if x)
    fields = ''.join(f'<div class="rb-dl"><dt>{esc(k)}</dt><dd>{v}</dd></div>' for k, v in p['fields'])
    return (f'<a class="rb-prod" href="#p-{p["id"]}" data-id="{p["id"]}" {attrs}>'
            f'<span class="rb-prod__ph"><img src="{p["img"]}" alt="{esc(p["alt"])}" loading="lazy"><span class="rb-prod__tags">{tags}</span></span>'
            f'<span class="rb-prod__bd"><span class="rb-prod__en">{esc(p["en"])}</span><b>{esc(p["title"])}</b><span class="rb-prod__desc">{esc(p["desc"])}</span><span class="rb-prod__more">Подробнее <i aria-hidden="true">→</i></span></span>'
            f'<span class="rb-prod__pd" hidden><span class="rb-prod__meta">{esc(meta)}</span>{fields}</span></a>')


def catalog(products, groups):
    """groups: [(ключ фильтра, подпись, [(значение, название)])]; у товара атрибут data-<ключ> со списком значений"""
    filt = ''
    for key, label, opts in groups:
        btns = f'<button type="button" data-v="all" aria-pressed="true">Все</button>' + ''.join(
            f'<button type="button" data-v="{v}" aria-pressed="false">{esc(n)}</button>' for v, n in opts)
        filt += f'<div class="rb-filter" role="group" aria-label="{esc(label)}" data-f="{key}"><span>{esc(label)}</span><div>{btns}</div></div>'
    def attrs(p):
        a = {'care': ' '.join(p['care']), 'line': ' '.join(p.get('lines', [])), 'type': p.get('type', '')}
        return ' '.join(f'data-{k}="{v}"' for k, v in a.items())
    cards = ''.join(product_card(p, attrs(p)) for p in products)
    return f'''<div class="rb-cat"><div class="rb-filters">{filt}</div><div class="rb-prods">{cards}</div>
<p class="rb-cat__empty" hidden>По этому сочетанию фильтров товаров нет — выберите другой вариант.</p>
<dialog class="rb-dlg" aria-labelledby="rb-dlg-t"><div class="rb-dlg__in"><div class="rb-dlg__ph"><img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" alt=""></div>
<div class="rb-dlg__bd"><button class="rb-dlg__x" type="button" aria-label="Закрыть">×</button><span class="rb-prod__en"></span><h3 id="rb-dlg-t"></h3><div class="rb-dlg__meta"></div><p class="rb-dlg__desc"></p><dl class="rb-dlg__dl"></dl>
<div class="rb-btns"><a class="rb-btn rb-btn--fill" href="#popup:price" data-close>Узнать цену</a><a class="rb-btn" href="#popup:feedback" data-close>Задать вопрос</a></div></div></div></dialog></div>'''


# ---------------------------------------------------------------- общие блоки
def section(kicker, h2, inner, cls=''):
    return f'<section class="rb-sec {cls}"><div class="rb-wrap">{f"<span class=\"rb-kicker\">{esc(kicker)}</span>" if kicker else ""}<h2>{h2}</h2><hr class="rb-rule">{inner}</div></section>'


def feats(items, cols=4):
    """карточки-преимущества: (иконка svg или '', заголовок, текст)"""
    return f'<div class="rb-feats rb-feats--{cols}">' + ''.join(
        f'<div class="rb-feat">{f"<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\">{ic}</svg>" if ic else ""}<b>{t}</b><p>{x}</p></div>' for ic, t, x in items) + '</div>'


def steps(items):
    return '<ol class="rb-steps">' + ''.join(f'<li><b>{esc(t)}</b><p>{x}</p></li>' for t, x in items) + '</ol>'


def faq(items):
    return '<div class="rb-faq">' + ''.join(f'<details class="rb-qa"{" open" if k == 0 else ""}><summary>{esc(q)}<i aria-hidden="true"></i></summary><div class="rb-qa__a">{a}</div></details>' for k, (q, a) in enumerate(items)) + '</div>'


def cta(title, text_, btn='Узнать цену', href='#popup:price', btn2=None):
    b2 = f'<a class="rb-btn" href="{btn2[1]}">{btn2[0]}</a>' if btn2 else ''
    return f'<section class="rb-sec"><div class="rb-wrap"><div class="rb-panel rb-cta"><div><h2>{title}</h2><p class="rb-muted">{text_}</p></div><div class="rb-btns"><a class="rb-btn rb-btn--fill" href="{href}">{btn}</a>{b2}</div></div></div></section>'


def stats(items):
    return '<div class="rb-stats rb-stats--4">' + ''.join(f'<div><div class="rb-stat__num">{n}</div><div class="rb-stat__txt">{t}</div></div>' for n, t in items) + '</div>'


ICON = {
    'gift': '<path d="M3 9h18v4H3zM5 13v8h14v-8M12 9v12M12 9c-1.5-3-5-4-5.5-2S9 9 12 9zm0 0c1.5-3 5-4 5.5-2S15 9 12 9z"/>',
    'stairs': '<path d="M3 20h5v-5h5v-5h5V5h3M3 20v1M21 5V4"/>',
    'play': '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M10 9.5v5l4.5-2.5z"/>',
    'users': '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-5.5 6.5-5.5s6.5 1.9 6.5 5.5M16 4.8a3.5 3.5 0 0 1 0 6.4M18.5 14.8c2 .6 3 2.3 3 5.2"/>',
    'doc': '<path d="M6 2.5h9l5 5V21.5H6z"/><path d="M15 2.5v5h5M9 13h7M9 17h5"/>',
    'chat': '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9.5h8M8 12.5h5"/>',
    'truck': '<path d="M2 6h12v10H2zM14 9h4l4 4v3h-8"/><circle cx="6.5" cy="17.5" r="2"/><circle cx="17.5" cy="17.5" r="2"/>',
    'shield': BRAND_ICON[3],
    'flask': '<path d="M9 2.5h6M10 2.5v6L4.5 19a1.8 1.8 0 0 0 1.6 2.5h11.8a1.8 1.8 0 0 0 1.6-2.5L14 8.5v-6M7 14h10"/>',
    'globe': '<circle cx="12" cy="12" r="9.5"/><path d="M2.5 12h19M12 2.5c2.8 3 2.8 16 0 19M12 2.5c-2.8 3-2.8 16 0 19"/>',
    'star': '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
    'heart': '<path d="M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.4 4.3 4.3 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10z"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/>',
}
WEBINARS = [  # записи на Рутубе (из раздела «Обучение» сайта JeuDérm)
    ('Обновляющая система Нова Комплекс', 'Механизм действия, показания и ограничения, выбор пациента и ключевые этапы процедуры.', 'd7302347806e412731e8452d92509b13'),
    ('Обновляющая система Зимо Комплекс', 'Действие Zymo, протокол и нюансы для разного возраста и типа кожи, включая чувствительную.', 'c266156ecd63023ff5dcac2c25901baf'),
    ('Пептидные решения для здоровья и молодости кожи', 'Для специалистов, которые хотят расширить арсенал проверенными препаратами.', 'be7dc7a49613fefc73a1bb21cc9b99ec'),
    ('Ангельское совершенство кожи', 'Система мягкого молекулярного обновления: гладкость, ровный тон и сияние без раздражения.', 'ecc180120e27f8f7743990dc621770f4'),
]
RUTUBE = 'https://rutube.ru/channel/42947212/'
UPCOMING = [  # ближайшие вебинары — обновляйте список
    ('10 ноября', 'Пилинг без перегрузки: контролируемое обновление кожи с JeuDérm',
     'Практический вебинар о Molecular Exfoliate: грамотные сочетания, частые ошибки и домашнее сопровождение клиента.'),
    ('24 ноября', 'Calyra Lux 5: знакомство с новинкой',
     'Концепция и ключевые компоненты продукта, чем он отличается от привычных решений и как включить его в практику.'),
]
WARN = '<p class="rb-warn">Имеются противопоказания. Перед применением необходима консультация специалиста.</p>'


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


# ---------------------------------------------------------------- страницы
def build_home():
    rel = 'index.html'
    s = soup(rel)
    rail = ''.join(pcard(rel, *c) for c in PRODUCT_CARDS)
    slides = [(img(rel, f, 1100), BRANDS[bi][0], pts, BRANDS[bi][2], bi, labels) for f, bi, pts, labels in HERO_SLIDES]
    ext = lambda h: ' target="_blank" rel="noopener"' if h.startswith('http') else ''
    def mask_pts(p):
        (fx, fy), (cx, cy), (hx, hy) = p
        return [(fx, fy), (cx, cy), (round((cx + hx) / 2) - 3, round((cy + hy) / 2) + 1), (hx, hy)]
    hs_attr = lambda p: ';'.join(f'{x},{y}' for x, y in mask_pts(p))
    plain = lambda labels: ' · '.join(strip_tags(l.replace('<br>', ' ')) for l in labels)
    imgs_html = ''.join(f'<img class="rb-stage__img{" is-active" if k == 0 else ""}" src="{u}" alt="{"Сияющая ухоженная кожа" if k == 0 else ""}" data-brand="{bi}" data-hs="{hs_attr(p)}" data-labels="{esc(plain(labels))}" data-name="{esc(b)}"{" fetchpriority=\"high\"" if k == 0 else " loading=\"lazy\" decoding=\"async\""}>' for k, (u, b, p, h, bi, labels) in enumerate(slides))
    sr_text = ' '.join(f'{b}: {plain(labels)}.' for u, b, p, h, bi, labels in slides)
    dots_html = ''.join(f'<button type="button" aria-label="Кадр {k + 1}: {esc(b)}"{" class=\"is-active\" aria-current=\"true\"" if k == 0 else ""}></button>' for k, (u, b, p, h, bi, labels) in enumerate(slides))
    first = slides[0][4]
    def bcard(k, n, t, h, photo, rnd):
        act = k == first
        return (f'<div class="rb-brand{" is-active" if act else ""}" data-brand="{k}">'
                f'<button class="rb-brand__head" type="button" aria-expanded="{"true" if act else "false"}" aria-controls="rb-brand-{k}"><img src="{img(rel, photo, 300)}" alt="" loading="lazy">'
                f'<div><b>{esc(n)}</b><span>{esc(t)}</span></div><i aria-hidden="true"></i></button>'
                f'<div class="rb-brand__body" id="rb-brand-{k}"><div><p>{esc(BRAND_DESC[k])}</p><a href="{h}"{ext(h)}>Подробнее →</a></div></div></div>')
    labels_of = {bi: labels for f, bi, p, labels in HERO_SLIDES}
    def holo_items(k):
        items = [strip_tags(l.replace('<br>', ' ')) for l in labels_of.get(k, [])]
        return [t for t in items if t.lower() != BRANDS[k][1].lower()]
    holos = ''.join(f'<div class="rb-holo{" is-active" if k == first else ""}" data-brand="{k}" aria-hidden="true"><div class="rb-holo__top"><svg viewBox="0 0 24 24">{BRAND_ICON[k]}</svg><b>{esc(BRANDS[k][1])}</b></div>'
                    f'<ul>{"".join(f"<li>{esc(t)}</li>" for t in holo_items(k))}</ul></div>' for k in range(len(BRANDS)))
    pts_html = ''.join(f'<button class="rb-pt{" is-active" if k == first else ""}" type="button" data-brand="{k}" aria-label="{esc(BRANDS[k][0].replace(chr(160), " "))}"></button>' for k in range(len(BRANDS)))
    trust_html = '<section class="rb-trust"><div class="rb-wrap"><div class="rb-trust__bar">' + ''.join(
        f'<div class="rb-trust__item"><svg viewBox="0 0 24 24" aria-hidden="true">{ic}</svg><div>{f"<b>{esc(big)}</b>" if big else ""}<span>{esc(small)}</span></div></div>' for ic, big, small in TRUST) + '</div></div></section>'
    brands_html = ''.join(bcard(k, *b) for k, b in enumerate(BRANDS))
    links_svg = '<svg class="rb-links" aria-hidden="true">' + ''.join(
        f'<g class="rb-link{" is-active" if k == first else ""}"><path class="rb-link__base"/><path class="rb-link__pulse" pathLength="100"/><path class="rb-link__spark" pathLength="100"/></g>' for k in range(len(BRANDS))) + '<path class="rb-link__holo"/></svg>'
    deco_svg = ('<svg class="rb-intro__deco" viewBox="0 0 1440 900" preserveAspectRatio="none" aria-hidden="true">'
                '<path d="M-40 780 C 380 660, 620 900, 980 720 S 1380 440, 1500 540" stroke="rgba(255,255,255,.06)"/>'
                '<path d="M760 -40 C 820 240, 1060 340, 1220 290 S 1440 170, 1500 230" stroke="rgba(255,255,255,.05)"/></svg>')
    cosmo = feats([(ICON['gift'], '−15% на первый заказ', 'Стартовая скидка для новых специалистов и клиник.'),
                   (ICON['stairs'], 'Накопительная система', 'Чем больше закупок — тем выгоднее условия.'),
                   (ICON['play'], 'Вебинары 2 раза в месяц', 'По вторникам: протоколы, сочетания, новинки.'),
                   (ICON['users'], 'Обучение и протоколы', 'Индивидуально и в группах, материалы для кабинета.')])
    body = f'''<section class="rb-intro">{deco_svg}<div class="rb-intro__glow"></div>{links_svg}<div class="rb-wrap">
<nav class="rb-bcol" aria-label="Наши бренды">{brands_html}</nav>
<div class="rb-stage" role="region" aria-roledescription="слайдер" aria-label="Бренды Революшн Био" data-interval="6000">{imgs_html}{pts_html}{holos}
<div class="rb-stage__cap" aria-hidden="true"><span class="rb-stage__name">{esc(slides[0][1])}</span><span class="rb-stage__pts">{esc(plain(slides[0][5]))}</span></div>
<p class="rb-sr">{esc(sr_text)}</p><div class="rb-stage__dots">{dots_html}</div></div>
<div class="rb-intro__text"><span class="rb-kicker">Революшн Био</span>
<h1>Инновационные решения для косметологов</h1><hr class="rb-rule">
<p class="rb-intro__lead">Официальный дистрибьютор препаратов для косметологов JeuDérm, Rejusome, Calyra Lux&nbsp;5 и&nbsp;Crystal&nbsp;PDRN в&nbsp;России.</p>
<div class="rb-btns"><a class="rb-btn rb-btn--fill" href="#popup:price">Узнать цену</a><a class="rb-btn" href="#katalog">Каталог продукции</a></div>
</div></div></section>
{trust_html}
<section class="rb-sec" id="katalog"><div class="rb-wrap"><div class="rb-railhead"><div><span class="rb-kicker">Каталог</span><h2>Продукция</h2><hr class="rb-rule"></div>
<div class="rb-railnav"><button type="button" data-dir="-1" aria-label="Назад">←</button><button type="button" data-dir="1" aria-label="Вперёд">→</button></div></div>
<div class="rb-rail" tabindex="0" aria-label="Направления продукции">{rail}</div></div></section>
<section class="rb-sec"><div class="rb-wrap"><div class="rb-split"><div><span class="rb-kicker">Для косметологов</span><h2>Работайте с официальным дистрибьютором</h2><hr class="rb-rule">
<p class="rb-lead">Оригинальная продукция с документами, обучение и поддержка менеджера. Цены — после заявки: менеджер свяжется с вами и подберёт условия.</p>
<div class="rb-btns"><a class="rb-btn rb-btn--fill" href="/kosmetologam">Косметологам</a><a class="rb-btn" href="#popup:price">Узнать цену</a></div></div>{cosmo}</div></div></section>
<section class="rb-sec"><div class="rb-wrap"><div class="rb-duo">
<a class="rb-panel rb-tile" href="/pacientam"><span class="rb-kicker">Пациентам</span><h3>Как работают процедуры и где их пройти</h3><p class="rb-muted">Что дают препараты JeuDérm, Rejusome и Calyra Lux&nbsp;5, как подготовиться к процедуре и ухаживать за кожей после.</p><span class="rb-card__more">Подробнее →</span></a>
<a class="rb-panel rb-tile" href="/distributor"><span class="rb-kicker">Партнёрам</span><h3>Стать дистрибьютором в вашем регионе</h3><p class="rb-muted">Прямые поставки, обучение команды, маркетинговые материалы и персональный менеджер.</p><span class="rb-card__more">Узнать условия →</span></a>
</div></div></section>
<section class="rb-sec"><div class="rb-wrap"><div class="rb-panel"><span class="rb-kicker">О компании</span><h2>Революшн Био</h2><hr class="rb-rule">
<p class="rb-lead">Официальный дистрибьютор южнокорейского производителя VIRTA-MED KOREA в России: поставки, логистика, обучение специалистов и маркетинговая поддержка — напрямую от производителя, без посредников.</p>
{stats(ABOUT_STATS)}<div class="rb-btns"><a class="rb-btn" href="/about">О компании</a><a class="rb-btn" href="/proizvoditel">О производителе</a></div></div></div></section>
{contacts_section(rel, s, h='h2')}{WARN_SEC}'''
    page('/', 'Главная', body, {'title': 'Революшн Био — инновационные препараты для косметологов',
                                 'description': 'Официальный дистрибьютор JeuDérm, Rejusome, Calyra Lux 5 и Crystal PDRN в России. Оригинальная продукция, обучение и поддержка косметологов.',
                                 'keywords': meta(s, 'keywords')})


def build_jeuderm(products):
    lines = [(k, n) for k, n, _ in JD_LINES]
    intro = ('<p>Южнокорейская профессиональная космецевтика на пептидах и пробиотиках. Эффективность формул подтверждена исследованиями '
             'в Дерматологическом центре Национального университета Чунгнам и в Университете Ханнам.</p>')
    body = hero('JeuDérm', [('JeuDérm', None)], intro, art=PAGE_ART.get('/jeuderm')) + f'''
<section class="rb-sec" style="padding-top:0"><div class="rb-wrap">{stats([('50 000+', 'процедур в клиниках и центрах'), ('20+', 'стран, где работают с брендом'), ('6', 'направлений ухода — ПРО и домашний'), ('ISO · GMP', 'стандарты производства')])}</div></section>
<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><span class="rb-kicker">Линейки</span><h2>Уход по задачам кожи</h2><hr class="rb-rule">{panels('index.html')}</div></section>
<section class="rb-sec" id="katalog" style="padding-top:0"><div class="rb-wrap"><span class="rb-kicker">Каталог</span><h2>Продукция JeuDérm</h2><hr class="rb-rule">
<p class="rb-muted" style="margin-bottom:28px">Выберите уход для кабинета или дома и линейку под задачу кожи. Нажмите на товар, чтобы открыть состав и применение.</p>
{catalog(products, [('care', 'Уход', [('pro', 'Профессиональный'), ('home', 'Домашний')]), ('line', 'Линейка', lines)])}</div></section>
{cta('Цены и протоколы — по запросу', 'Оставьте заявку: менеджер пришлёт прайс для специалистов и протоколы процедур.', btn2=('Официальный сайт JeuDérm', 'https://jeuderm-russia.ru/'))}{WARN_SEC}'''
    page('/jeuderm', 'JeuDérm', body, {'title': 'JeuDérm — пептидная космецевтика из Кореи для косметологов | Революшн Био',
                                       'description': 'Профессиональный и домашний уход JeuDérm: Reform Age, Acno Active, Ato Care, Nova·Zymo, Hair Genesis, Crystal PDRN. Официальный дистрибьютор в России.',
                                       'keywords': 'JeuDérm, ЖеДерм, пептидная космецевтика, профессиональная косметика, Корея, Crystal PDRN'})


def build_rejusome(products):
    s = soup('product/itemlist/category/5-ekzosomy.html')
    desc = clean('product/itemlist/category/5-ekzosomy.html', s.select_one('.products-subcategory-description'))
    intro = '<p>Стерильные сыворотки и космецевтика с экзосомами для глубокого восстановления и обновления кожи — в кабинете и дома.</p>'
    body = hero('Rejusome', [('Rejusome', None)], intro, art=PAGE_ART.get('/rejusome')) + f'''
<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><span class="rb-kicker">Каталог</span><h2>Продукция Rejusome</h2><hr class="rb-rule">
{catalog(products, [('type', 'Направление', RJ_TYPES)])}</div></section>
{section('Технология', 'Что такое экзосомы', f'<div class="rb-rich">{desc}</div>') if strip_tags(desc) else ''}
{cta('Цены — по запросу', 'Оставьте заявку: менеджер пришлёт прайс и расскажет о протоколах.', btn2=('Сайт Rejusome', 'https://rejusome.com/'))}{WARN_SEC}'''
    page('/rejusome', 'Rejusome', body, {'title': 'Rejusome — стерильные сыворотки и космецевтика с экзосомами | Революшн Био',
                                         'description': 'Rejusome, Rejusome Plus и линейка Exo Boost: экзосомы для восстановления кожи и волос. Официальный дистрибьютор в России.',
                                         'keywords': 'Rejusome, Реджусом, экзосомы, сыворотка с экзосомами, Exo Boost'})


def build_calyra():
    p = dict(CALYRA, img=img('index.html', 'source/round-calyra.webp', 1100), alt='Calyra Lux 5')
    body = hero('Calyra Lux 5', [('Calyra Lux 5', None)], '<p>Новая эра долголетия кожи: CAP Пептид 5, полинуклеотиды (PN) и гиалуронат натрия в одном шприце.</p>', art=PAGE_ART.get('/calyra-lux-5')) + f'''
<section class="rb-sec" style="padding-top:0"><div class="rb-wrap">{stats([('1000 ppm', 'CAP Пептид 5 · клеточный потенциал'), ('2%', 'полинуклеотиды (PN) · обновление'), ('1%', 'гиалуронат натрия · увлажнение'), ('3 в 1', 'три актива в одном шприце')])}</div></section>
<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><div class="rb-split"><img class="rb-hero__art" src="{p['img']}" alt="Calyra Lux 5" loading="lazy">
<div><span class="rb-kicker">Продукт</span><h2>{esc(p['title'])}</h2><hr class="rb-rule"><p class="rb-dlg__meta">{esc(p['vol'])} · {esc(p['care_t'])}</p><p class="rb-muted">{esc(p['desc'])}</p>
<dl class="rb-dlg__dl">{''.join(f'<div class="rb-dl"><dt>{esc(k)}</dt><dd>{v}</dd></div>' for k, v in p['fields'])}</dl><div class="rb-btns"><a class="rb-btn rb-btn--fill" href="#popup:price">Узнать цену</a></div></div></div></div></section>
{section('Почему это новинка', 'Работа на качество и ресурс кожи', feats([
        (BRAND_ICON[2], 'Теломерная защита', 'Запатентованный CAP Пептид 5 поддерживает клеточный потенциал и процессы теломерной защиты.'),
        (BRAND_ICON[0], 'Обновление', 'Полинуклеотиды поддерживают естественное обновление кожи.'),
        (ICON['flask'], 'Увлажнение', 'Гиалуронат натрия интенсивно увлажняет и поддерживает защитные функции.'),
        (ICON['star'], '3 протокола', 'Радиочастотный лифтинг, аппаратные процедуры, дермапен.')]))}
{cta('Узнать цену и записаться на обучение', 'Подробно о составе, технологии и протоколах — на официальном сайте Calyra Lux 5.', btn2=('Сайт Calyra Lux 5', 'https://calyralux.ru/'))}{WARN_SEC}'''
    page('/calyra-lux-5', 'Calyra Lux 5', body, {'title': 'Calyra Lux 5 — CAP Пептид 5, PN и гиалуронат натрия | Революшн Био',
                                                 'description': 'CALYRA LUX 5: теломерная защита и долголетие кожи. CAP Пептид 5 1000 ppm, PN 2%, гиалуронат натрия 1% в одном шприце.',
                                                 'keywords': 'Calyra Lux 5, Калюра Люкс 5, CAP Пептид 5, полинуклеотиды, долголетие кожи'})


def build_kosmetologam():
    up = ''.join(f'<article class="rb-event"><span class="rb-event__date">{esc(d)}</span><div><h3>{esc(t)}</h3><p class="rb-muted">{esc(x)}</p></div><a class="rb-btn" href="#popup:signup">Записаться</a></article>' for d, t, x in UPCOMING)
    vids = ''.join(f'<a class="rb-video" href="https://rutube.ru/video/{v}/" target="_blank" rel="noopener"><span class="rb-video__n">Вебинар {k + 1:02d}</span><b>{esc(t)}</b><p>{esc(x)}</p><span class="rb-card__more">Смотреть на Рутубе →</span></a>' for k, (t, x, v) in enumerate(WEBINARS))
    body = hero('Косметологам', [('Косметологам', None)], '<p>Оригинальная продукция с документами, выгодные условия, обучение и поддержка — от официального дистрибьютора в России.</p>') + f'''
<section class="rb-sec" style="padding-top:0"><div class="rb-wrap">{feats([
        (ICON['gift'], '−15% на первый заказ', 'Стартовая скидка для новых специалистов и клиник.'),
        (ICON['stairs'], 'Накопительная система лояльности', 'Скидка растёт вместе с объёмом закупок.'),
        (ICON['shield'], 'Оригинальная продукция', 'Прямые поставки от производителя, документы на всю продукцию.'),
        (ICON['chat'], 'Персональный менеджер', 'Подбор ассортимента, протоколы и ответы на вопросы.')])}</div></section>
{section('Обучение', 'Вебинары и обучение', f"""<div class="rb-split"><div class="rb-rich"><p><strong>Вебинары — по вторникам, 2 раза в месяц.</strong> Разбираем протоколы, сочетания препаратов и новинки. Время и ссылку на эфир сообщает менеджер.</p>
<p><strong>Индивидуальное и групповое обучение</strong> — по согласованию: в учебном центре или в вашей клинике при запуске препаратов.</p>
<p>Партнёр по обучению — институт косметологии «Дом Русской Косметики»: программы с документами государственного образца, НМО и ФИС ФРДО.</p>
<div class="rb-btns"><a class="rb-btn rb-btn--fill" href="#popup:signup">Записаться на обучение</a><a class="rb-btn" href="{RUTUBE}" target="_blank" rel="noopener">Канал на Рутубе</a></div></div>
<div><h3 style="margin-top:0">Ближайшие вебинары</h3><div class="rb-events">{up}</div></div></div>""")}
{section('Записи', 'Смотрите вебинары на Рутубе', f'<div class="rb-videos">{vids}</div>')}
{section('Как заказать', 'Четыре шага до первой поставки', steps([
        ('Заявка', 'Оставьте заявку на сайте или напишите в мессенджер.'),
        ('Консультация', 'Менеджер свяжется с вами, пришлёт прайс и поможет подобрать препараты.'),
        ('Счёт и оплата', 'Оформляем заказ с учётом скидки −15% на первый заказ.'),
        ('Доставка', 'Отправляем продукцию по России вместе с документами.')]))}
{section('Вопросы', 'Частые вопросы', faq([
        ('Почему на сайте нет цен?', '<p>Цены для специалистов присылает менеджер после заявки — так мы учитываем вашу скидку и объём закупки.</p>'),
        ('Как получить скидку −15%?', '<p>Скидка действует на первый заказ для новых клиентов. Укажите в заявке, что заказываете впервые.</p>'),
        ('Как работает накопительная система?', '<p>Скидка растёт вместе с суммой ваших закупок. Подробные условия расскажет менеджер.</p>'),
        ('Где посмотреть записи вебинаров?', f'<p>Часть записей — на нашем <a href="{RUTUBE}" target="_blank" rel="noopener">канале на Рутубе</a>, остальные — по запросу у менеджера.</p>'),
        ('Есть ли документы на продукцию?', '<p>Да, продукция поставляется напрямую от производителя с документами. Производство работает по стандартам ISO и GMP.</p>')]))}
{cta('Получите прайс для специалистов', 'Оставьте заявку — менеджер свяжется с вами, пришлёт цены и расскажет об условиях.')}{WARN_SEC}'''
    page('/kosmetologam', 'Косметологам', body, {'title': 'Косметологам — условия, скидки и обучение | Революшн Био',
                                                 'description': 'Скидка −15% на первый заказ, накопительная система лояльности, вебинары 2 раза в месяц и обучение по препаратам JeuDérm, Rejusome и Calyra Lux 5.',
                                                 'keywords': 'косметологам, обучение косметологов, вебинары, JeuDérm, Rejusome, Calyra Lux 5'})


def build_pacientam():
    body = hero('Пациентам', [('Пациентам', None)], '<p>Как работают процедуры с препаратами JeuDérm, Rejusome и Calyra Lux&nbsp;5, как подготовиться и как сохранить результат.</p>') + f'''
<section class="rb-sec" style="padding-top:0"><div class="rb-wrap">{feats([
        (BRAND_ICON[0], 'Возрастные изменения', 'Пептидный уход JeuDérm Reform Age и Calyra Lux 5 — для плотности, увлажнённости и сияния кожи.'),
        (BRAND_ICON[1], 'Восстановление кожи', 'Сыворотки с экзосомами Rejusome — для глубокого восстановления и ровного тона.'),
        (ICON['heart'], 'Чувствительная и проблемная кожа', 'Линейки JeuDérm Ato Care и Acno Active — для реактивной и склонной к акне кожи.'),
        (ICON['users'], 'Кожа головы и волосы', 'Rejusome Plus Hair и JeuDérm Hair Genesis — для кожи головы и роста волос.')])}</div></section>
{section('Процедура', 'Как проходит курс', steps([
        ('Консультация', 'Специалист оценивает состояние кожи и подбирает препараты и протокол.'),
        ('Процедура', 'Препарат вводится или наносится по протоколу производителя — в кабинете косметолога.'),
        ('Курс', 'Обычно рекомендуется курс из нескольких процедур; точную схему определяет специалист.'),
        ('Домашний уход', 'Средства для дома помогают сохранить результат между визитами.')]))}
{section('Вопросы', 'Частые вопросы', faq([
        ('Где пройти процедуру?', '<p>Оставьте заявку — мы подскажем косметолога или клинику, которые работают с нашими препаратами.</p>'),
        ('Можно ли купить препараты самостоятельно?', '<p>Профессиональные препараты применяет специалист. Средства для домашнего ухода подберёт ваш косметолог.</p>'),
        ('Есть ли противопоказания?', '<p>Да, как у любых процедур. Перед курсом обязательно проконсультируйтесь со специалистом.</p>')]))}
{cta('Подскажем, где пройти процедуру', 'Оставьте заявку — мы свяжемся с вами и порекомендуем специалиста.', btn='Задать вопрос', href='#popup:feedback')}{WARN_SEC}'''
    page('/pacientam', 'Пациентам', body, {'title': 'Пациентам — процедуры с JeuDérm, Rejusome и Calyra Lux 5 | Революшн Био',
                                           'description': 'Что дают процедуры с препаратами JeuDérm, Rejusome и Calyra Lux 5, как проходит курс и где найти специалиста.',
                                           'keywords': 'процедуры, косметолог, экзосомы, пептиды, уход за кожей'})


def build_about():
    rel = 'about.html'
    s = soup(rel)
    body = hero('О компании', [('О компании', None)], '<p>ООО «Революшн Био» — официальный дистрибьютор продукции южнокорейского производителя VIRTA-MED KOREA в России.</p>') + f'''
<section class="rb-sec" style="padding-top:0"><div class="rb-wrap">{stats(ABOUT_STATS)}</div></section>
{section('Что мы делаем', 'Больше, чем поставка косметики', feats([
        (ICON['shield'], 'Прямые поставки', 'Оригинальная продукция напрямую от производителя — с документами, без посредников.'),
        (ICON['truck'], 'Логистика по России', 'Доставляем профессиональные и домашние средства клиникам, косметологам и партнёрам.'),
        (ICON['users'], 'Обучение', 'Вебинары, обучение в клиниках и в малых группах, международные симпозиумы.'),
        (ICON['doc'], 'Маркетинговая поддержка', 'Протоколы, материалы и сопровождение для специалистов и дистрибьюторов.')]))}
<section class="rb-sec"><div class="rb-wrap"><div class="rb-panel rb-quote"><span class="rb-kicker">Научный руководитель</span>
<blockquote>«Работая в эстетической медицине более 20 лет, я перепробовала множество брендов, но именно ЖеДерм стал для меня настоящим открытием. Это инструмент, который помогает достигать видимых и устойчивых результатов у клиентов».</blockquote>
<p><b>Лилия Мукарамова</b><br><span class="rb-muted">Научный руководитель Революшн Био, международный тренер</span></p></div></div></section>
{section('Реквизиты', 'ООО «Революшн Био»', '<div class="rb-rich"><p>105064, Москва, ул. Земляной Вал, д. 7, пом. 2/4<br>ИНН 9709100594 · КПП 770901001 · ОГРН 1237700714085</p></div><div class="rb-btns"><a class="rb-btn" href="/proizvoditel">О производителе</a><a class="rb-btn" href="/distributor">Стать дистрибьютором</a></div>')}
{cta('Работайте с официальным дистрибьютором', 'Новым клиентам — −15% на первый заказ.')}'''
    page('/about', 'О компании', body, {'title': 'О компании Революшн Био — официальный дистрибьютор в России',
                                        'description': 'Революшн Био — официальный дистрибьютор JeuDérm, Rejusome и Calyra Lux 5: прямые поставки, логистика, обучение и поддержка специалистов.',
                                        'keywords': meta(s, 'keywords')})


def build_proizvoditel():
    letter = 'https://cdn.jsdelivr.net/gh/freyia-me/-@16606b2/images/home/distributor-letter.webp'
    body = hero('Производитель', [('Производитель', None)], '<p>VIRTA-MED KOREA Co., LTD — южнокорейская компания из Тэджона, производитель профессиональной космецевтики JeuDérm, Rejusome и Calyra Lux&nbsp;5.</p>') + f'''
<section class="rb-sec" style="padding-top:0"><div class="rb-wrap">{stats([('ISO · GMP', 'международные стандарты производства'), ('50 000+', 'процедур в клиниках и центрах'), ('20+', 'стран, где работают с продукцией'), ('Корея', 'Тэджон, собственное производство')])}</div></section>
{section('Наука', 'Клинически протестированные формулы', feats([
        (ICON['flask'], 'Исследования', 'Эффективность средств подтверждена в Дерматологическом центре Национального университета Чунгнам и в Университете Ханнам.'),
        (ICON['shield'], 'Стандарты качества', 'Производство работает по международным стандартам ISO и GMP.'),
        (BRAND_ICON[0], 'Биотехнологии', 'Пептиды, пробиотики, экзосомы, полинуклеотиды и PDRN в основе формул.'),
        (ICON['globe'], 'Международный опыт', 'Продукцию используют специалисты более чем в 20 странах.')]))}
<section class="rb-sec"><div class="rb-wrap"><div class="rb-split"><div><span class="rb-kicker">Официальное подтверждение</span><h2>Письмо производителя</h2><hr class="rb-rule">
<p class="rb-lead">Производитель подтверждает: ООО «Революшн Био» уполномочено представлять бренд, осуществлять продажи, маркетинговую поддержку и логистику на всей территории России.</p>
<p class="rb-muted">VIRTA-MED KOREA Co., LTD · подписано CEO Tatyana Jeon · 01.11.2025</p></div>
<a class="rb-letter" href="{letter}" target="_blank" rel="noopener"><img src="{letter}" alt="Письмо производителя об официальном дистрибьюторе" loading="lazy"></a></div></div></section>
{section('Бренды', 'Продукция производителя', feats([
        (BRAND_ICON[0], '<a href="/jeuderm">JeuDérm</a>', 'Пептидная космецевтика: профессиональный и домашний уход.'),
        (BRAND_ICON[1], '<a href="/rejusome">Rejusome</a>', 'Стерильные сыворотки и космецевтика с экзосомами.'),
        (BRAND_ICON[2], '<a href="/calyra-lux-5">Calyra Lux 5</a>', 'CAP Пептид 5, PN и гиалуронат натрия в одном шприце.'),
        (BRAND_ICON[3], '<a href="/jeuderm?line=pdrn">Crystal PDRN</a>', 'PDRN + HA 3% — восстановление качества кожи.')]))}'''
    page('/proizvoditel', 'Производитель', body, {'title': 'Производитель VIRTA-MED KOREA — JeuDérm, Rejusome, Calyra Lux 5 | Революшн Био',
                                                  'description': 'VIRTA-MED KOREA Co., LTD (Тэджон, Корея): производство по стандартам ISO и GMP, клинически протестированные формулы.',
                                                  'keywords': 'VIRTA-MED KOREA, производитель, JeuDérm, Корея, ISO, GMP'})


def build_distributor():
    body = hero('Стать дистрибьютором', [('Стать дистрибьютором', None)], '<p>Работаем с дистрибьюторами, клиниками эстетической медицины и косметологическими центрами — напрямую от официального дистрибьютора в России.</p>') + f'''
<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><div class="rb-btns" style="margin-top:0"><a class="rb-btn rb-btn--fill" href="#popup:partner">Узнать условия</a><a class="rb-btn" href="https://wa.me/79253428202" target="_blank" rel="noopener">Написать в WhatsApp</a></div></div></section>
{section('Что получает партнёр', 'Почему с нами выгодно', feats([
        (ICON['shield'], 'Оригинальная продукция', 'Прямые поставки, документы на всю продукцию.'),
        (ICON['star'], 'Полный портфель', 'Препараты для кабинета и домашний уход: клиенты возвращаются между процедурами.'),
        (ICON['users'], 'Обучение команды', 'Бесплатное обучение специалистов, протоколы, вебинары.'),
        (ICON['doc'], 'Маркетинговая поддержка', 'Фото продуктов, описания, материалы для соцсетей и презентации.'),
        (ICON['chat'], 'Персональный менеджер', 'Помощь с запуском, ассортиментом и первыми продажами.'),
        (ICON['stairs'], 'Растущие условия', 'Условия улучшаются вместе с объёмом закупок.')], cols=3))}
{section('Как начать', 'Четыре шага до партнёрства', steps([
        ('Заявка', 'Оставьте заявку или напишите в мессенджер — расскажите о регионе и компании.'),
        ('Предложение', 'Менеджер пришлёт прайс для партнёров и условия сотрудничества.'),
        ('Договор и первая поставка', 'Подбираем стартовый ассортимент под рынок региона.'),
        ('Обучение и запуск', 'Обучаем команду, передаём протоколы и материалы, сопровождаем первые продажи.')]))}
{cta('Получите прайс для партнёров', 'Пришлём условия сотрудничества, прайс и материалы о брендах.', btn='Получить прайс', href='#popup:partner')}'''
    page('/distributor', 'Стать дистрибьютором', body, {'title': 'Стать дистрибьютором JeuDérm, Rejusome, Calyra Lux 5 | Революшн Био',
                                                        'description': 'Партнёрство для дистрибьюторов и клиник: прямые поставки, обучение, маркетинговая поддержка и персональный менеджер.',
                                                        'keywords': 'стать дистрибьютором, партнёрство, JeuDérm, Rejusome'})


def build_contacts():
    s = soup('kontakty.html')
    page('/kontakty', 'Контакты', hero('Контакты', [('Контакты', None)]) + contacts_section('kontakty.html', s), seo_of(s, 'Контакты'))


def build_404():
    body = '''<section class="rb-hero rb-404"><div class="rb-wrap"><span class="rb-kicker">Ошибка 404</span><h1>Страница не найдена</h1><hr class="rb-rule">
<p class="rb-lead">Возможно, страница переехала: мы обновили сайт и собрали всю продукцию на страницах брендов.</p>
<div class="rb-btns"><a class="rb-btn rb-btn--fill" href="/">На главную</a><a class="rb-btn" href="/jeuderm">JeuDérm</a><a class="rb-btn" href="/rejusome">Rejusome</a><a class="rb-btn" href="/calyra-lux-5">Calyra Lux 5</a></div></div></section>'''
    page('/404', 'Страница не найдена', body, {'title': 'Страница не найдена — Революшн Био', 'description': '', 'keywords': ''})


def build_article(rel, alias):
    s = soup(rel)
    d = k2_item(rel, s)
    body = hero(d['title'], [(d['title'], None)]) + f'''<section class="rb-sec" style="padding-top:0"><div class="rb-wrap"><div class="rb-rich">{d['intro']}{d['full']}</div></div></section>'''
    page(alias, d['title'], body, seo_of(s, d['title']))


ABOUT_STATS = [('с 2022', 'года на рынке'), ('15 000', 'клиентов в нашей базе'), ('5', 'инновационных технологий: пептиды, экзосомы, PN, PDRN, CAP Пептид 5'), ('ISO · GMP', 'стандарты производства')]
WARN_SEC = f'<div class="rb-wrap">{WARN}</div>'

JD = jd_products() + [pdrn_product()]
RJ = rj_products()
build_home()
build_jeuderm(JD)
build_rejusome(RJ)
build_calyra()
build_kosmetologam()
build_pacientam()
build_about()
build_proizvoditel()
build_distributor()
build_contacts()
build_404()
build_article('policy.html', '/policy')
build_article('soglasie.html', '/soglasie')

# ---------------------------------------------------------------- редиректы со старого сайта и SEO
def old_url(rel):
    return '/' if rel == 'index.html' else '/' + rel[:-5]

OLD_PRODUCT = {o: f'/rejusome#p-{p["id"]}' for p in RJ for o in p['old']}
OLD_PRODUCT['product/item/59-crystal-pdrn.html'] = '/jeuderm?line=pdrn#p-crystal-pdrn'
OLD_PRODUCT['product/item/81-jeuderm-homecare.html'] = '/jeuderm?care=home'
OLD_PRODUCT['product/item/82-jeuderm-pofessional.html'] = '/jeuderm?care=pro'
OLD_CAT = {
    '7-jeuderm': '/jeuderm', '9-biorevitalizatsiya': '/jeuderm?line=pdrn', '5-ekzosomy': '/rejusome?type=serum',
    '19-trikhologiya': '/rejusome?type=hair', '11-pro-skincare': '/rejusome?type=cosmetics',
}
def new_url(rel):
    if rel in OLD_PRODUCT:
        return OLD_PRODUCT[rel]
    m = re.match(r'product/itemlist/category/([^/]+)\.html$', rel)
    if m and m.group(1) in OLD_CAT:
        return OLD_CAT[m.group(1)]
    first = rel.split('/')[0].replace('.html', '')
    return {'index': None, 'about': None, 'kontakty': None, 'policy': None, 'soglasie': None,
            'product': '/#katalog', 'uchebnyj-tsentr': '/kosmetologam', 'sales': '/kosmetologam', 'news': '/about',
            'partners': '/distributor'}.get(first, '/')

redirects = set()
for root_, dirs, files in os.walk(SRC):
    for f in files:
        if not f.endswith('.html'):
            continue
        rel = os.path.relpath(os.path.join(root_, f), SRC).replace(os.sep, '/')
        if rel.startswith(('templates/', 'media/', 'components/', 'modules/', 'plugins/', 'cache/', 'images/')):
            continue
        dst = new_url(rel)
        if dst and dst != old_url(rel):
            redirects.add((old_url(rel), dst))
redirects.add(('/component/k2/item/7-doktor-vasilenko-elina', '/'))
redirects.add(('/component/k2/item/8-irina', '/'))
redirects = sorted(redirects)
with open(os.path.join(OUT, 'redirects.txt'), 'w', encoding='utf-8') as f:
    f.write('# 301-редиректы: старый адрес (Joomla) -> новый адрес (Tilda)\n# Tilda: Настройки сайта → Ещё → Редиректы (301)\n'
            '# Адреса с #p-… открывают на странице бренда окно нужного товара.\n')
    for a, b in redirects:
        f.write(f'{a}\t{b}\n')
with open(os.path.join(OUT, 'seo-pages.txt'), 'w', encoding='utf-8') as f:
    for alias, name, t, dsc, kw in SEO:
        f.write(f'{alias}  (файл tilda/{name}.html)\n  Title: {t}\n  Description: {dsc}\n  Keywords: {kw}\n\n')
json.dump({'pages': [s[0] for s in SEO], 'images': len(IMAGES), 'redirects': len(redirects), 'products': {'jeuderm': len(JD), 'rejusome': len(RJ)}},
          sys.stdout, ensure_ascii=False, indent=1)
