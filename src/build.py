"""Build the SEO mockup of /hair/shampoos from the scraped page.

Usage: python3 -I build.py <scraped shampoos.html> <archived styles.css (gzip or plain)>
Writes index.html and assets/styles.css next to this src/ folder.
"""
import gzip, html, json, os, re, sys

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.dirname(SRC_DIR)
ARCHIVE = "https://web.archive.org/web/2026im_/https://www.beautyplussalon.com"

page_path, css_path = sys.argv[1], sys.argv[2]
h = open(page_path, encoding="utf-8").read()
read = lambda name: open(os.path.join(SRC_DIR, name), encoding="utf-8").read()
top, bottom = read("top.html"), read("bottom.html")


def matching_div_end(doc, start):
    """Index just after the </div> closing the <div> opened at `start`."""
    depth, i = 0, start
    for m in re.compile(r"<div\b|</div>").finditer(doc, start):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return m.end()
    raise ValueError("unbalanced div")


# Head: title, meta description, robots, styles
TITLE = "Professional Salon Shampoo Brands | Beauty Plus Salon"
META = ("Shop 1,100+ salon shampoos from Redken, Pureology, Biolage, Matrix and more. "
        "Color-safe, sulfate-free and purple formulas. Free U.S. shipping from $59.")
h = re.sub(r"<title>.*?</title>", f"<title>{TITLE}</title>", h, count=1, flags=re.S)
h = re.sub(r'<meta name="description"[^>]*>', f'<meta name="description" content="{META}">\n<meta name="robots" content="noindex, nofollow">', h, count=1)
h = re.sub(r'<link[^>]+href="[^"]*/css/styles\.css"[^>]*>',
           '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Mulish:ital,wght@0,300..900;1,300..900&display=swap">'
           '<link rel="stylesheet" href="assets/styles.css"><link rel="stylesheet" href="assets/seo.css">', h, count=1)
h = re.sub(r'href="[^"]*/nouislider\.min\.css"', 'href="https://cdn.jsdelivr.net/npm/nouislider@15.7.1/dist/nouislider.min.css"', h)
h = re.sub(r'href="[^"]*/splide/splide\.min\.css"', 'href="https://cdn.jsdelivr.net/npm/@splidejs/splide@4.1.3/dist/css/splide.min.css"', h)

# Scripts: theme libraries from public CDNs, trackers removed
h = re.sub(r'<script[^>]+src="[^"]*/alpine3\.min\.js"[^>]*>', '<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js">', h)
h = re.sub(r'src="[^"]*/nouislider\.min\.js"', 'src="https://cdn.jsdelivr.net/npm/nouislider@15.7.1/dist/nouislider.min.js"', h)
h = re.sub(r'src="[^"]*/splide/splide\.min\.js"', 'src="https://cdn.jsdelivr.net/npm/@splidejs/splide@4.1.3/dist/js/splide.min.js"', h)
TRACKER_SRC = r"googletagmanager|google-analytics|klevu|squarecdn|apis\.google|cloudflareinsights|/w4b7/|\.ct\.js|ieUrlPolyfill"
h = re.sub(r'<script[^>]+src="[^"]*(?:%s)[^"]*"[^>]*>\s*</script>' % TRACKER_SRC, "", h)
TRACKER_INLINE = re.compile(r"GTM-|gtm\.start|fbq|GoogleAnalytics|developer_id|init-external-scripts|mfHyvaFbPixelData")
h = re.sub(r"<script(?![^>]*src)[^>]*>(.*?)</script>",
           lambda m: "" if TRACKER_INLINE.search(m.group(1)) else m.group(0), h, flags=re.S)
h = re.sub(r"<noscript>\s*<iframe[^>]*googletagmanager.*?</noscript>", "", h, flags=re.S)
h = re.sub(r'<link[^>]+href="https://www\.beautyplussalon\.com/static/[^"]*"[^>]*>', "", h)

# Images: served from the archive.org copies (the live site is behind a Cloudflare challenge)
h = re.sub(r'(?:https://www\.beautyplussalon\.com)?/media//?', ARCHIVE + "/media/", h)

# H1
h = re.sub(r'(<span class="base" data-ui-id="page-title-wrapper">)[^<]*(</span>)', r"\1Salon Shampoo Brands\2", h, count=1)

# Category description: hidden 860-word block replaced by short intro + linking blocks
start = h.find('<div id="category-view-container"')
end = matching_div_end(h, start)
h = h[:start] + '<div id="category-view-container" class="category-view container">' + top + "</div>" + h[end:]

# Product names: H2 -> plain text, keeps the same look
h, n = re.subn(r'(<a class="product-item-link[^>]*>\s*)<h2>(.*?)</h2>', r'\1<div class="product-name">\2</div>', h, flags=re.S)
print("product H2 converted:", n)

# Bottom SEO content, full width below the product grid and sidebar
h = h.replace("</main>", bottom + "</main>", 1)

# Structured data: ItemList description + FAQPage
intro_text = html.unescape(re.sub(r"<[^>]+>", "", re.search(r'<p class="seo-intro">(.*?)</p>', top, re.S).group(1))).strip()
def fix_itemlist(m):
    data = json.loads(m.group(1))
    if data.get("@type") == "ItemList":
        data["name"] = "Salon Shampoo Brands"
        data["description"] = intro_text
        return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"
    return m.group(0)
h = re.sub(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', fix_itemlist, h, flags=re.S)
faq = [(html.unescape(q).strip(), html.unescape(re.sub(r"<[^>]+>", "", a)).strip())
       for q, a in re.findall(r"<summary>(.*?)</summary>\s*<p>(.*?)</p>", bottom, re.S)]
faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
h = h.replace("</head>", '<script type="application/ld+json">' + json.dumps(faq_ld, ensure_ascii=False) + "</script>\n</head>", 1)

# Public mockup: visible banner, and no working form (login, newsletter, search, add to cart)
banner = ('<div class="seo-mock-banner" role="note">SEO mockup by datashake for Beauty Plus Salon. '
          'This is not the official store: forms and cart are disabled. '
          'Shop on <a href="https://www.beautyplussalon.com/">beautyplussalon.com</a>.</div>')
h = re.sub(r'(<body[^>]*>)', r'\1' + banner, h, count=1)
h = re.sub(r'(<form\b[^>]*?)\saction="[^"]*"', r'\1 action="#"', h)
h = re.sub(r'<form\b', '<form onsubmit="return false"', h)
h = re.sub(r'<input\b(?=[^>]*type="(?:email|password|text|search|tel)")', '<input disabled', h)
h = re.sub(r'<button\b(?=[^>]*type="submit")', '<button disabled', h)

# Annotation toggle
toggle = ('<button type="button" class="seo-toggle" onclick="document.body.classList.toggle(\'seo-show-annot\')">'
          '<i></i>SEO mockup: show changes</button>')
# Some recent product images are not archived: show a neutral bottle placeholder instead of a broken icon
placeholder = ("<script>(function(){var ph='data:image/svg+xml;utf8,' + encodeURIComponent("
               "'<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 300 300\"><rect width=\"300\" height=\"300\" fill=\"#fff\"/>"
               "<rect x=\"120\" y=\"40\" width=\"60\" height=\"30\" rx=\"6\" fill=\"#d1d5db\"/><rect x=\"95\" y=\"70\" width=\"110\" height=\"200\" rx=\"18\" fill=\"#e5e7eb\"/>"
               "<rect x=\"110\" y=\"130\" width=\"80\" height=\"60\" rx=\"4\" fill=\"#fff\"/></svg>');"
               "function fix(i){if(i.dataset.ph)return;i.dataset.ph=1;var p=i.closest('picture');if(p)p.querySelectorAll('source').forEach(function(s){s.remove()});i.srcset='';i.src=ph;}"
               "document.querySelectorAll('img').forEach(function(i){if(i.complete&&i.naturalWidth===0)fix(i);i.addEventListener('error',function(){fix(i)});});})();</script>")
# Sticky filters: offset = height of the sticky header, which changes with scroll
sticky = ("<script>(function(){function upd(){var hd=document.querySelector('.page-header');if(!hd)return;"
          "document.documentElement.style.setProperty('--seo-sticky-top',(hd.getBoundingClientRect().bottom+16)+'px');}"
          "upd();addEventListener('scroll',upd,{passive:true});addEventListener('resize',upd);})();</script>")
h = h.replace("</body>", toggle + placeholder + sticky + "</body>", 1)

open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8").write(h)

# Theme CSS: drop the self-hosted Mulish @font-face rules (Google Fonts serves the same family)
raw = open(css_path, "rb").read()
css = (gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw).decode("utf-8")
css = re.sub(r"@font-face\{[^}]*Mulish[^}]*\}", "", css)
os.makedirs(os.path.join(OUT_DIR, "assets"), exist_ok=True)
open(os.path.join(OUT_DIR, "assets", "styles.css"), "w", encoding="utf-8").write(css)
open(os.path.join(OUT_DIR, "assets", "seo.css"), "w", encoding="utf-8").write(read("seo.css"))
print("written", os.path.join(OUT_DIR, "index.html"), len(h))
