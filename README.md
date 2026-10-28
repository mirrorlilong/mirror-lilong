# Mirror Lilong

The Mirror Lilong news website: news from Lilong, Manipur and the Northeast.

- **Post and edit news:** open `/admin` on the live site and sign in with GitHub. Phone steps are in [HOW-TO-POST.md](HOW-TO-POST.md).
- **Stories** live in `content/stories/`, one JSON file each (written by the admin panel).
- **Photos** uploaded in the admin panel go to `static/img/uploads/`.
- **Design** (styles, logo, script) lives in `static/`. The page layout is in `build.py`.
- **Build:** `python3 build.py` writes the finished site to `_site/`. It uses plain Python 3 with no packages. Netlify runs it on every change (see `netlify.toml`), so a saved story is live in about a minute.

## Story fields

| Field | What it does |
|---|---|
| `title` | Headline |
| `date` | Date and time (`YYYY-MM-DDTHH:mm`, India time). Newest first everywhere. |
| `category` | Section: Manipur, Northeast, India, World, Sports, Entertainment |
| `also_in` | Optional second section |
| `summary` | Line under the headline |
| `image`, `full_image` | Photo (and an optional different image for the story page; a portrait image is shown as a news card) |
| `image_credit` | Credit under the photo (`[text](link)` makes a link) |
| `body` | Story text (Markdown: paragraphs, **bold**, *italic*, links, lists, quotes) |
| `facebook`, `sources` | "Read on Facebook" link and source links |
| `lead` | Big story at the top of the home page (newest one wins; else the newest story) |
| `breaking`, `top`, `trending` | Show in the ticker / Top Stories / Trending (topped up with the newest stories) |
| `desk` | Mirror Lilong's own story (red badge, "From the Mirror Lilong desk") |
| `video` | Play icon, and listed on the Videos page |
| `hidden` | Keeps the story off the site |

The admin panel is [Sveltia CMS](https://github.com/sveltia/sveltia-cms) (pinned version), configured in `static/admin/config.yml`. It signs in with GitHub through Netlify's OAuth provider.
