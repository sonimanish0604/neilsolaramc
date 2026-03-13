# DirectAdmin Deployment Guide

This repo now contains a static landing page at:

- `product/solar_sanchalak/site/index.html`
- `product/solar_sanchalak/site/styles.css`

The target public URL is:

- `https://software.nogginhausenergy.org`

## Step 1. Create the subdomain in DirectAdmin

From the dashboard shown in your screenshot:

1. Click `Subdomain Management`
2. Choose the domain `nogginhausenergy.org`
3. Create the subdomain name: `software`
4. Submit the form

Expected result:

- DirectAdmin creates `software.nogginhausenergy.org`
- It also creates a document root for that subdomain

Common document-root patterns in DirectAdmin are one of these:

- `domains/nogginhausenergy.org/public_html/software/`
- `domains/nogginhausenergy.org/subdomains/software/public_html/`

Use `File Manager` after creation to confirm which one your host uses.

## Step 2. Upload the website files

Upload these files from the repo into the subdomain's document root:

- `product/solar_sanchalak/site/index.html`
- `product/solar_sanchalak/site/styles.css`

Do not upload the entire repo. Only upload the static site files unless you want to publish additional assets later.

## Step 3. Test the subdomain

After upload, open:

- `https://software.nogginhausenergy.org`

If the page does not open immediately:

- wait a few minutes for the subdomain to propagate inside the host
- confirm `index.html` is inside the actual subdomain document root
- confirm the `styles.css` file is in the same folder as `index.html`

## Step 4. Optional improvements

You can extend the page later with:

- product screenshots
- a demo request form
- pricing or pilot-offer section
- a contact WhatsApp button
- testimonials or client logos

## Important note about branching

The repo is currently on:

- `feature/phase1e-feature-a-geo-validation`

There are also uncommitted changes under `product/`.

Because of that, creating and switching to a new branch right now should be done carefully so we do not accidentally carry unrelated work into a marketing-site commit.
