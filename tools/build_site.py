"""Build every page of the website.

    python3 tools/build_site.py

The app name, tagline, web address and contact email live in site.json, so a
new name or your own domain is a one-file change: edit site.json, run this
script, commit. The home page body is src/index.html; the city guides come
from data/guides.json (refresh it with tools/import_guides.py).

Writes: index.html, about.html, contact.html, privacy.html, terms.html,
404.html, guides/, sitemap.xml, robots.txt and CNAME (only when the address
in site.json is your own domain).
"""
import html
import json
import re
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
DATA = json.loads((ROOT / 'data' / 'guides.json').read_text(encoding='utf-8'))
NAME = SITE['name']
BASE = SITE['url'].rstrip('/')
UPDATED = date.today().strftime('%-d %B %Y')
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']

e = html.escape

LOGO = ('<span class="logo" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M3 19h18M7 15.5l11.2-5.3c1.3-.6 2.3.9 1 1.8L11 17"/>'
        '<path d="M6.5 11.5 4 9.6l1.6-.8 3 1.4"/></svg></span>')
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23131413'/%3E"
           "%3Cpath d='M14 40h36M22 34l26-12c3-1 5 2 2 4L30 38' stroke='%23fff' stroke-width='4' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")


def contact_href():
    if SITE.get('contactEmail'):
        return 'mailto:' + SITE['contactEmail']
    return SITE['contactForm']


def page(path, title, description, body, depth=0, home=False, up=None):
    """Wrap a page body in the shared head, header and footer and write it."""
    up = '../' * depth if up is None else up
    full_title = f'{NAME} · {SITE["tagline"]}' if home else f'{title} · {NAME}'
    canonical = BASE + '/' + ('' if path == 'index.html' else path.replace('index.html', ''))
    doc = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:title" content="{e(title if not home else NAME)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{e(BASE)}/img/welcome.jpg">
<link rel="icon" href="{FAVICON}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}style.css">
</head>
<body>

<header class="nav">
  <div class="wrap nav-in">
    <a class="brand" href="{up}index.html">{LOGO}{e(NAME)}</a>
    <nav class="links" aria-label="Main">
      <a href="{up}guides/index.html">Travel guides</a>
      <a href="{up}index.html#features">The app</a>
      <a href="{up}about.html">About</a>
      <a href="{up}contact.html">Contact</a>
    </nav>
    <a class="nav-cta" href="{up}guides/index.html">Guides</a>
  </div>
</header>

{body}

<footer class="foot">
  <div class="wrap foot-in">
    <span>© {SITE["year"]} {e(NAME)}</span>
    <span><a href="{up}guides/index.html">Travel guides</a> · <a href="{up}about.html">About</a> · <a href="{up}contact.html">Contact</a> · <a href="{up}privacy.html">Privacy</a> · <a href="{up}terms.html">Terms</a></span>
  </div>
  <div class="wrap"><p class="tiny">Prices are estimates from travel partners and may change. Some links to travel partners are affiliate links, which help keep {e(NAME)} free. Always check visa and entry rules with official sources before you travel.</p></div>
</footer>

</body>
</html>
'''
    out = ROOT / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding='utf-8')
    return path


def slug(text):
    s = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return s or 'place'


def hours(minutes):
    h, m = divmod(int(round(minutes)), 60)
    return f'{h}h {m:02d}m' if h else f'{m}m'


def doc_page(path, title, description, inner):
    body = f'<main class="wrap doc">\n  <p class="eyebrow">Last updated {UPDATED}</p>\n  <h1>{e(title)}</h1>\n{inner}\n</main>'
    return page(path, title, description, body)


# ---------------------------------------------------------------- guides
guides = DATA['guides']
used = set()
for g in guides:
    s = slug(g['name'])
    if s in used:
        s = slug(g['name'] + ' ' + g['country'])
    used.add(s)
    g['slug'] = s

shutil.rmtree(ROOT / 'guides', ignore_errors=True)
written = []


def vibe_chips(g):
    return ''.join(f'<span class="chip">{e(v)}</span>' for v in g['vibes'])


def guide_page(g):
    facts = []
    if g.get('flightFromSingapore'):
        facts.append(('Flight from Singapore', hours(g['flightFromSingapore'] * 60) + ' nonstop'))
    if g.get('fromSingapore'):
        f = g['fromSingapore']
        facts.append(('One-way from Singapore', f'from S${f["fare"]}'))
    facts.append(('Currency', g['currency'] or 'Local currency'))
    if g['plug']:
        facts.append(('Plugs', g['plug']))
    facts_html = ''.join(f'<div class="fact"><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in facts)

    trend = ''
    if g['trending']:
        trend = ('<section class="block"><h2>Trending right now</h2><ul class="checks">'
                 + ''.join(f'<li>{e(t)}</li>' for t in g['trending']) + '</ul></section>')

    events = ''.join(
        f'''<li class="event{' warn' if h.get('warning') else ''}"><div class="when"><b>{MONTHS[h['month'] - 1][:3]}</b>{h.get('day', '') or ''}</div>
        <div><h3>{e(h['title'])}</h3><p>{e(h['note'])}</p>{'<p class="warn-note">Plan around this</p>' if h.get('warning') else ''}</div></li>'''
        for h in g['holidays'])

    good = []
    if g['payment']:
        good.append(('Paying', g['payment']))
    if g['dutyFree']:
        good.append(('Duty-free alcohol', g['dutyFree']))
    if g.get('budgetAirlines'):
        good.append(('Budget airlines from Singapore', g['budgetAirlines']))
    good_html = ''.join(f'<div class="row"><span>{e(k)}</span><p>{e(v)}</p></div>' for k, v in good)

    flights = ''
    if g['nonstopFrom']:
        more = g['nonstopCount'] - len(g['nonstopFrom'])
        flights = ('<section class="block"><h2>Nonstop flights</h2>'
                   f'<p class="muted">{e(g["name"])} has nonstop flights from {g["nonstopCount"]} cities. The shortest:</p><div class="routes">'
                   + ''.join(f'<div class="route"><span>{e(c)}</span><b>{hours(m)}</b></div>' for c, m in g['nonstopFrom'])
                   + '</div>' + (f'<p class="muted small">And {more} more.</p>' if more > 0 else '') + '</section>')

    fare_note = ''
    if g.get('fromSingapore'):
        f = g['fromSingapore']
        fare_note = (f'<p class="muted small">Fare: cheapest one-way price seen recently from Singapore with {e(f["airline"])}, '
                     f'for travel on {e(f["seen"])}, in Singapore dollars. Prices change all the time; the real price is the one on the booking site.</p>')

    desc = f'{g["name"]}, {g["country"]} travel guide. Famous for: {g["famousFor"]}. Festivals by month, money, plugs and nonstop flights.'
    body = f'''<main>
<section class="g-hero">
  <div class="wrap">
    <p class="crumbs"><a href="index.html">Travel guides</a> / {e(g['country'])}</p>
    <h1>{e(g['name'])}</h1>
    <p class="famous">Famous for</p>
    <p class="lead">{e(g['famousFor'])}.</p>
    <div class="chips">{vibe_chips(g)}</div>
    <div class="facts-row">{facts_html}</div>
  </div>
</section>
<div class="wrap g-body">
  <div class="g-main">
    {trend}
    <section class="block"><h2>Festivals and holidays</h2><p class="muted">What's on in {e(g['name'])} through the year, and when to plan around closures.</p><ul class="events">{events}</ul></section>
    {flights}
    <section class="block"><h2>Good to know</h2><div class="rows">{good_html}</div>{fare_note}</section>
    <p class="muted small">This guide is a starting point. Visa rules, holidays and prices change, so always check with the airline and official government sources before you book.</p>
  </div>
  <aside class="g-side">
    <div class="side-card">
      <h3>Can you go?</h3>
      <p>{e(NAME)} checks {e(g['name'])} against your passport and budget, and plans the trip day by day.</p>
      <p class="badge">Coming soon to iOS and Android</p>
      <a class="btn" href="../index.html">See the app</a>
    </div>
  </aside>
</div>
</main>'''
    return page(f'guides/{g["slug"]}.html', f'{g["name"]}, {g["country"]} travel guide', desc, body, depth=1)


for g in guides:
    written.append(guide_page(g))

# Guides index
by_country = {}
for g in guides:
    by_country.setdefault(g['country'], []).append(g)
all_vibes = sorted({v for g in guides for v in g['vibes']})


def card(g, extra=''):
    return (f'<a class="g-card" href="{g["slug"]}.html" data-name="{e((g["name"] + " " + g["country"]).lower())}" '
            f'data-vibes="{e("|".join(g["vibes"]))}"><b>{e(g["name"])}</b><span>{e(g["famousFor"])}</span>{extra}</a>')


sin_list = sorted([g for g in guides if g.get('flightFromSingapore')], key=lambda g: g['flightFromSingapore'])
sin_cards = ''.join(card(g, f'<em>{hours(g["flightFromSingapore"] * 60)} from Singapore'
                           + (f' · from S${g["fromSingapore"]["fare"]}' if g.get('fromSingapore') else '') + '</em>')
                    for g in sin_list[:12])
country_html = ''.join(
    f'<section class="country" data-country><h2>{e(c)} <small>{len(gs)}</small></h2><div class="g-grid">{"".join(card(g) for g in gs)}</div></section>'
    for c, gs in sorted(by_country.items()))
vibe_buttons = ''.join(f'<button type="button" class="chip" data-vibe="{e(v)}" aria-pressed="false">{e(v)}</button>' for v in all_vibes)

guides_index = f'''<main>
<section class="g-hero">
  <div class="wrap">
    <p class="eyebrow">Travel guides</p>
    <h1>{len(guides)} places, explained in a minute.</h1>
    <p class="lead">What each place is famous for, the festivals and holidays month by month, money and plugs, and where you can fly from nonstop.</p>
  </div>
</section>
<div class="wrap">
  <section class="block">
    <h2>Quick trips from Singapore</h2>
    <div class="g-grid">{sin_cards}</div>
  </section>
  <section class="block">
    <h2>All guides</h2>
    <div class="filter">
      <input id="q" type="search" placeholder="Search a city or country" aria-label="Search guides">
      <div class="chips" id="vibes">{vibe_buttons}</div>
      <p class="muted small" id="count"></p>
    </div>
    {country_html}
  </section>
</div>
<script>
(function(){{
  var q=document.getElementById('q'),vb=document.getElementById('vibes'),count=document.getElementById('count');
  var picked=new Set();
  function run(){{
    var t=q.value.trim().toLowerCase(),n=0;
    document.querySelectorAll('[data-country]').forEach(function(sec){{
      var shown=0;
      sec.querySelectorAll('.g-card').forEach(function(c){{
        var ok=(!t||c.dataset.name.indexOf(t)>-1);
        if(ok&&picked.size){{var vs=c.dataset.vibes.split('|');ok=vs.some(function(v){{return picked.has(v)}});}}
        c.hidden=!ok; if(ok){{shown++;n++;}}
      }});
      sec.hidden=!shown;
    }});
    count.textContent=(t||picked.size)?n+' guides match':'';
  }}
  q.addEventListener('input',run);
  vb.addEventListener('click',function(ev){{
    var b=ev.target.closest('button'); if(!b)return;
    var v=b.dataset.vibe; if(picked.has(v)){{picked.delete(v);b.setAttribute('aria-pressed','false');}}else{{picked.add(v);b.setAttribute('aria-pressed','true');}}
    run();
  }});
}})();
</script>
</main>'''
written.append(page('guides/index.html', 'Travel guides',
                    f'{len(guides)} city travel guides: what each place is famous for, festivals by month, money, plugs and nonstop flights.',
                    guides_index, depth=1))

# ---------------------------------------------------------------- home
teaser_cards = ''.join(card(g).replace('href="', 'href="guides/') for g in sin_list[:6])
teaser = f'''<section id="guides" class="section">
  <div class="wrap">
    <p class="eyebrow">Travel guides</p>
    <h2>Free guides to {len(guides)} places.</h2>
    <div class="g-grid">{teaser_cards}</div>
    <p style="margin-top:24px"><a class="btn" href="guides/index.html">Browse all travel guides</a></p>
  </div>
</section>'''
home = (ROOT / 'src' / 'index.html').read_text(encoding='utf-8')
home = home.replace('{{name}}', e(NAME)).replace('{{guides_teaser}}', teaser)
written.append(page('index.html', NAME,
                    f'{NAME} shows the places you can fly to on your budget, filtered by what your passport allows. Free travel guides to {len(guides)} places. Coming soon to iOS and Android.',
                    home, home=True))

# ---------------------------------------------------------------- about / contact
contact = contact_href()
contact_label = SITE['contactEmail'] or 'Send us a message'
written.append(doc_page('about.html', f'About {NAME}', f'Who makes {NAME} and why.', f'''
  <p>{e(NAME)} is a travel app made in Singapore for travellers across Asia. It answers the question every long weekend starts with: where can I actually go, with my passport, on my budget?</p>
  <h2>Why we built it</h2>
  <p>Planning a short trip usually means a dozen tabs: flight prices, visa rules, what the weather is like, whether a festival will close everything. {e(NAME)} puts that in one place. Pick a budget and a vibe, and you see only the places you can enter and afford, with a simple guide to each one.</p>
  <h2>What we offer</h2>
  <ul>
    <li>Free <a href="guides/index.html">travel guides</a> to {len(guides)} places, with festivals and holidays by month.</li>
    <li>A visa filter for all 199 passports.</li>
    <li>Round-trip price estimates and booking through trusted partners such as Aviasales, Trip.com, Agoda, Klook and GetYourGuide.</li>
    <li>Weekend and long-weekend shortcuts, and day-by-day trip plans.</li>
  </ul>
  <h2>How we make money</h2>
  <p>{e(NAME)} is free. We earn a small commission when you book through our partner links, at no extra cost to you, and offer an optional Pro upgrade. We never sell your data. See our <a href="privacy.html">privacy policy</a>.</p>
  <h2>Our information</h2>
  <p>Guides are written by our team with AI help and checked against public sources. Visa rules and prices change, so we always point you to official sources before you book. Spotted a mistake? <a href="contact.html">Tell us</a>.</p>'''))

written.append(doc_page('contact.html', 'Contact', f'How to contact {NAME}.', f'''
  <p>We'd love to hear from you, whether it's feedback on the app, a mistake in a guide, or a partnership idea.</p>
  <p><a class="btn" href="{e(contact)}">{e(contact_label)}</a></p>
  <h2>Partners and press</h2>
  <p>Travel brands, tourism boards and creators are welcome to get in touch about working together.</p>
  <h2>Corrections</h2>
  <p>If a visa rule, holiday date or tip in one of our guides is wrong, please tell us which page and what changed, and we'll fix it.</p>'''))

# ---------------------------------------------------------------- privacy / terms
written.append(doc_page('privacy.html', 'Privacy policy', f'Privacy policy for the {NAME} app and website.', f'''
  <p>{e(NAME)} ("we", "the app") helps you find places to fly to by budget, travel style and passport. We collect as little as we can. This policy covers the app and this website.</p>
  <h2>What you can use without an account</h2>
  <p>You can explore destinations, prices, visa information and city guides without signing up. Your choices, such as departure city, passport, dates, budget and vibes, stay on your device.</p>
  <h2>If you create an account</h2>
  <p>You can sign in with Apple, Google or email to save the places you have been and your trip plans. We then store your email address or sign-in ID and the places and plans you save, so they are there on your other devices. We do not sell this information.</p>
  <h2>Travel partners and booking links</h2>
  <p>When you tap to check flights, hotels or tours, you leave the app or this website and go to a partner site (for example Aviasales, Trip.com, Agoda, Klook or GetYourGuide) through our partner network, Travelpayouts. That site's own privacy policy applies there. Some of these links are affiliate links: we may earn a small commission at no extra cost to you. Partner sites may use cookies to know the booking came from us. We do not see your payment details.</p>
  <h2>Ads</h2>
  <p>The free version of the app may show ads from an ad network such as Google AdMob. The ad network may use a device advertising ID to show and measure ads. You can limit ad tracking in your phone's settings. Pro removes ads once that feature is available.</p>
  <h2>Purchases</h2>
  <p>Pro is bought through the App Store or Google Play. Apple or Google handle the payment, and we only receive confirmation that you have Pro.</p>
  <h2>Crash and usage data</h2>
  <p>We may collect anonymous crash reports and basic usage numbers to fix bugs and improve the app. These do not identify you.</p>
  <h2>This website</h2>
  <p>This site does not set its own cookies or use tracking. Our web host may keep standard server logs, such as IP addresses, for security.</p>
  <h2>Your choices</h2>
  <ul>
    <li>You can use the app without an account.</li>
    <li>You can delete your account and saved data at any time in the app, or by contacting us.</li>
    <li>You can ask us what data we hold about you.</li>
  </ul>
  <h2>Children</h2>
  <p>The app is not aimed at children under 13, and we do not knowingly collect their data.</p>
  <h2>Changes</h2>
  <p>If we change this policy, we will update the date at the top of this page.</p>
  <h2>Contact</h2>
  <p>Questions about privacy? <a href="contact.html">Contact us</a>.</p>'''))

written.append(doc_page('terms.html', 'Terms of use', f'Terms of use for the {NAME} app and website.', f'''
  <p>These terms apply when you use the {e(NAME)} app or this website. By using them you agree to these terms. If you get the app from the App Store, Apple's <a href="https://www.apple.com/legal/internet-services/itunes/dev/stdeula/">standard licence agreement</a> applies too.</p>
  <h2>Travel information is a guide</h2>
  <p>Visa rules, flight times, prices, holidays, weather and city tips come from public sources and our own drafts. They can be out of date or wrong. Always check with the airline, the embassy or official government sources before you book or travel. We are not responsible for a trip that goes wrong because of information in the app or on this website.</p>
  <h2>Prices</h2>
  <p>Prices are recent fares seen by our partners, shown as a guide. The real price is the one on the booking site when you book, and it can be higher.</p>
  <h2>Booking with partners</h2>
  <p>When you book flights, hotels or tours, you book with that partner (for example Aviasales, Trip.com, Agoda, Klook or GetYourGuide), not with us. Their terms, prices and refund rules apply. Some links are affiliate links, so we may earn a small commission at no extra cost to you.</p>
  <h2>Pro</h2>
  <p>Pro is sold through the App Store or Google Play as a monthly subscription or a one-time lifetime purchase. Monthly plans renew automatically until you cancel in your App Store or Google Play account settings, at least 24 hours before the next renewal. Refunds are handled by Apple or Google under their rules. "Lifetime" means for as long as we offer the app.</p>
  <h2>Fair use</h2>
  <p>Please don't copy the app's or this website's content in bulk, break the app, or use it for anything illegal.</p>
  <h2>Changes</h2>
  <p>We may update the app and these terms. If we change the terms, we will update the date at the top of this page.</p>
  <h2>Contact</h2>
  <p>Questions? <a href="contact.html">Contact us</a>. See also our <a href="privacy.html">privacy policy</a>.</p>'''))

page('404.html', 'Page not found', 'This page does not exist.',
     f'<main class="wrap doc"><h1>Page not found</h1><p>That page has moved or never existed. Try the <a href="{BASE}/">home page</a> or our <a href="{BASE}/guides/">travel guides</a>.</p></main>',
     up=BASE + '/')

# ---------------------------------------------------------------- sitemap, robots, CNAME
urls = []
for p in written:
    loc = BASE + '/' + p
    loc = loc[:-len('index.html')] if loc.endswith('index.html') else loc
    urls.append(f'  <url><loc>{e(loc)}</loc><lastmod>{date.today().isoformat()}</lastmod></url>')
(ROOT / 'sitemap.xml').write_text(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + '\n'.join(sorted(urls)) + '\n</urlset>\n', encoding='utf-8')
(ROOT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n', encoding='utf-8')

host = urlparse(BASE).hostname or ''
cname = ROOT / 'CNAME'
if host.endswith('github.io'):
    cname.unlink(missing_ok=True)
else:
    cname.write_text(host + '\n', encoding='utf-8')

print(f'Built {len(written)} pages ({len(guides)} guides) for {NAME} at {BASE}')
