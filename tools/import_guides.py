"""Copy the city guides from the app into data/guides.json for the website.

Run from this repository, with the app repository next to it:

    python3 tools/import_guides.py ../project-pace

It reads the app's guide, place, route and fare files and keeps only what the
guide pages show, so the website doesn't carry the app's large data files.
Then run `python3 tools/build_site.py` to rebuild the pages.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
app = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT.parent / 'project-pace')
data = app / 'assets' / 'data'


def load(p):
    return json.loads((data / p).read_text(encoding='utf-8'))


sin = load('destinations_sin.json')
world = load('guides_world.json')['destinations']
places = load('world/places.json')['places']
routes = load('world/routes.json')
fares = load('world/fares.json')

vibes = {s['id']: s['label'] for s in sin['styles']}

# Nonstop departures into each place: (city, minutes), from the route file.
arrivals = {}
for code, o in routes['origins'].items():
    for r in o['routes']:
        pid, minutes = r[0], r[1]
        arrivals.setdefault(pid, {})
        city = o['city']
        if city not in arrivals[pid] or minutes < arrivals[pid][city]:
            arrivals[pid][city] = minutes

sin_fares = fares['fares'].get('SIN', {})

guides = {}


def add(g, extra=None):
    pid = g['id']
    p = places.get(pid, {})
    name = g.get('name') or p.get('name')
    if not name or not g.get('famousFor') or not g.get('holidays'):
        return
    entry = {
        'id': pid,
        'name': name,
        'country': g.get('country') or p.get('country', ''),
        'iso': g.get('iso') or p.get('iso', ''),
        'currency': g.get('currency') or p.get('currency', ''),
        'famousFor': g['famousFor'],
        'vibes': [vibes[t] for t in g.get('tags', []) if t in vibes],
        'trending': g.get('trending', []),
        'holidays': sorted(g['holidays'], key=lambda h: (h['month'], h.get('day', 0))),
        'plug': g.get('plug', ''),
        'payment': g.get('payment', ''),
        'dutyFree': g.get('alcohol', ''),
    }
    deps = sorted(arrivals.get(pid, {}).items(), key=lambda kv: kv[1])
    entry['nonstopFrom'] = [[c, m] for c, m in deps[:12]]
    entry['nonstopCount'] = len(deps)
    if pid in sin_fares:
        f = sin_fares[pid]
        entry['fromSingapore'] = {'fare': f[0], 'airline': f[1], 'seen': f[2]}
    if extra:
        entry.update(extra)
    guides.setdefault(pid, entry)


for g in sin['destinations']:
    add(g, {'flightFromSingapore': g.get('hours'),
            'budgetAirlines': g.get('budgetAirlines', '')})
for g in world:
    add(g)

out = {
    'note': 'Copied from the app by tools/import_guides.py. Guides are drafts to verify; fares are cached Travelpayouts prices in SGD.',
    'routesChecked': routes.get('checked'),
    'faresChecked': fares.get('checked'),
    'guides': sorted(guides.values(), key=lambda g: (g['country'], g['name'])),
}
(ROOT / 'data').mkdir(exist_ok=True)
(ROOT / 'data' / 'guides.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'{len(guides)} guides written to data/guides.json')
