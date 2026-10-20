# Putting the site online

Goal: **always up, cheap, almost no maintenance.** For ~100 visitors a month, one small
server is plenty. This guide uses a small VPS running Docker, with **Caddy** handling
HTTPS certificates automatically.

**Cost:** server ≈ €4–6/month + domain ≈ €10–15/year + email (free tiers exist).

---

## 1. Things to get

| What | Suggestion |
|---|---|
| **Server (VPS)** | Hetzner Cloud *CX22* (≈ €4/mo, Germany), or any Ubuntu 24.04 VPS with 2 GB RAM |
| **Domain** | Cloudflare Registrar, Namecheap, INWX… (e.g. `johannal.art` — `.de` is great for a German audience) |
| **Mailbox** | Zoho Mail (free, custom domain) or Google Workspace → `hello@yourdomain` |
| **Sending emails** | The site sends order/commission emails. Use the SMTP details of your mailbox, or a free sender like Brevo / Resend |

## 2. Point the domain at the server

In your domain's DNS settings, create:

- `A` record: `@` → the server's IPv4 address
- `A` record: `www` → the same address (and `AAAA` for IPv6 if you have it)

Wait a few minutes. Caddy gets the HTTPS certificate on its own.

## 3. Prepare the server (once)

```bash
ssh root@YOUR_SERVER_IP
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
ufw allow OpenSSH && ufw allow 80 && ufw allow 443 && ufw --force enable
```

## 4. Get the code and configure

```bash
git clone git@github.com:psrajoria/johanna_art_site.git
cd johanna_art_site/deploy
cp .env.example .env
nano .env        # fill in domain, SECRET_KEY, email settings
```

Generate the `SECRET_KEY` with:
`python3 -c "import secrets; print(secrets.token_urlsafe(50))"`

## 5. Start it

```bash
docker compose up -d --build
```

First start takes a few minutes. Then create the pages and your login:

```bash
docker compose exec web python manage.py seed_site --domain yourdomain.com
docker compose exec web python manage.py createsuperuser     # Johanna's login
```

Open `https://yourdomain.com/admin/`, log in, and follow `docs/ADMIN_GUIDE.md`.
**Do not run `seed_demo`** — it only works in development and creates fake artwork.

### Before telling anyone
- [ ] Shop settings: real PayPal email / PayPal.me / IBAN, notification email
- [ ] Shipping prices
- [ ] Legal pages filled in, **checked**, and published (Impressum is mandatory in Germany)
- [ ] Site settings: footer, contact email, Instagram link, share image
- [ ] Place a **test order** end-to-end (then cancel it)
- [ ] Once HTTPS works: set `SECURE_HSTS_SECONDS=31536000` in `.env`, then `docker compose up -d`

## 6. Backups (important!)

Everything that can't be rebuilt — the database, artwork photos, digital download
files — lives in one Docker volume. Back it up every night:

```bash
chmod +x backup.sh
crontab -e
# add this line (backup at 03:15 every night):
15 3 * * * /root/johanna_art_site/deploy/backup.sh >> /var/log/johanna-backup.log 2>&1
```

This keeps 30 days of backups in `deploy/backups/` **on the same server**, which doesn't
help if the server dies. **Also copy them off the server** — e.g. with
[rclone](https://rclone.org) to Backblaze B2 (cheap) or Google Drive: uncomment the
`rclone` line in `backup.sh`. Many VPS providers also offer automatic server snapshots
(Hetzner: ≈ €1/month) — worth switching on as a second safety net.

**Restore** (new server, or after a disaster): do steps 3–5 *without* `seed_site`, then:

```bash
docker compose stop web
docker run --rm -v deploy_data:/data -v $PWD/backups:/backups alpine \
  sh -c "cd /tmp && tar xzf /backups/johanna-XXXX.tar.gz && cp db.sqlite3 /data/ && \
         rm -rf /data/media /data/private_media && cp -r media private_media /data/ 2>/dev/null; true"
docker compose up -d
```
(The volume name is `<folder>_data`; check with `docker volume ls`.)

## 7. Updating the site later

```bash
cd johanna_art_site && git pull
cd deploy && docker compose up -d --build
```
Database changes are applied automatically on start. A few seconds of downtime at most.

## 8. Is it healthy?

- `docker compose ps` — both services should be *running* (web also *healthy*)
- `docker compose logs -f web` — live log
- Free uptime monitoring: UptimeRobot or Better Stack pointed at `https://yourdomain.com/` —
  you get an email if it ever goes down.

---

## Local development (your computer)

```bash
cd src
python -m venv venv && venv\Scripts\activate      # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_site          # pages in EN + DE
python manage.py seed_demo          # fake artworks so you can see the design (dev only)
python manage.py createsuperuser
python manage.py runserver
```

- Site: http://localhost:8000 — Admin: http://localhost:8000/admin/
- Emails print in the terminal in development.
- Tests: `python manage.py test`
- After changing any text in templates/code: add the German in `src/tools/german.py`,
  then run `python tools/i18n.py build` (it lists anything missing).
- Preview a look: add `?theme=dark&palette=meadow` to any URL.

## Taking real payments later

Right now payment is manual (PayPal / bank, then "mark as paid"). To add automatic
card/PayPal/Klarna payments later, the only part that changes is "something marks the
order as paid" — that's `Order.status = paid`, which already does everything else
(stock, downloads, emails). A payment provider's webhook can simply call it.
