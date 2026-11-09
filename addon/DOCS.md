# My Kitchen — Home Assistant add-on

Self-hosted, LLM-powered household recipe generator.

## Requirements
- Home Assistant OS or Supervised (add-ons aren't available on Container/Core).
- A Gemini API key (or Anthropic), unless you run the `mock` provider.

## Install
1. Settings → Add-ons → Add-on Store → ⋮ (top right) → Repositories.
2. Add `https://github.com/amiablealex/my-kitchen` and close.
3. Find **My Kitchen** in the store and click **Install** (first build takes a
   few minutes on a Pi — it fetches and builds the image locally).

## Configure & start
1. On the **Configuration** tab set `llm_provider` and the matching API key
   (or pick `mock` to try it without a key). Save.
2. **Start** the add-on, then open the **Log** tab. On first run you'll see a
   one-time block with a login user and temporary password.
3. Open **My Kitchen** from the Home Assistant sidebar (ingress, over HTTPS) and
   log in. Change the password in the app. (A direct-LAN port is also exposed,
   but the installable PWA only comes fully alive over the HTTPS ingress URL.)

## Usage limits & cost
`limit_generations_per_user_day` (default 10) and `limit_household_calls_day`
(default 40) cap AI calls per local calendar day, and
`limit_regenerates_per_brief` (default 3) caps "Neither — try again" rounds — generous for normal use,
there to stop a runaway. The app's **Usage** page shows calls, tokens and an
estimated cost. For a hard stop on the provider side as well, set a budget
alert and a daily request quota on your API key.

## Data & backups
- The SQLite database lives in the add-on's `/data` and is included in Home
  Assistant backups automatically.

## Updating
- Push app changes to `main`, bump `version` in `config.yaml`. HA offers the
  update; the entrypoint applies any new DB migrations automatically on start.
