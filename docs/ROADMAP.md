# Roadmap — making the site truly Johanna's

What exists, what we need from Johanna, and what can still be built.
Status: ✅ done · 🟡 partly · ⬜ not started · 🔒 blocked until we get something

---

## 1. What we need (checklist)

### From Johanna — her work and voice
- [ ] 8–15 full-resolution photos/scans of paintings, straight-on, even light
- [ ] For 2–3 of them: a photo of the pencil sketch / first wash, same angle (for the layers slider)
- [ ] Process photos or short clips: paints, brushes, desk, hands working
- [ ] Her 3 favourite pieces (hero and homepage)
- [ ] 3–5 artists/sites she likes and 2–3 she doesn't (tells us her taste)
- [ ] The pigments she uses most (builds her own colour palette)
- [ ] Mood: airy/white paper, or warm/moody?
- [ ] A handwriting sample (sentence, dark pen, white paper, photo or scan) and her signature a few times
- [ ] Optional: a motif she always draws (leaf, house, bird) → logo/loading mark
- [ ] A paragraph or two about her in her own words, and a good photo of her / her studio
- [ ] Places she has painted, with rough location (sketchbook map)

### From Johanna and you — shop and legal
- [ ] Prices, print sizes, paper type, shipping prices
- [ ] Real PayPal email / PayPal.me name, IBAN for bank transfer, notification email
- [ ] Impressum details (full name, address, contact) — **required by German law**
- [ ] Legal texts checked by a professional or a reputable generator (Impressum, Datenschutz, AGB, Widerruf/returns)
- [ ] Decide if she is a *Kleinunternehmer* (§19 UStG, no VAT) — affects invoices and the shop setting

### From you — launch
- [ ] Domain (a `.de` or `.art` name), mailbox (e.g. `hello@domain`), SMTP details
- [ ] A small VPS (≈ €4–6/month) — see `DEPLOY.md`
- [ ] Off-server backup target (Backblaze B2 / Google Drive) and server snapshots

---

## 2a. Added in the second round ✅

Privacy-friendly **Insights** (visits, hearts, carts, referrers) · **Instagram** strip and footer
link, hand-picked or automatic · **Newsletter** with double opt-in · **Discount codes, free-shipping
codes and gift cards** · **Waiting list** for sold-out work · **PDF invoices and packing slips**
with sequential numbers · **CSV/Excel exports** · **Morning digest email** and daily scheduler ·
**Commission tools** (progress photos, deposit, visual size picker with rough price) ·
**Collections** · **Customer reviews** with approval · **Video block** (own file or click-to-load
YouTube) · **Wall preview** · **Sketchbook map** · gallery filters without page reloads ·
watercolour bloom image reveal · styled error pages · one-click light/dark button.

Still open: real automatic payments (needs her PayPal/Stripe account and keys), real handwriting,
palette and photos (see section 1), selling gift cards as a product (gift card codes can be created
by hand today).

## 2. What is built ✅

| Area | Details |
|---|---|
| Gallery & shop | Artworks, ways to buy (original / prints with stock / digital download), cart, guest checkout, accounts optional |
| Orders | Manual PayPal/bank flow, statuses, emails EN/DE, stock and sold counters, shipping zones |
| Commissions | Request form with reference photo, quote → in progress → shipped, private status page |
| Blog | Posts, tags, RSS |
| Languages | English `/` and German `/de/`, side-by-side translation in the admin |
| Look | Light/dark/auto + 5 colour palettes, self-hosted fonts, animations, mobile layout |
| Her touch | Name & signature, "Just keep layering" sketch-to-finished slider, automatic colour swatches from each painting, brush-wash page transitions |
| Performance | Subsetted fonts, no heavy blur filters, lazy images with painting-coloured placeholders, link prefetch |
| SEO | Sitemap, share images, product structured data |
| Control for Johanna | **Price visibility per artwork** (see §4), draft/publish, dashboard with to-dos |

---

## 3. Design, colour and visual ideas

Order is rough priority (impact on "this is hers" vs. effort).

### High impact
1. **Her real palette** — a sixth theme built from her actual pigments and paintings, set as default. ⬜ 🔒 needs her paintings/pigments
2. **Her handwriting** — logo, signature, captions and a few headings from her scanned writing (SVG, tiny file). ⬜ 🔒 handwriting sample
3. **Real watercolour textures** — scans of her paper (cold-press grain) and a few real brush-stroke washes as backgrounds, replacing generated gradients. ⬜ 🔒 scans
4. **Sketchbook map** — a hand-drawn map with a pin per place; pins open the artworks painted there. ⬜ 🔒 place list
5. **Layered hero** — homepage hero that builds a painting in three layers (sketch → wash → detail) as the page loads. 🟡 mechanism exists, needs real images
6. **Paint-in-water reveal** on artwork images (colour blooms across the image as it scrolls in). ⬜

### Medium impact
7. **"Behind the painting" panel** per artwork: story, materials, time spent, process photos in a horizontal scroller. 🟡 story exists
8. **View on your wall** — visitors upload a wall photo (processed in the browser, never uploaded) and see a print at true scale. ⬜
9. **Gallery as a masonry/"pinboard"** layout with filters that update without reloading. ⬜
10. **Watercolour-style loading mark** and favicon from her motif. ⬜
11. **Seasonal/featured collections** ("Summer in Portugal") with their own colour wash. ⬜
12. **Dark mode palettes tuned per palette** (contrast audit of all 5 × 2 combinations). ⬜
13. **Print/commission size picker** with a visual scale (hand next to the artwork). ⬜

### Polish
14. Custom brush cursor (desktop only, optional). ⬜
15. Sound-free micro-interactions: cart button "dips" into the bag, swatches bleed on hover. 🟡
16. Print-ready stylesheet for blog posts. ⬜
17. Gift options: handwritten note, gift wrap, gift card. ⬜

---

## 4. Johanna decides what is public

### Price: show or "on request" ✅
On every artwork there is a tick box **"show price and allow buying"** (Gallery settings).
- Ticked (default): price shown, cart and checkout work.
- Unticked: no price anywhere (cards, pages, structured data); the page shows *Price on request* with an *Ask for the price* button that opens the contact form with the artwork pre-filled. Buying is **switched off server-side** too, so a hidden price cannot be bought by guessing a URL.
- Set it on the English page; the German page follows it automatically.

### Published or not ✅ (Wagtail built-in)
- **Save draft** keeps a page invisible; **Publish** makes it visible; **Unpublish** takes it down again.
- **Schedule:** *Settings → Go-live date / Expiry date* publishes or retires an artwork automatically.
- Per offer: untick **Active** to hide a single print size or the digital version.
- Status **Not for sale** shows the artwork as portfolio-only.

### Ideas to extend
- ⬜ "Notify me when available" email for sold/reserved pieces
- ⬜ Per-collection visibility (e.g. a hidden "friends & family" collection with a private link)

---

## 5. Instagram — can photos be linked automatically?

**Yes, with conditions.** Instagram has no free "just show my posts" feature; there are three ways:

| Option | How it works | Pros | Cons |
|---|---|---|---|
| **A. Official API (recommended)** | Her account must be a **Creator or Business** account (free to switch, in Instagram settings). We create a small Meta developer app and a long-lived access token. A scheduled job fetches her latest posts, **stores the images on our server**, and shows them in a "Latest from Instagram" strip. | Automatic, fast, privacy-friendly (visitors never contact Instagram until they click), matches the design | Token must be renewed about every 60 days (the job does this automatically); one-time setup; Instagram can change the API |
| **B. Third-party widget** (Behold, Elfsight …) | Paste an embed code | Easy | Loads external scripts (needs a cookie-consent banner in Germany), slower, looks generic, paid beyond a free tier |
| **C. Manual picks (works today, no account change)** | In the admin she chooses 6–9 photos and pastes the post links | Zero risk, fully designed, no consent issues | Not automatic |

**Plan:** build **C first** (a "From my Instagram" block she can add to any page; 1 day), then **A** once she has switched to a Creator account.
**What we need for A:** her Creator/Business account, her one-time "Log in with Instagram" approval, and 30 minutes together.

Also possible: link the other way — every artwork page gets a *Share* button and a pre-written caption she can paste into Instagram.

---

## 6. Technical to-do

### Before launch (must)
- [ ] Real payment details, shipping prices, legal pages published
- [ ] Test order end-to-end on the live server, then cancel it
- [ ] Domain + HTTPS + HSTS, email sending verified (SPF/DKIM so emails don't land in spam)
- [ ] Nightly backup **off-server**, and one practice restore
- [ ] Uptime monitor (UptimeRobot / Better Stack)
- [ ] Remove demo data (`seed_demo` is dev-only) and stop tracking `src/dev.sqlite3` in git

### Performance
- [ ] AVIF images next to WebP; responsive `srcset` everywhere
- [ ] Tiny blurred placeholders for big images (partly done via palette colour)
- [ ] Lighthouse pass (target 95+ on mobile) and accessibility check (contrast on all palettes, keyboard, screen reader)
- [ ] Cache headers / CDN (Cloudflare free) in front of the server

### Quality and growth
- [ ] Newsletter sign-up + "new work" email (double opt-in, GDPR)
- [ ] Cookie/consent notice only if third-party embeds are added (none today)
- [ ] Automatic payment (PayPal/Stripe/Klarna) — only "mark paid" changes, see `DEPLOY.md`
- [ ] Invoice PDF per order (needed for business sales)
- [ ] Order/inquiry export to CSV for the tax advisor
- [ ] Admin "to-do" email digest each morning
- [ ] More tests: German pages, hidden-price flow in the admin, upload edge cases

---

## 7. Suggested order of work

1. **Content pass** — Johanna's photos, handwriting, about text → real palette, hero, signature (biggest "hers" jump).
2. **Launch basics** — domain, server, legal, payment details, backups.
3. **Sketchbook map + layers on real pieces.**
4. **Instagram strip (manual), then automatic.**
5. **Newsletter, wall preview, collections.**
