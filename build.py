"""Build the AlgoClair static site: wraps content/<lang>/<slug>.html fragments in the shared layout.

Each fragment starts with a JSON header between <!--meta and -->:
  {"title", "description", "rubric", "dek", "pair" (slug in the other language),
   "date" (YYYY-MM-DD), "kind": "article" | "page" | "legal", "card": short teaser}
Placeholders in fragments: {{BUY}} (buy button), {{GUIDE}} (link to the sales page).
Output goes to docs/ (GitHub Pages: main branch, /docs folder).
"""
import json, pathlib, re, html, shutil

ROOT = pathlib.Path(__file__).parent
BASE_URL = "https://gwalarn-studio.github.io/algoclair/"
# Payments worker address, known once it is deployed (e.g. "https://commandes.xxx.workers.dev").
# While empty, buy buttons show "available soon" instead of a link.
WORKER_URL = ""
PRICE = "7 €"

T = {
 "fr": {"back": "Retour", "home": "Accueil", "cats_label": "Catégories", "guide": "Le guide", "other": "EN", "other_lang": "en",
        "tag": "Les algorithmes des réseaux sociaux, expliqués simplement.",
        "legal": "Mentions légales", "privacy": "Confidentialité", "terms": "CGV", "withdraw": "Se rétracter du contrat ici",
        "promo_h": "Le guide complet", "promo_p": "Décoder l'algorithme d'Instagram, TikTok et YouTube Shorts : 11 chapitres, 25 accroches, un plan de 30 jours.",
        "promo_b": "Voir le guide", "updated": "Mis à jour le", "next": "À lire aussi",
        "buy": "Acheter le guide · " + PRICE, "soon": "Disponible très bientôt",
        "disc": "AlgoClair est un site indépendant, sans lien avec Instagram, Meta, TikTok ou YouTube. Nous citons nos sources et n'inventons aucun chiffre.",
        "rubrics": {"algo": "Algorithmes", "create": "Créer du contenu", "myths": "Mythes et vérités", "guide": "Guide", "legal": "Informations légales"}},
 "en": {"back": "Back", "home": "Home", "cats_label": "Categories", "guide": "The guide", "other": "FR", "other_lang": "fr",
        "tag": "Social media algorithms, explained simply.",
        "legal": "Legal notice", "privacy": "Privacy", "terms": "Terms", "withdraw": "Withdraw from contract here",
        "promo_h": "The complete guide", "promo_p": "Decode the Instagram, TikTok and YouTube Shorts algorithms: 11 chapters, 25 hooks, a 30-day plan.",
        "promo_b": "See the guide", "updated": "Updated", "next": "Read next",
        "buy": "Buy the guide · " + PRICE, "soon": "Available very soon",
        "disc": "AlgoClair is an independent site, not affiliated with Instagram, Meta, TikTok or YouTube. We cite our sources and never invent numbers.",
        "rubrics": {"algo": "Algorithms", "create": "Content creation", "myths": "Myths and facts", "guide": "Guide", "legal": "Legal"}},
}
# Sister sites of the Gwalarn family, linked in every footer: (name, short description per lang, url per lang).
SISTERS = [("Plume & Go", {"fr": "CV et textes rédigés par IA", "en": "AI-written CVs and texts"},
            {"fr": "https://gwalarn-studio.github.io/Plume-and-go/?lang=fr", "en": "https://gwalarn-studio.github.io/Plume-and-go/?lang=en"}),
           ("NextDesk", {"fr": "carrière et télétravail", "en": "careers and remote work"},
            {"fr": "https://gwalarn-studio.github.io/nextdesk/fr/", "en": "https://gwalarn-studio.github.io/nextdesk/"}),
           ("AlgoClair", {"fr": "algorithmes des réseaux sociaux", "en": "social media algorithms"},
            {"fr": "https://gwalarn-studio.github.io/algoclair/", "en": "https://gwalarn-studio.github.io/algoclair/en/"})]

def sisters(lang, me):
    label = "Les sites Gwalarn :" if lang == "fr" else "Gwalarn sites:"
    links = "".join(f'<span>{html.escape(n)}</span>' if n == me else f'<a href="{u[lang]}">{html.escape(n)} · {d[lang]}</a>' for n, d, u in SISTERS)
    return f'<div class="wrap sister"><span>{label}</span>{links}</div>'

LEGAL = {"fr": ("mentions-legales", "confidentialite", "cgv", "retractation"),
         "en": ("legal-notice", "privacy", "terms", "withdrawal")}
GUIDE = {"fr": "guide-algorithme", "en": "algorithm-guide"}
# Category pages, in menu order: (rubric key, slug). Same order in both languages so pages pair up.
CATS = {"fr": [("algo", "algorithmes"), ("create", "creer-du-contenu"), ("myths", "mythes-et-verites")],
        "en": [("algo", "algorithms"), ("create", "content-creation"), ("myths", "myths-and-facts")]}
CAT_DEK = {"fr": {"algo": "Comment Instagram, TikTok et YouTube décident quoi montrer, d'après ce qu'ils ont eux-mêmes déclaré.",
                  "create": "Accroches, formats et méthodes pour fabriquer des vidéos qu'on regarde jusqu'au bout.",
                  "myths": "Shadowban, hashtags, heure magique : ce qui est vrai, ce qui est faux."},
           "en": {"algo": "How Instagram, TikTok and YouTube decide what to show, based on what they have said themselves.",
                  "create": "Hooks, formats and methods to make videos people watch to the end.",
                  "myths": "Shadowbans, hashtags, the magic hour: what's true and what isn't."}}

ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%23111827'/%3E"
        "%3Ccircle cx='16' cy='16' r='8' fill='none' stroke='%23ffffff' stroke-width='3'/%3E%3C/svg%3E")

def fmt_date(d, lang):
    y, m, dd = d.split("-")
    if lang == "fr":
        mois = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
        return f"{int(dd)} {mois[int(m)-1]} {y}"
    months = "January February March April May June July August September October November December".split()
    return f"{months[int(m)-1]} {int(dd)}, {y}"

def home_path(lang):
    return "index.html" if lang == "fr" else "en/index.html"

def rel(path):
    return "../" * path.count("/")

def buy_button(lang, cls="btn btn-mark"):
    t = T[lang]
    if not WORKER_URL:
        return f'<a class="{cls}" aria-disabled="true">{t["soon"]}</a>'
    return f'<a class="{cls}" href="{WORKER_URL}/commander/guide-algo?lang={lang}" rel="nofollow">{t["buy"]}</a>'

def head(lang, title, desc, path, alt_path, extra=""):
    canon = BASE_URL + ("" if path == "index.html" else path)
    links = f'<link rel="canonical" href="{canon}">'
    if alt_path is not None:
        alt = BASE_URL + ("" if alt_path == "index.html" else alt_path)
        links += (f'<link rel="alternate" hreflang="{lang}" href="{canon}">'
                  f'<link rel="alternate" hreflang="{T[lang]["other_lang"]}" href="{alt}">')
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="google-site-verification" content="xr04cnwUJ9O7dfNQE8VGNQkIYiNTeebG1ID9B4vZDqc">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{html.escape(title)}"><meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{canon}">
{links}
<link rel="icon" type="image/svg+xml" href="{rel(path)}assets/gwalarn-icone.svg"><link rel="icon" type="image/png" href="{rel(path)}assets/gwalarn-icone.png"><link rel="apple-touch-icon" href="{rel(path)}assets/gwalarn-icone.png">
<link rel="stylesheet" href="{rel(path)}assets/fonts/fonts.css">
<link rel="stylesheet" href="{rel(path)}assets/style.css">{extra}
</head><body>"""

def cat_path(lang, rubric):
    return next(f"{lang}/{slug}.html" for k, slug in CATS[lang] if k == rubric)

def nav(lang, path, alt_path, active=None):
    t = T[lang]; r = rel(path)
    def item(href, label, key):
        cur = ' aria-current="page"' if key == active else ""
        return f'<a href="{r}{href}"{cur}>{label}</a>'
    cats = item(home_path(lang), t["home"], "home")
    cats += "".join(item(f"{lang}/{slug}.html", t["rubrics"][k], k) for k, slug in CATS[lang])
    cats += item(f"{lang}/{GUIDE[lang]}.html", t["guide"], "guide")
    other_home = home_path(t["other_lang"])
    other = f"{r}{alt_path}" if alt_path is not None else f"{r}{other_home}"
    return f"""<header class="band"><div class="wrap nav">
<a class="logo" href="{r}{home_path(lang)}"><img class="gw-mark" src="{r}assets/gwalarn-icone.svg" alt="" width="28" height="28">Algo<span>Clair</span></a>
<nav class="menu" aria-label="Menu">
<a class="lang" href="{other}" hreflang="{t['other_lang']}" lang="{t['other_lang']}">{t['other']}</a>
<a class="cta" href="{r}{lang}/{GUIDE[lang]}.html">{t['guide']} · {PRICE}</a></nav></div>
<nav class="cats" aria-label="{t['cats_label']}"><div class="wrap">{cats}</div></nav>"""

def footer(lang, path):
    t = T[lang]; r = rel(path); l = LEGAL[lang]
    return f"""<footer><div class="wrap row"><span>AlgoClair · Gwalarn · {t['tag']}</span>
<nav><a href="{r}{lang}/{l[0]}.html">{t['legal']}</a><a href="{r}{lang}/{l[1]}.html">{t['privacy']}</a><a href="{r}{lang}/{l[2]}.html">{t['terms']}</a><a href="https://commandes.gwalarn.workers.dev/retractation?site=algoclair&amp;lang={lang}">{t['withdraw']}</a></nav>
</div>{sisters(lang, "AlgoClair")}</footer><script src="{r}assets/site.js" defer></script></body></html>"""

def promo(lang):
    t = T[lang]
    return f"""<div class="box promo"><h3>{t['promo_h']}</h3><p>{t['promo_p']}</p>
<a class="btn btn-mark" href="{GUIDE[lang]}.html">{t['promo_b']}</a></div>"""

def fr_typo(s):
    """French typography: no-break spaces inside « » and before : ; ? ! so they never start a line. Text only, tags untouched."""
    def fix(t):
        t = t.replace("« ", "«\u00a0").replace(" »", "\u00a0»")
        return re.sub(r" ([:;?!])", "\u00a0\\1", t)
    return re.sub(r"(^|>)([^<]*)", lambda m: m.group(1) + fix(m.group(2)), s)

def load(lang):
    out = []
    for f in sorted((ROOT / "content" / lang).glob("*.html")):
        raw = f.read_text(encoding="utf-8")
        m = re.match(r"\s*<!--meta\s*(\{.*?\})\s*-->", raw, re.S)
        meta = json.loads(m.group(1)); meta["slug"] = f.stem
        meta["body"] = raw[m.end():].replace("{{BUY}}", buy_button(lang)).replace("{{GUIDE}}", f"{GUIDE[lang]}.html")
        out.append(meta)
    return out

def write(path, page):
    if path == "index.html" or path.startswith("fr/"):
        page = fr_typo(page)
    (ROOT / "docs" / path).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / path).write_text(page, encoding="utf-8")

def build_page(lang, a, related):
    t = T[lang]
    path = f"{lang}/{a['slug']}.html"
    alt_path = f"{t['other_lang']}/{a['pair']}.html" if a.get("pair") else None
    kind = a.get("kind", "article")
    extra = ""
    if kind == "article":
        ld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": a["title"],
                         "description": a["description"], "inLanguage": lang, "dateModified": a["date"],
                         "publisher": {"@type": "Organization", "name": "AlgoClair"}}, ensure_ascii=False)
        extra = f'<script type="application/ld+json">{ld}</script>'
    page = head(lang, a["title"] + " | AlgoClair", a["description"], path, alt_path, extra) + nav(lang, path, alt_path, a["rubric"] if kind == "article" else ("guide" if a["rubric"] == "guide" else None))
    crumb = (f'<a href="{rel(path)}{cat_path(lang, a["rubric"])}">{t["rubrics"][a["rubric"]]}</a>'
             if kind == "article" else t["rubrics"][a["rubric"]])
    page += f"""<div class="wrap article-head">
<a class="back" href="{rel(path)}{home_path(lang)}" data-back><span aria-hidden="true">←</span> {t['back']}</a>
<div class="crumbs"><a href="{rel(path)}{home_path(lang)}">{t['home']}</a> / {crumb}</div>
<h1>{html.escape(a['title'])}</h1>
<p class="dek">{a['dek']}</p>
<div class="byline">{t['updated']} {fmt_date(a['date'], lang)}</div></div></header>"""
    if kind == "article":
        rel_list = "".join(f'<li><a href="{r["slug"]}.html">{html.escape(r["title"])}</a></li>' for r in related)
        page += f"""<main class="wrap layout"><article class="prose">{a['body']}
<p class="disclosure">{t['disc']}</p></article>
<aside class="side">{promo(lang)}<div class="box"><h3>{t['next']}</h3><ul>{rel_list}</ul></div></aside></main>"""
    elif kind == "legal":
        page += f'<main class="wrap" style="padding-block:40px 64px"><article class="prose legal">{a["body"]}</article></main>'
    else:
        page += f'<main class="wrap" style="padding-block:40px 64px">{a["body"]}</main>'
    page += footer(lang, path)
    write(path, page)
    return path

HOME = {
 "fr": {"title": "AlgoClair : comprendre l'algorithme d'Instagram, TikTok et YouTube pour percer",
        "desc": "Guides gratuits et sourcés pour comprendre les algorithmes d'Instagram, TikTok et YouTube Shorts, et faire décoller vos vidéos.",
        "h1": "Comprendre les algorithmes des réseaux sociaux, <em>sources à l'appui.</em>",
        "lead": "Ce que les plateformes ont vraiment dit sur leurs algorithmes, traduit en actions simples. Sans chiffres inventés, sans recette miracle.",
        "latest": "Articles gratuits",
        "strip": ("Le guide complet pour percer", "11 chapitres, 25 accroches à adapter, une méthode de test et un plan d'action de 30 jours. PDF en français et en anglais, téléchargement immédiat.", "Découvrir le guide")},
 "en": {"title": "AlgoClair: understand the Instagram, TikTok and YouTube algorithms and break through",
        "desc": "Free, sourced guides to understand the Instagram, TikTok and YouTube Shorts algorithms and get your videos going.",
        "h1": "Understand social media algorithms, <em>with sources.</em>",
        "lead": "What the platforms have really said about their algorithms, turned into simple actions. No made-up numbers, no miracle recipe.",
        "latest": "Free articles",
        "strip": ("The complete guide to breaking through", "11 chapters, 25 hooks to adapt, a testing method and a 30-day action plan. PDF in English and French, instant download.", "See the guide")},
}

def build_home(lang, items):
    t = T[lang]; h = HOME[lang]
    path = home_path(lang); alt = home_path(t["other_lang"])
    page = head(lang, h["title"], h["desc"], path, alt) + nav(lang, path, alt, "home")
    page += f"""<div class="wrap hero"><span class="eyebrow">{t['tag']}</span><h1>{h['h1']}</h1><p>{h['lead']}</p>
<div><a class="btn btn-mark" href="{rel(path)}{lang}/{GUIDE[lang]}.html">{h['strip'][2]} · {PRICE}</a></div></div></header><main>"""
    cards = ""
    for a in sorted([i for i in items if i.get("kind", "article") == "article"], key=lambda x: x["date"]):
        cards += f"""<a class="card" href="{rel(path)}{lang}/{a['slug']}.html"><span class="tag">{t['rubrics'][a['rubric']]}</span>
<h3>{html.escape(a['title'])}</h3><p>{a['card']}</p></a>"""
    page += f"""<section class="wrap"><div class="sec-head"><h2>{h['latest']}</h2></div><div class="grid">{cards}</div></section>
<section class="wrap" style="padding-top:0"><div class="strip"><div><h2>{h['strip'][0]}</h2><p>{h['strip'][1]}</p></div>
<a class="btn btn-mark" href="{rel(path)}{lang}/{GUIDE[lang]}.html">{h['strip'][2]}</a></div></section></main>"""
    page += footer(lang, path)
    write(path, page)
    return path

def card(lang, path, a):
    t = T[lang]
    return f"""<a class="card" href="{rel(path)}{lang}/{a['slug']}.html"><span class="tag">{t['rubrics'][a['rubric']]}</span>
<h3>{html.escape(a['title'])}</h3><p>{a['card']}</p></a>"""

def build_cat(lang, i, items):
    t = T[lang]; key, slug = CATS[lang][i]
    path = f"{lang}/{slug}.html"; alt = f"{t['other_lang']}/{CATS[t['other_lang']][i][1]}.html"
    name = t["rubrics"][key]
    page = head(lang, f"{name} | AlgoClair", CAT_DEK[lang][key], path, alt) + nav(lang, path, alt, key)
    page += f"""<div class="wrap article-head">
<a class="back" href="{rel(path)}{home_path(lang)}" data-back><span aria-hidden="true">←</span> {t['back']}</a>
<h1>{name}</h1><p class="dek">{CAT_DEK[lang][key]}</p></div></header><main>"""
    cards = "".join(card(lang, path, a) for a in items if a.get("kind", "article") == "article" and a["rubric"] == key)
    page += f"""<section class="wrap"><div class="grid">{cards}</div></section>
<section class="wrap" style="padding-top:0">{promo_strip(lang, path)}</section></main>"""
    page += footer(lang, path)
    write(path, page)
    return path

def promo_strip(lang, path):
    h = HOME[lang]
    return f"""<div class="strip"><div><h2>{h['strip'][0]}</h2><p>{h['strip'][1]}</p></div>
<a class="btn btn-mark" href="{rel(path)}{lang}/{GUIDE[lang]}.html">{h['strip'][2]}</a></div>"""

def main():
    docs = ROOT / "docs"
    if docs.exists(): shutil.rmtree(docs)
    docs.mkdir()
    shutil.copytree(ROOT / "assets", docs / "assets")
    urls = []
    for lang in ("fr", "en"):
        items = load(lang)
        arts = [a for a in items if a.get("kind", "article") == "article"]
        for a in items:
            related = [r for r in arts if r["slug"] != a["slug"]][:4]
            p = build_page(lang, a, related)
            if a.get("kind") != "legal":
                urls.append((p, a["date"]))
        urls.append((build_home(lang, items), max(a["date"] for a in items)))
        for i in range(len(CATS[lang])):
            urls.append((build_cat(lang, i, items), max(a["date"] for a in items)))
    sm = "".join(f"<url><loc>{BASE_URL}{'' if p == 'index.html' else p}</loc><lastmod>{d}</lastmod></url>" for p, d in urls)
    (docs / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>', encoding="utf-8")
    (docs / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}sitemap.xml\n", encoding="utf-8")
    (docs / ".nojekyll").write_text("")
    print(len(urls), "pages")

if __name__ == "__main__":
    main()
