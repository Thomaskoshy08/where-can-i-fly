# Where Can I Fly website

Website for the Where Can I Fly app: landing page, 361 free city travel guides, About, Contact, Privacy and Terms.

Live site: https://thomaskoshy08.github.io/where-can-i-fly/

## How it's built

The pages are plain HTML made by one script. Don't edit the generated `.html` files by hand; change the source and rebuild:

    python3 tools/build_site.py

- `site.json`: app name, tagline, web address and contact email. **Change the name or move to your own domain here**, then rebuild.
- `src/index.html`: home page body (`{{name}}` becomes the app name).
- `data/guides.json`: city guides, copied from the app. Refresh with `python3 tools/import_guides.py ../project-pace`, then rebuild.
- `style.css`: styles (light and dark mode). `img/`: app screenshots.
- Generated: `index.html`, `about.html`, `contact.html`, `privacy.html`, `terms.html`, `404.html`, `guides/`, `sitemap.xml`, `robots.txt`, and `CNAME` when `site.json` uses your own domain.

## Moving to your own domain

1. Buy the domain (for example from Cloudflare, Namecheap or Porkbun).
2. At the domain seller, add DNS records: four `A` records for `@` pointing to 185.199.108.153, 185.199.109.153, 185.199.110.153 and 185.199.111.153, and a `CNAME` record for `www` pointing to `thomaskoshy08.github.io`.
3. Set `"url"` in `site.json` to `https://yourdomain.com`, run the build, and merge. This writes the `CNAME` file.
4. In GitHub: Settings > Pages > Custom domain, enter the domain, Save, and tick "Enforce HTTPS" once it's offered.
5. Update the website address in Travelpayouts.
