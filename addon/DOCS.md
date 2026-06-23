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
3. Open the app (host port for now; ingress is added in the next version) and
   log in. Change the password in the app.

## Data & backups
- The SQLite database lives in the add-on's `/data` and is included in Home
  Assistant backups automatically.

## Updating
- Push app changes to `main`, bump `version` in `config.yaml`. HA offers the
  update; the entrypoint applies any new DB migrations automatically on start.
