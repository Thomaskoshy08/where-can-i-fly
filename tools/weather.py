"""Daily weather for every place in the app, from Apple WeatherKit.

Run once a day by .github/workflows/weather.yml. The app downloads the files
this writes from the website, so WeatherKit is called once per place per day
(about 2,700 calls), however many people use the app.

Writes:
  _site/data/weather.json   10-day forecast for every place (not committed)
  data/climate.json         usual weather for each month, built from last
                            year's weather; a few months are refreshed each
                            run and the file is committed
  _site/data/apple-weather-*.png   the Apple Weather mark the app must show

Needs these environment variables (GitHub secrets):
  WEATHERKIT_KEY         the .p8 key file's text
  WEATHERKIT_KEY_ID      its Key ID
  WEATHERKIT_TEAM_ID     the Apple Developer Team ID
  WEATHERKIT_SERVICE_ID  the Services ID, e.g. com.projectpace.whereCanIFly.weather

Optional: CLIMATE_BUDGET (default 25000) caps the extra calls for climate per
run, so the first fill spreads over a few days and stays well inside the
500,000 free calls a month.
"""
import calendar
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import jwt  # PyJWT
from timezonefinder import TimezoneFinder

PLACES_URL = 'https://raw.githubusercontent.com/thomaskoshy08/project-pace/main/assets/data/world/places.json'
API = 'https://weatherkit.apple.com/api/v1'
ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / '_site' / 'data'
CLIMATE = ROOT / 'data' / 'climate.json'
WORKERS = 8

# WeatherKit condition codes as WMO codes, which the app already draws.
WMO = {
    'Clear': 0, 'MostlyClear': 1, 'PartlyCloudy': 2, 'MostlyCloudy': 3, 'Cloudy': 3,
    'Foggy': 45, 'Haze': 45, 'Smoky': 45, 'Dust': 45, 'Breezy': 1, 'Windy': 2,
    'Drizzle': 53, 'FreezingDrizzle': 56,
    'Rain': 63, 'SunShowers': 80, 'HeavyRain': 65, 'FreezingRain': 66, 'Showers': 80,
    'Sleet': 67, 'WintryMix': 67, 'Hail': 96,
    'Flurries': 71, 'Snow': 73, 'SunFlurries': 85, 'HeavySnow': 75, 'BlowingSnow': 75, 'Blizzard': 75,
    'ScatteredThunderstorms': 95, 'IsolatedThunderstorms': 95, 'Thunderstorms': 95,
    'StrongStorms': 95, 'Hot': 0, 'Frigid': 0,
    'TropicalStorm': 95, 'Hurricane': 95,
}


def token():
    team = os.environ['WEATHERKIT_TEAM_ID']
    service = os.environ['WEATHERKIT_SERVICE_ID']
    now = int(time.time())
    return jwt.encode(
        {'iss': team, 'iat': now, 'exp': now + 3600 * 6, 'sub': service},
        os.environ['WEATHERKIT_KEY'],
        algorithm='ES256',
        headers={'kid': os.environ['WEATHERKIT_KEY_ID'], 'id': f'{team}.{service}'},
    )


TOKEN = None
CALLS = 0


def get(url, auth=True):
    global CALLS
    headers = {'Authorization': f'Bearer {TOKEN}'} if auth else {}
    for attempt in range(4):
        try:
            CALLS += 1
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 404):
                raise
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(2 ** attempt * 2)
    raise RuntimeError(f'gave up on {url}')


def days_for(lat, lon, tz, start=None, end=None):
    q = f'dataSets=forecastDaily&timezone={tz}'
    if start:
        q += f'&dailyStart={start}T00:00:00Z&dailyEnd={end}T00:00:00Z'
    body = json.loads(get(f'{API}/weather/en/{lat:.3f}/{lon:.3f}?{q}'))
    return body.get('forecastDaily', {}).get('days', [])


def forecast(place):
    pid, p, tz = place
    try:
        days = days_for(p['lat'], p['lon'], tz)
    except Exception as e:  # one bad place shouldn't stop the rest
        print(f'  {pid}: {e}', file=sys.stderr)
        return pid, None
    if not days:
        return pid, None
    return pid, [
        days[0]['forecastStart'][:10],
        [WMO.get(d.get('conditionCode'), 2) for d in days],
        [round(d['temperatureMax']) for d in days],
        [round(d['temperatureMin']) for d in days],
        [round(100 * d.get('precipitationChance', 0)) for d in days],
    ]


def month_summary(place, year, month):
    """Usual weather for one month: [code, max, min, % of rainy days]."""
    pid, p, tz = place
    last = calendar.monthrange(year, month)[1]
    days = []
    # Ten days a request, the length of a forecast, to be safe.
    for first in range(1, last + 1, 10):
        start = dt.date(year, month, first)
        end = min(start + dt.timedelta(days=10), dt.date(year, month, last) + dt.timedelta(days=1))
        days += days_for(p['lat'], p['lon'], tz, start.isoformat(), end.isoformat())
    if not days:
        return None
    n = len(days)
    rainy = sum(1 for d in days if d.get('precipitationAmount', 0) >= 2 or d.get('precipitationChance', 0) >= 0.5)
    code = Counter(WMO.get(d.get('conditionCode'), 2) for d in days).most_common(1)[0][0]
    return [
        code,
        round(sum(d['temperatureMax'] for d in days) / n),
        round(sum(d['temperatureMin'] for d in days) / n),
        round(100 * rainy / n),
    ]


def update_climate(places, budget):
    """Refreshes the months that are missing or more than a year old."""
    climate = json.loads(CLIMATE.read_text()) if CLIMATE.exists() else {'months': {}, 'places': {}}
    today = dt.date.today()
    paused = climate.get('historyUnavailable')
    if paused and (today - dt.date.fromisoformat(paused)).days < 30:
        print(f'climate: history was unavailable on {paused}; trying again 30 days later')
        return
    # Each month comes from its latest finished occurrence, e.g. in Nov 2026:
    # Nov 2025, Dec 2025, ... Oct 2026.
    wanted = []
    for m in range(1, 13):
        year = today.year if m < today.month else today.year - 1
        if climate['months'].get(str(m)) != f'{year}-{m:02d}':
            wanted.append((year, m))
    per_place = 4
    for year, m in wanted:
        cost = per_place * len(places)
        if cost > budget:
            print(f'climate: {year}-{m:02d} waits for the next run (budget left {budget})')
            break
        print(f'climate: building {year}-{m:02d}')
        with ThreadPoolExecutor(WORKERS) as pool:
            results = list(pool.map(lambda pl: (pl[0], safe(month_summary, pl, year, m)), places))
        got = 0
        for pid, summary in results:
            if summary:
                climate['places'].setdefault(pid, [None] * 12)[m - 1] = summary
                got += 1
        if got < len(places) // 2:
            # Don't spend calls every day on history WeatherKit won't give.
            print(f'climate: only {got} places for {year}-{m:02d}; pausing for 30 days.')
            climate['historyUnavailable'] = today.isoformat()
            break
        climate.pop('historyUnavailable', None)
        climate['months'][str(m)] = f'{year}-{m:02d}'
        budget -= cost
    climate['source'] = 'Apple Weather, average of each month over the past year'
    CLIMATE.parent.mkdir(exist_ok=True)
    CLIMATE.write_text(json.dumps(climate, separators=(',', ':'), sort_keys=True) + '\n')


def safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        print(f'  {args[0][0]}: {e}', file=sys.stderr)
        return None


def save_logos():
    """The Apple Weather mark the app must show next to the weather."""
    info = json.loads(get('https://weatherkit.apple.com/attribution/en', auth=False))
    for key, name in (('logoLight3x', 'apple-weather-light.png'), ('logoDark3x', 'apple-weather-dark.png')):
        url = info.get(key)
        if url:
            if url.startswith('/'):
                url = 'https://weatherkit.apple.com' + url
            (SITE / name).write_bytes(get(url, auth=False))
    (SITE / 'apple-weather.json').write_text(
        json.dumps({'legalPageURL': info.get('legalPageURL', 'https://weatherkit.apple.com/legal-attribution.html')})
    )


def main():
    global TOKEN
    TOKEN = token()
    SITE.mkdir(parents=True, exist_ok=True)
    raw = json.loads(urllib.request.urlopen(PLACES_URL, timeout=60).read())['places']
    tf = TimezoneFinder()
    places = []
    for pid, p in sorted(raw.items()):
        tz = tf.timezone_at(lat=p['lat'], lng=p['lon']) or 'UTC'
        places.append((pid, p, tz))
    print(f'{len(places)} places')

    with ThreadPoolExecutor(WORKERS) as pool:
        results = dict(pool.map(forecast, places))
    got = {k: v for k, v in results.items() if v}
    print(f'forecast: {len(got)} of {len(places)} places, {CALLS} calls')
    if len(got) < len(places) // 2:
        sys.exit('Too few forecasts; not publishing.')
    (SITE / 'weather.json').write_text(
        json.dumps(
            {'source': 'Apple Weather', 'updated': dt.datetime.now(dt.timezone.utc).isoformat(timespec='minutes'),
             'places': got},
            separators=(',', ':'),
        )
    )

    try:
        save_logos()
    except Exception as e:
        print(f'logos: {e}', file=sys.stderr)

    update_climate(places, int(os.environ.get('CLIMATE_BUDGET', '25000')))
    print(f'done, {CALLS} calls in all')


if __name__ == '__main__':
    main()
