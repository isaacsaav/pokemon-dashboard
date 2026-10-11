# Pokémon Market Tracker

A tiny dashboard that tracks card and set prices. A GitHub Action refreshes the data every day, and GitHub Pages hosts the page so anyone with the link can open it.

## 1. Try it on your computer (VS Code)

1. Open this folder in VS Code (File > Open Folder).
2. Open the terminal (Terminal > New Terminal).
3. Preview with sample data: `python fetch_prices.py --demo`
4. Open `index.html` in your browser (or right-click it and use Live Server if you have that extension).
5. Load real prices: `python fetch_prices.py`

You need Python 3 installed. There is nothing else to install.

## 2. Choose what to track

Edit `watchlist.json`. Each card or set needs an `id` and a `label` (the name shown on the dashboard).

Find IDs at https://pokemontcg.io or by browsing https://dev.pokemontcg.io. Card IDs look like `base1-4` (set id, dash, card number). Set IDs look like `sv3pt5`.
If an ID is wrong, the script tells you which one when it runs.

## Eras

`eras.json` holds the 10 Pokémon TCG eras (Wizards of the Coast through Mega Evolution). The script looks up which era each card or set belongs to, and the dashboard has an Era dropdown to filter by it. You don't need to tag anything yourself. The dropdown only lists eras you are actually tracking.

## 3. Put it online and share it

1. Create a free account at github.com and make a new repository (public is simplest).
2. Upload this folder to it (VS Code: Source Control > Publish to GitHub).
3. In the repo go to Settings > Pages. Under Source, choose "Deploy from a branch", branch `main`, folder `/ (root)`. Save.
4. After a minute your link appears there, like `https://YOURNAME.github.io/pokemon-dashboard/`. Send it to your cousin.

## 4. Turn on the daily refresh

- Optional but recommended: get a free API key at https://dev.pokemontcg.io, then in the repo go to Settings > Secrets and variables > Actions > New repository secret. Name it `POKEMONTCG_API_KEY` and paste the key.
- Go to the Actions tab and run "Daily price update" once by hand to test it. After that it runs by itself every day at 11:00 UTC. Change the time in `.github/workflows/daily.yml`.

## How it fits together

| File | Job |
| --- | --- |
| `eras.json` | The list of eras (rarely changes) |
| `watchlist.json` | What you track (the only file you normally edit) |
| `fetch_prices.py` | Gets today's prices and adds them to the history |
| `data/history.csv` | Every daily price, kept forever |
| `data/data.js` | Same data, formatted for the page |
| `index.html` | The dashboard |
| `.github/workflows/daily.yml` | Runs the script every day |

## Notes

- Trend charts start with one dot and fill in over time, since the history is built one day at a time.
- Prices are TCGplayer market prices in USD. A set's value is the sum of all its cards' market prices.
