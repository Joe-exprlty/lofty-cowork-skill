# Hosting the Setup Web App

The `index.html` in this folder is a complete standalone web app that walks new users through installing the Lofty + Cowork skill. It has no build step, no dependencies you need to install, and no server. You just need somewhere to host the static file.

Three free options below, easiest first.

---

## Option 1: GitHub Pages from this repo (recommended, 5 minutes)

GitHub Pages serves static files for free directly from your repo. Since this app already lives in the `docs/` folder, you just need to flip a switch.

1. Go to your repo on GitHub: `github.com/Joe-exprealty/lofty-cowork-skill`
2. Click the **Settings** tab (top of the page, on the right).
3. In the left sidebar, click **Pages**.
4. Under "Build and deployment", set:
   - **Source:** Deploy from a branch
   - **Branch:** `main` and `/docs`
   - Click **Save**.
5. Wait 1 to 2 minutes. GitHub builds the page.
6. Refresh the Settings → Pages screen. You'll see a green banner with a URL like:
   ```
   https://joe-exprealty.github.io/lofty-cowork-skill/
   ```
7. That's your live web app. Share that URL with anyone you want to onboard.

If you want a custom domain (like `setup.sellingpdxhomes.com`), GitHub Pages supports that too. Settings → Pages has a Custom domain field. You'd need to add a DNS CNAME record at your domain registrar pointing to `joe-exprealty.github.io`.

---

## Option 2: Cloudflare Pages

Slightly more powerful (analytics, faster CDN, password protection if you want it). Free tier is generous.

1. Go to dash.cloudflare.com, choose Workers & Pages, click Create.
2. Connect your GitHub account.
3. Pick the `lofty-cowork-skill` repo.
4. Build settings:
   - Build command: leave blank (no build needed)
   - Output directory: `docs`
5. Click Save and Deploy.

You get a URL like `lofty-cowork-skill.pages.dev` and a CDN-cached site. You can attach a custom domain later if you want.

---

## Option 3: Netlify, Vercel, or any other static host

Same idea as Cloudflare Pages. Connect the repo, set the publish directory to `docs/`, deploy.

For a "drop the file somewhere" approach, you can also put `index.html` on your existing website. Anywhere a static HTML file can sit, this app works. It only needs to be served over HTTPS for the clipboard buttons to work in modern browsers.

---

## Updating the app

When you change `index.html`, commit and push to main. GitHub Pages (and Cloudflare Pages, if you connected the repo) rebuilds automatically. Updates go live within a minute or two.

To preview changes locally before pushing, just open the file in a browser:

```bash
open /Users/joesaling/Code/lofty-cowork-skill/docs/index.html
```

That works because the app uses CDNs (Tailwind, Google Fonts) and has no local build dependencies. Pure HTML, CSS, and vanilla JavaScript.

---

## What's in the app

- Hero section with download CTA
- "What you can do" feature grid
- Interactive prerequisites checklist
- OS picker (Mac / Windows / Linux) that adjusts commands automatically
- Six-step setup walkthrough with copy-to-clipboard buttons
- Sample prompts to try, each copy-to-clipboard
- Top 5 quirks and safety habits
- Help section with links to repo, install guide, full guide, direct download
- Your contact footer

The app auto-detects the visitor's OS and sets the right tab on load. If they're on Windows, the `mkdir -p` command stays hidden and the PowerShell `New-Item` shows instead.

---

## A note about hyperlinks

Every link in the app uses your repo URL `Joe-exprealty/lofty-cowork-skill`. If your actual GitHub username spells differently, do a find-and-replace in `index.html` for `Joe-exprealty` and replace with the right spelling.

Same goes for `joe@sellingpdxhomes.com`, `(503) 910-7364`, and `sellingpdxhomes.com` if any of those change.
