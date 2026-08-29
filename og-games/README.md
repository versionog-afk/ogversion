# og-games

The OG VERSION arcade. Lives at **https://ogversion.com/og-games** (also `/games`).

`index.html` renders whatever is listed in `games.json` — it never hardcodes a game.
Adding a game is two steps: drop the folder, add the entry.

## Adding a game

1. Put the game in its own folder here, with an `index.html` at its root:

   ```
   og-games/
     my-game/
       index.html
       ...assets
   ```

2. Add one entry to `games.json`:

   ```json
   {
     "games": [
       {
         "slug": "my-game",
         "title": "My Game",
         "note": "One line about it.",
         "status": "live",
         "cover": "covers/my-game.webp"
       }
     ]
   }
   ```

Order in the file is the order on the page.

### Entry fields

| Field    | Required | Meaning |
|----------|----------|---------|
| `slug`   | yes      | Folder name. Also the fallback URL (`slug/`). |
| `title`  | yes      | Shown on the card. |
| `note`   | no       | One-line description under the title. |
| `status` | no       | `live` (default) makes the card a link; `soon` shows it greyed out and unclickable. |
| `cover`  | no       | Image path relative to this folder, e.g. `covers/my-game.webp`. Without one the card shows its slot number. |
| `url`    | no       | Override the link — use it for a game hosted elsewhere. |

Cover art: 4:3, `.webp`, ~1200px wide. Keep them in `covers/`.

## Moving a local folder in

From the machine that has the games:

```bash
cp -R ~/path/to/og-games/* /path/to/ogversion/og-games/
cd /path/to/ogversion
git add og-games && git commit -m "Add games to the arcade" && git push
```

Then add each game to `games.json`. Vercel deploys on push.

## Notes

- Everything here is static — no build step. A game only needs to run from a plain folder.
- Keep each game self-contained; don't reach into `../assets`.
- With no entries in `games.json`, the page shows an "empty cabinet" state instead of a broken grid.
