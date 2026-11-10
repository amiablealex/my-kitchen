# Changelog

## 0.29.0 — @kitchen can start a new version
**From a question to a new version in one tap.** When @kitchen's answer
suggests a change big enough to need the recipe rewriting (making it
vegetarian, cooking it in the slow cooker, turning it into a traybake), a
*Make this version N* button appears under the reply. It opens the refine
panel with the change already written in. Nothing is sent until you've
confirmed it, as with any new version.

Small swaps don't get the button: lemon for lime, dried herbs for fresh,
thighs for breasts. Nor do questions about storing, reheating, timing or
technique. Make those as you cook. Answers given before this update never
show the button.

- @kitchen is more dependable: if the quick model sends back an empty answer,
  the main model now answers instead of showing *Try again*.
- Failed attempts in your recipe list can be cleared again with the small ×
  on their row (with *Undo*). They have no recipe page of their own, so this
  is the one row that keeps a button.

**For the self-hosted:** one small database migration (a new column on
notes), applied automatically when the add-on starts. There's a new
`flask eval-kitchen` command that checks @kitchen flags the right answers,
using about ten cheap calls per run.

## 0.28.3
- *Ready to cook?* fits on one phone screen: two request chips instead of
  four (they now sit on one row), and one fewer line of explanation above
  the request box.

## 0.28.2
- **"Ready to cook?" reworked.** Your saved recipes that fit come first, under
  *Already in your recipes*. Below them, one *Make something new* card holds
  the request box and the *Generate recipes* button together, so what you
  ask for and the button that sends it are in the same place. The coloured
  band and the fold-away request box are gone.
- *What are you making?* is now centred like the steps after it, with more
  space between meal type and cuisine.

## 0.28.1
- **The cook wizard keeps its buttons in one place.** Back and Continue now
  sit together at the bottom right of every step, just above the bottom bar,
  and stay there while you scroll a long ingredient list. On *How much time?*
  and *Who's eating?* the choices sit in the middle of the screen.
- **A clearer "Ready to cook?" page.** Your brief is one row of chips (tap
  *Full brief* for the detail). Saved recipes you can cook right now get
  their own coloured section, and the request box folds away under *Nothing
  take your fancy?* The button at the bottom always makes something new.
- **Quieter recipe lists.** The cook's initial is now a small tag at the start
  of each row's details, so titles get the full width.
- Fixed: the ⋯ menu's items now line up.

## 0.28.0 — Petals: a new look throughout
**A design language of its own.** Buttons, chips and cards now share one
shape: rounded, with a single sharp corner that flips when you tap it. The
outline buttons and the coloured stripes down the left of cards, notices and
menus are gone. Where something needs marking, a small coloured "bead" holds
its icon instead.

- **Each place has its colour.** Stock is lime, Recipes orange, Favourites
  pink and Cook the pinwheel, on the home tiles, in the menu and in the
  bottom bar.
- **Wizard choices are chips.** Picking one fills it in the step's colour
  with a tick. Back and Continue are now a small arrow and one wide button.
- **A tidier recipe page.** Favourite sits next to the servings. Print or
  share, Edit recipe and Archive have moved into the ⋯ menu at the top
  right. Edit tags and Edit links are quieter text buttons.
- **New versions start from the trail.** Tap *+ New version* at the end of
  the version trail to refine a recipe. Before anything is sent there's now
  a check: it shows your change, explains that the current version is kept,
  and points you to @kitchen if you only meant to ask a question. The same
  check applies to *Rewrite the method for this many*.
- **Shorter recipe rows.** One line for the title, one for the date, cuisine,
  time and servings. Who cooked it is a coloured initial, and a pair you
  haven't chosen between yet is one *Pick one* row. Archiving from the list
  has gone; archive from the recipe's ⋯ menu instead.
- **Slightly smaller headings and buttons**, so more fits on a phone screen.
  Body text and tap targets are unchanged.

## 0.27.2 — A new look: the pinwheel
- The four-colour pinwheel is now My Kitchen's logo. It appears in the browser
  tab, on the home-screen app icon (with a version cut for Android's adaptive
  icons), next to the name in the menu, on the login screen, on printed
  recipes, and as this add-on's icon and logo.
- A phone that already has My Kitchen on its home screen may keep the old icon
  until you remove and re-add it.

## 0.27.1
- Tidier @kitchen composer. There's now only one button for posting: it reads
  *Add note*, and turns into *Ask @kitchen* (with the pinwheel) as soon as
  your text starts with @kitchen. The *Ask @kitchen instead* shortcut hides
  once you're asking, and comes back if you remove the @kitchen.

## 0.27.0 — Ask @kitchen

**Ask questions about a recipe.** In a recipe's Notes, start what you type with
**@kitchen** (or tap *Ask @kitchen*) and post it. The kitchen replies just
underneath, in the thread: how long to rest it, what to use instead of crème
fraîche, whether it freezes. It knows the recipe, the number of servings
you're viewing it at, what's in stock, and everyone's allergies and dislikes,
so it won't suggest a swap someone can't eat. It only answers questions. To
change the recipe itself, use *Refine*.

Answers usually arrive in a few seconds. A slower one shows "Thinking…" and
appears when it's ready, and if one fails there's a *Try again* button.
Deleting a question removes its answer too. Questions don't appear in the
print / share view.

New add-on options: `limit_questions_per_user_day` (default 20; questions
also count towards the household limit) and `llm_qa_model` (blank uses the
quick, cheap `gemini-3.5-flash-lite`, and falls back to your main model if that
one isn't available). Questions appear on the Usage page as their own type.

## 0.26.0 — Try again, refine, and recipe versions

**Neither of the two? Try again.** The choice screen has a new *Neither — try
again* option. It fetches two more recipes from the same brief and steers them
clearly away from everything you've already passed on. Your special request is
pre-filled, so you can tweak it first. There are three fresh tries per brief
(a new add-on option), and *The previous two* takes you back a round. Rejected
rounds no longer pile up on the Recipes page: a run of tries shows as one entry.

**Refine a recipe.** AI recipes have a new *Not quite right? Refine it* panel:
say what you'd change ("make it spicier", "swap the cream for something
lighter") and you get a revised version. It opens by itself straight after you
pick a recipe. Allergies still always apply. If you've scaled the servings, the
panel can rewrite the whole method for the new number of people.

**Recipe versions.** A refined recipe shows a trail along the top: Original →
"make it spicier" → … Tap any step to see that version. The newest version
replaces the older ones on the Recipes page (marked v2, v3…) and in
suggestions. Earlier versions are kept, along with any favourites and notes
on them.

## 0.25.0 — Special requests and a usage page

**Tell the kitchen what you fancy.** The last step of Lets Cook has a new
optional box: *Anything in mind?* Type a dish, a mood or a style ("a proper
curry, nothing too fiery", "I'm tired, keep it simple") or tap one of the
suggestions, and both recipes are built around it. It never overrides an
allergy or an ingredient you chose to use up. If you name a food someone
dislikes, though, you get it. Recipes made this way show what you asked for.

**New Usage page** (in the menu). It shows how many AI calls the household has
made, the tokens used and an estimated cost: today, this week, this month,
per person, and the most recent calls.

**Daily limits.** By default each person can start 10 recipe generations a day
and the household 40 AI calls a day. Both are new add-on options. The limits
are there to stop anything running away, not to get in the way, and they reset
at midnight. If you start a generation while one of yours is already running
(another tab or device), you're taken back to the one in progress.

## 0.24.0 — Archive and servings

**Archive recipes you don't need to see.** Each row on the Recipes page now
has an archive button. The recipe disappears from Recipes, Favourites and the
cook wizard's suggestions, with an Undo straight afterwards. You can also
archive from a recipe's own page. Nothing is deleted: everything archived is
listed on the new Archive page (linked from Recipes), and Restore brings it
back. Archiving applies to the whole household.

**Scale a recipe to more or fewer people.** On a recipe page, use − and + next
to the ingredients to change the number of servings, and the amounts adjust.
Amounts like "a splash" are left as they are, and quantities in the method
stay at the original serving size. It's only for the current view: nothing is
saved, and the print / share view always uses the recipe's own serving count.

## 0.23.0 — Recipe data export
- The print / share view has a new "Download recipe data (JSON)" link, which saves the recipe (title, intro, ingredients, method, tips and tags) as a file for publishing elsewhere. Household notes and names are not included.

## 0.22.0

**Dietary tags now come in three kinds: Allergy, Dislike and Diet.**

Dislikes are new, and they fix a real problem. If you'd added something like
"Pesto" as a preference, the recipe generator was being told to lean *towards*
it — and the instruction couldn't reach anything that wasn't already in your
stock anyway. A Dislike is now kept out of the whole recipe: ingredients,
optional extras, even serving suggestions.

- **Allergy** — never used, in any form. Overrides everything.
- **Dislike** — a food someone doesn't like. Left out entirely, but an
  ingredient you deliberately choose in the wizard still wins.
- **Diet** — how someone eats generally (vegetarian, gluten-free, nothing too
  spicy). Steers the whole recipe.

**Please check your existing tags.** Everything you'd added as a "preference"
is now filed under **Diet**. Anything that's really a disliked food should be
switched to **Dislike** on Manage → Dietary tags.

Also in this release:
- Choosing a tag type now explains what each one does, with examples.
- You can assign a tag to people as you create it, instead of making a second
  trip to the Household page.
- The "Who's eating?" step shows each person's tags as colour-coded badges, so
  you can see an allergy at a glance.
- The review page lists allergies, dislikes and diets separately.

No database changes in this release.

## 0.21.0 - Smarter recipe filtering

- The recipes search box now filters by **cuisine, meal type, cook and source**
  as well as by name. Start typing and tap a suggestion to add it as a filter —
  stack several to narrow things down, tap one to remove it.
- Works on Favourites too. The old Cook dropdown is gone, folded into the search.

## 0.20.0 - Build a meal around your staples

- You can now pick **staples** when choosing what to use up — handy when you want
  a meal built around the oregano and tomatoes rather than just whatever's fresh.
  They sit in their own section, tucked away until you want them.
- Fixed: staples weren't always being passed to the recipe generator.
- Recipes with notes now show a small speech bubble in your recipes list.

## 0.19.0 - Notes on your recipes

- Leave **notes** on any recipe — how it went, what you changed, whether to make
  it again. Notes show who wrote them and when, oldest first, and everyone in the
  household sees them.
- Cooked it more than once? Add another note. Your own notes can be deleted.
- Notes don't appear on the print / share view, so a printed recipe stays clean.

## 0.18.2 - Little fixes to share page

- Added border around timer pills for better visibility
- Fixed double-line closing render
- Improved overlap behaviour on long pages (now constrained to sections)

## 0.18.1 - Print / share polish

- The share view is now presented as **Print / share this recipe**, with a
  printer icon — printing or saving to PDF is the reliable way to send a recipe
  to someone.
- Added a short hint on the page explaining how to print from a phone.

## 0.18.0 - Share a recipe

- New **Share this recipe** button on every recipe: opens a clean, chrome-free
  version of the recipe with no navigation bars, so a scrolling screenshot
  captures the whole thing uninterrupted.
- The same page prints (or saves to PDF) properly on a light background.

## 0.17.1 - Tidier cuisine choices
- Condensed the cuisine list into clearer groups, so more recipes get a fitting tag.
- Cuisine and meal type now shown as compact chips rather than a long stacked list.

## 0.17.0 - Richer cuisines & smarter recipe variety
- Expanded the cuisine choices: added French, Middle Eastern, Indian, Thai, Chinese and Mexican, and split the old catch-all "Asian" into its distinct cuisines.
- Creative variety is now tailored to the meal type. Desserts and baking draw on sweet-leaning ideas rather than savoury ones, and sauces are left to their own devices.
- Regional flavour nudges no longer pull against a cuisine you've specifically chosen.
- When no cuisine is chosen, generations now vary between a creative nudge and a completely free hand for more variety across recipes.
- Sharpened how "Sauce or dressing" is interpreted, so you get the sauce itself rather than a dish built around one.

## 0.16.2 - Fixes

- Fixed recipe display for ingredients without specified unit

- Adjusted 'baking' meal type generations to actually result in the craft, not just the technique.

## 0.16.1 - made recipe editing orderable

- Ingredients, prep, cook, tips sections now reoderable within their sections

## 0.16.0 - Much more intuitive stock management

- Shared search bar to filter existing stock and add from catalogue.

- Clear distinction of staples showing up in search

- Management of staples separated in the manage route

## 0.15.1 - Polka hero

- Little styling update on home page and generating spinner

## 0.15.0 - Quite a nice little improvement to user experience

- Making a shift from 'functional' to 'intuitive'

## 0.14.1 - Fixed llm leaning too heavily on "To-buy"

- Prevented llm generated recipes bbeing based around a to_buy not-in-stock ingredient,
instead guided the llm to use as 'optional extras' i.e garnish, flavour enhancers and to never build a
meal around an item not in stock

- Rephrased "You may need to-buy" -> "Optional Extra" for clarity

## 0.14.0 — Recipe suggestions at "Lets cook"

- The review step now shows saved recipes you can cook **right now** that fit
  your brief, as tappable cards — before offering to generate a new one. A
  deterministic, no-AI query over your linked recipe bank (the keystone payoff).
- Recipes carry a quick/relaxed **time badge**: AI recipes inherit it from the
  cook; user recipes set it on the create/edit form.
- The cuisine step's "Surprise me" now reads **Any** (same behaviour).

## 0.13.0
- Filter the recipes list by source (AI generated / created by hand).
- Recipes are now colour-dotted by origin across the recipes list, favourites,
  and the recipe page — a playful AI pinwheel vs a solid dot for your own.

## 0.12.0
- Recipes now carry meal-type and cuisine tags, editable inline on the recipe
  page (cuisine shown only for cuisine-bearing meal types).
- AI recipes are tagged automatically from the wizard choices; created recipes
  can be tagged on the create/edit form. Both tags are optional.
- Edit your own created recipes from a button on the recipe page.

## 0.11.0
- Recipe pages now show which catalogue ingredient each line is linked to, as a
  small tag beside it — and you can change those links. Tap "Edit links" on the
  Ingredients section to re-link a line to a different ingredient, unlink one,
  or add a brand-new ingredient to your catalogue and link it in one step.
- Works on every recipe, including ones generated before now.
- Your corrections are shared across the household and stick — nothing is
  re-linked automatically behind your back.
- No schema change, and the generation prompt is unchanged.

## 0.10.0
- Groundwork for "what can I cook now?" suggestions: every new recipe's
  ingredients are now linked to the shared ingredient catalogue behind the
  scenes. No visible change — recipe pages and the generation prompt are exactly
  as before.
- Applied as a fresh rebuild onto the new, larger ingredient catalogue: saved
  recipes, favourites and history are cleared, and a new login password is
  generated (shown in the add-on log; set your own with `flask set-password`).
  Back up /data first if you want a copy of the old data.
- Additive schema: a new `recipe_ingredients` table plus provenance fields on
  recipes (source / meal type / author). The generation prompt is unchanged.

## 0.9.0
- Recipe generation now runs in the background. Generating no longer holds the
  page open for the whole wait: the "Lets Cook" flow starts the job and shows a
  "cooking up your recipes…" page that updates itself and jumps to your two
  recipes the moment they're ready.
- Fixes generations timing out when cooking remotely (over the Nabu Casa cloud
  link) — the long wait no longer runs through the proxy in one request.
- A double-tap on "Generate recipes" now resumes the same wait instead of
  starting a second generation.
- If a generation gets stuck or takes too long, the page shows a clear message
  and a way to try again, rather than hanging.
- Additive migration: new nullable `generations.status` column; existing
  recipes and history are unaffected. The generation prompt is unchanged.

## 0.8.0
- Add a "meal type" selector to the Lets Cook wizard (Breakfast, Lunch, Dinner,
  Snack, Side dish, Dessert, Baking, Sauce or dressing). It sits on the cuisine
  step; the non-cuisine types (Dessert/Baking/Sauce or dressing) hide and omit cuisine.
- Meal type is a soft steer in the generation brief (Dinner stays the default and
  changes nothing) and is recorded on each generation.
- Additive migration: new nullable `generations.meal_type` column; existing rows unaffected.

## 0.7.4
- dummy version bump to test if data persists

## 0.7.3
- sidebar no longer requires user to be admin

## 0.7.2 
- Csrf fix

## 0.7.1
- Ingress and path handling

## 0.7.0
- Initial Home Assistant add-on packaging (pass 7b).
- Reuses the standalone container recipe; app fetched from `main` at build.
- Add-on options → env (LLM provider/model/key, temperature, max-tokens,
  recent-titles N, timezone, gunicorn sizing).
- SECRET_KEY generated once and persisted to /data (stable across restarts).
- First-run auto-seed: starter catalogue + one user with a generated password
  printed to the add-on log.
- SQLite DB persists in HA's /data (captured by HA backups).
