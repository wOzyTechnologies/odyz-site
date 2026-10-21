"""Write the site footer into every page of odyz.app.

Every page gets the same footer: Odyz's own links, its help and comparison
pages, and the row of all wOzy apps. Help and Compare list every page with a
<meta name="footer-label"> tag, in footer-order, and the year is always
current. Run it after adding or renaming a page:

    python3 tools/site-footer.py          # update every page
    python3 tools/site-footer.py --check  # exit 1 if a page is out of date

A page gets the footer between <!-- site-footer --> and <!-- /site-footer -->.
A page that still has its own <footer> gets it replaced the first time.
The footer's styles live in styles.css (search for "Shared site footer"). The
script also fills any <!-- help-list --> block with the help pages, and warns
about pages missing from sitemap.xml. wozy.co runs the same script with its
own sections.
"""
import datetime
import hashlib
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1] / "docs"
SITE = "https://www.odyz.app"
CSS = None

# Pages that never get the footer.
SKIP = {"privacy.html", "terms.html"}

# A column is (heading, links). A link is (label, href). "AUTO:help" and
# "AUTO:compare" expand to the section's pages with a footer-label under
# /help/ or /compare/, in footer-order. Columns with no links are left out.
APPS = ("Apps", [
    ("Animal Loop", "https://www.wozy.co/animal-loop/"),
    ("TicToe Fury", "https://www.wozy.co/tictoefury/"),
    ("Odyz", "/"),
    ("Dapply", "https://www.wozy.co/dapply/"),
    ("About wOzy", "https://www.wozy.co/"),
])
COPYRIGHT = "© {year} wOzy Technologies LLC"

# The first section whose prefix matches a page's path wins.
SECTIONS = [
    {
        "prefix": "",
        "brand": ("Odyz", "/", "/assets/logo-stamp.png",
                  "Your trips, map and digital passport, built from the photos on your phone."),
        "columns": [
            APPS,
            ("Odyz", [
                ("Features", "/#features"),
                ("Reviews", "/#testimonials"),
                ("FAQ", "/#faq"),
                ("Press kit", "/press/"),
                ("Download on the App Store", "https://apps.apple.com/us/app/odyz/id6736624376"),
            ]),
            ("Help", ["AUTO:help", ("Contact support", "https://www.wozy.co/contact/?app=odyz")]),
            ("Compare", ["AUTO:compare"]),
        ],
        "bottom": [("Privacy Policy", "/privacy/"), ("Terms & Conditions", "/terms/"), ("X", "https://x.com/odyzapp")],
    },
]

START, END = "<!-- site-footer -->", "<!-- /site-footer -->"
LIST_START, LIST_END = "<!-- help-list -->", "<!-- /help-list -->"


def meta(text, name):
    m = re.search(r'<meta\s+name="%s"\s+content="([^"]*)"' % re.escape(name), text)
    return html.unescape(m.group(1)) if m else None


def url_for(path):
    rel = path.relative_to(ROOT).as_posix()
    return "/" + rel[: -len("index.html")] if rel.endswith("index.html") else "/" + rel


def pages():
    for p in sorted(ROOT.rglob("*.html")):
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith((".", "_")) or "/." in rel or rel in SKIP or rel.startswith("google"):
            continue
        yield p


def labelled(kind, prefix=""):
    found = []
    for p in pages():
        rel = p.relative_to(ROOT).as_posix()
        if f"/{kind}/" not in "/" + rel or not rel.startswith(prefix):
            continue
        text = p.read_text(encoding="utf-8")
        label = meta(text, "footer-label")
        if prefix:
            label = meta(text, "footer-label-app") or label
        if label:
            order = float(meta(text, "footer-order") or 100)
            found.append((order, url_for(p), label, meta(text, "description") or ""))
    return [(label, href, desc) for _, href, label, desc in sorted(found)]


def section_for(rel):
    return next(sec for sec in SECTIONS if rel.startswith(sec["prefix"]))


def footer_html(rel):
    sec = section_for(rel)
    year = datetime.date.today().year
    esc = lambda s: html.escape(s, quote=True)
    cols = []
    for heading, links in sec["columns"]:
        items = []
        for link in links:
            if isinstance(link, str) and link.startswith("AUTO:"):
                items += [(label, href) for label, href, _ in labelled(link[5:], sec["prefix"])]
            else:
                items.append(link)
        if not items:
            continue
        lis = "\n".join(f'          <li><a href="{esc(h)}">{esc(l)}</a></li>' for l, h in items)
        cols.append(
            f'      <nav class="sf-col" aria-label="{esc(heading)}">\n'
            f'        <h2 class="sf-h">{esc(heading)}</h2>\n'
            f"        <ul>\n{lis}\n        </ul>\n      </nav>"
        )
    name, href, logo, tagline = sec["brand"]
    bottom = " ".join(f'<a href="{esc(h)}">{esc(l)}</a>' for l, h in sec["bottom"])
    return f"""{START}
<footer class="sf">
  <div class="sf-in">
    <div class="sf-grid" style="--sf-cols: {len(cols)}">
      <div class="sf-brand">
        <a class="sf-logo" href="{href}"><img src="{logo}" alt="" width="36" height="36"><span>{esc(name)}</span></a>
        <p>{esc(tagline)}</p>
      </div>
{chr(10).join(cols)}
    </div>
    <div class="sf-bottom">
      <p>{esc(COPYRIGHT.format(year=year))}</p>
      <p class="sf-links">{bottom}</p>
    </div>
  </div>
</footer>
{END}"""


def help_list_html():
    esc = lambda s: html.escape(s, quote=True)
    items = "\n".join(
        f'  <li><a href="{esc(href)}">{esc(label)}</a><span>{esc(desc)}</span></li>'
        for label, href, desc in labelled("help")
    )
    return f'{LIST_START}\n<ul class="help-list">\n{items}\n</ul>\n{LIST_END}'


def css_link():
    digest = hashlib.md5((ROOT / CSS).read_bytes()).hexdigest()[:8]
    return f'<link rel="stylesheet" href="/{CSS}?v={digest}">'


def update(text, rel):
    footer = footer_html(rel)
    if START in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: footer, text, count=1, flags=re.S)
    elif "<footer" in text:
        text = re.sub(r"<footer\b.*?</footer>", lambda m: footer, text, count=1, flags=re.S)
    else:
        return text
    if not CSS:
        pass
    elif f'href="/{CSS}' in text:
        text = re.sub(r'<link rel="stylesheet" href="/%s\?v=[0-9a-f]+">' % re.escape(CSS), css_link(), text)
    else:
        text = text.replace("</head>", f"{css_link()}\n</head>", 1)
    if LIST_START in text:
        text = re.sub(re.escape(LIST_START) + r".*?" + re.escape(LIST_END), lambda m: help_list_html(), text, flags=re.S)
    return text


def main():
    check = "--check" in sys.argv
    stale = []
    for p in pages():
        old = p.read_text(encoding="utf-8")
        new = update(old, p.relative_to(ROOT).as_posix())
        if new != old:
            stale.append(p.relative_to(ROOT).as_posix())
            if not check:
                p.write_text(new, encoding="utf-8")
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    missing = [url_for(p) for p in pages()
               if p.name == "index.html" and SITE + url_for(p) not in sitemap
               and 'http-equiv="refresh"' not in p.read_text(encoding="utf-8")]
    for m in missing:
        print(f"warning: {m} is not in sitemap.xml", file=sys.stderr)
    if check:
        if stale:
            print("Footer out of date in:\n  " + "\n  ".join(stale) + "\nRun: python3 tools/site-footer.py", file=sys.stderr)
            sys.exit(1)
        print("Footer up to date on every page.")
    else:
        print(f"Updated {len(stale)} page(s).")


if __name__ == "__main__":
    main()
