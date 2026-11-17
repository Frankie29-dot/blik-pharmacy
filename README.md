# Blik Pharmacy

## Deploy the website to Vercel

Import this repository into Vercel with the **Root Directory** left blank so it
contains `public/` and `vercel.json`. The Vercel config selects the **Other**
framework preset and serves `public/` as the static site output. No build command is
needed.

The FastAPI backend is in `blik-backend/` and is deployed separately. Do not set
Vercel's project Root Directory to `blik-backend/` for the website deployment.
