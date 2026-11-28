# Where Can I Fly

Website for the Where Can I Fly app: visa-friendly trips by budget, from Asia. Coming soon to iOS and Android.

Live site: https://thomaskoshy08.github.io/where-can-i-fly/

- `index.html`: landing page
- `privacy.html`: privacy policy
- `style.css`: styles (light and dark mode)
- `img/`: app screenshots
- `data/climate.json`: usual weather per month for every place (built by the weather job)
- `tools/weather.py` and `.github/workflows/weather.yml`: once a day, fetch the 10-day forecast for every place from Apple WeatherKit and publish the site with `data/weather.json`, which the app downloads. This job also publishes the site, so Settings > Pages > Source must be "GitHub Actions". It needs the secrets `WEATHERKIT_KEY`, `WEATHERKIT_KEY_ID`, `WEATHERKIT_TEAM_ID` and `WEATHERKIT_SERVICE_ID`.
