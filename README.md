# Johanna L — art website

A Wagtail (Django) site for Johanna's watercolour work: gallery, shop (originals, prints,
digital downloads), commissions, blog — in **English and German**, with a light/dark mode
and five colour palettes. Johanna manages everything from the Wagtail admin; no code needed.

| Doc | For |
|---|---|
| [`docs/ADMIN_GUIDE.md`](docs/ADMIN_GUIDE.md) | Johanna — how to run the site day to day |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | Putting it online, backups, updates, local development |

## What's inside

- **Gallery & shop** — artworks with "ways to buy": original (one-of-a-kind), prints
  (sizes, stock counts), digital downloads (private files, released after payment)
- **Orders** — cart, guest checkout (accounts optional), manual PayPal/bank payment,
  status flow with automatic emails, stock & sold counters, shipping zones & prices
- **Commissions** — request form with reference photo, quote → in progress → shipped
  workflow, private status page for the customer
- **Blog** — posts, tags, RSS
- **Admin dashboard** — what needs attention, plus launch warnings
- **i18n** — English at `/`, German at `/de/`; page translations edited side by side
- **Appearance** — Light/Dark/Auto + 5 palettes, remembered per visitor
- **Privacy-friendly** — self-hosted fonts, no tracking cookies

## Layout

```
src/        Django project (config/, home/, artworks/, shop/, blog/, contact/, tools/)
deploy/     docker-compose, Caddy (HTTPS), backup script, .env.example
docs/       guides
```

Quick start and tests: see *Local development* in `docs/DEPLOY.md`.
