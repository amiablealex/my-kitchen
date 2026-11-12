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

## Model for @kitchen answers
`llm_qa_model` picks the model that answers @kitchen questions on a recipe.
Leave it blank to use `gemini-3.5-flash-lite` (quick and cheap for short
answers). If that model is refused, the app falls back to `llm_model`.

## Usage limits & cost
`limit_generations_per_user_day` (default 10) and `limit_household_calls_day`
(default 40) cap AI calls per local calendar day, and
`limit_regenerates_per_brief` (default 3) caps "Neither — try again" rounds,
and `limit_questions_per_user_day` (default 20) caps @kitchen questions — generous for normal use,
there to stop a runaway. The app's **Usage** page shows calls, tokens and an
estimated cost. For a hard stop on the provider side as well, set a budget
alert and a daily request quota on your API key.

## Receipt scanning & privacy
On the Stock page, the receipt icon in the search box reads a photo of a
shopping receipt and offers to mark what you bought as in stock. Before
anything is sent you drag two bars to frame just the item lines; the photo is
cropped and shrunk on your phone, and only that part is uploaded. My Kitchen
passes it to your AI provider for one read and doesn't store it anywhere.
Nothing is stocked until you confirm, and anything it couldn't place is listed
for you to sort out.

A receipt can carry the shop, date and time, card and loyalty details, which
is why framing comes first. If you'd rather not send receipt photos at all,
set `receipt_scanning: false` and the icon disappears. Pasting a list or a
receipt's text into the stock search works either way: it's matched on your
own server, and only the product names it can't place are sent to the AI, as
text.

Check how your provider treats what you send. **Free tiers may use submitted
content, including images, to improve the provider's products, and may allow
human review**; paid, billing-enabled API projects generally don't. For
Gemini, Google applies its paid-tier data terms to free quota too in the UK,
EEA and Switzerland. Elsewhere, use a billing-enabled project, or turn
receipt scanning off.

`limit_receipt_reads_per_user_day` (default 10) caps receipt reads and list
matches per person; they also count towards `limit_household_calls_day`.

## Data & backups
- The SQLite database lives in the add-on's `/data` and is included in Home
  Assistant backups automatically.

## Updating
- Push app changes to `main`, bump `version` in `config.yaml`. HA offers the
  update; the entrypoint applies any new DB migrations automatically on start.
