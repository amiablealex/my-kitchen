# My Kitchen — Home Assistant add-on

Self-hosted, LLM-powered household recipe generator.

## Requirements
- Home Assistant OS or Supervised (add-ons aren't available on Container/Core).
- A Gemini API key (or Anthropic), unless you run the `mock` provider or your
  own model (see *Your own model*).

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

## Your own model (untested)
**I've tried to let you use your own model, but I haven't been able to test
it. It will only be as good as your model.** Set `llm_provider:
openai_compatible` to use any server that speaks the OpenAI chat API: Ollama,
LM Studio, llama.cpp, vLLM, or a cloud service such as OpenRouter.

- `llm_base_url`: your server's address, e.g. `http://192.168.1.20:11434` for
  Ollama. `/v1` is added if the address has no path.
- `llm_model`: the model's name on your server (required, no default).
  `llm_qa_model` can name a smaller one for @kitchen answers.
- `llm_api_key`: only if your server or service needs one.
- `llm_images`: turn on only if the model reads images (a "vision" model).
  Off, receipt scanning and recipes from photos simply don't appear.
- `llm_job_timeout_minutes` (default 5): how long a generation may take before
  it's treated as stuck. Local models on modest hardware can need much
  longer; two full recipes are a few thousand words of output.

Things to know. Recipe quality was tuned on Gemini; smaller models write
plainer recipes and may break the JSON format, which shows as a failed
generation. **They also follow allergy and dislike rules less reliably**, and
the prompt is the only safeguard, so check recipes for anyone with an allergy.
A Raspberry Pi is too slow to run a useful model itself; a computer with a
recent graphics card or Apple Silicon on your network is a better host. The
Usage page shows these calls' tokens but no cost, since My Kitchen can't know
your model's price. If you use a model through a cloud service, the receipt
privacy note still applies: the app says "your AI model" rather than "a cloud
AI model", because it can't tell which you're using.

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

## Importing recipes
*Add a recipe* offers *Import from the web* (a link or pasted text) and *From
a photo*. For a link, My
Kitchen fetches the page itself and, where the site provides structured recipe
data (most do), sends only that to the AI model; otherwise it sends the page's
text. The model lays the recipe out in My Kitchen's sections without
rewriting it, using `llm_qa_model`. Photos (up to four pages of one recipe)
are shrunk on your phone, sent together in one call on your main model, which
reads handwriting better, and aren't kept. *From a photo* only appears when
your provider reads images. Imports count towards `limit_household_calls_day`.

## Data & backups
- The SQLite database lives in the add-on's `/data` and is included in Home
  Assistant backups automatically.

## Updating
- Push app changes to `main`, bump `version` in `config.yaml`. HA offers the
  update; the entrypoint applies any new DB migrations automatically on start.
