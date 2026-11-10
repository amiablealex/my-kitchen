"""@kitchen questions (Phase 27): answer a cook's question about one recipe.

Only answers, never a rewrite. Refine is the rewrite path, and this keeps the
two apart. The answer is plain text in the notes feed, written onto the
question's own RecipeComment row. Kept apart from prompt.py on purpose: the
sealed generation prompt is untouched.

Context sent: the recipe (in the output-contract shape), the servings the
cook is viewing it at, the last few answered questions on this recipe (for
follow-ups), what's in stock and the staples (so a substitution can come
from the cupboard), and every active household member's allergies and
dislikes. An answer suggests swaps, so it has to know what's off limits for
whoever eats next time, not only who the recipe was first made for.
"""
import json
import re

from ..extensions import db
from ..models import Ingredient, Recipe, RecipeComment, User, utcnow
from .providers import DEFAULT_QA_MODELS, ProviderError, get_provider

QA_MAX_TOKENS = 1024        # thinking counts against this; answers are asked to be short
QA_TEMPERATURE = 0.4
ANSWER_MAX_CHARS = 4000     # storage guard; a real answer is a fraction of this
HISTORY_TURNS = 3           # earlier answered questions sent for follow-ups

QA_SYSTEM_PROMPT = """You are the kitchen assistant in a household's recipe app. A cook \
has asked a question about ONE recipe, posted in the recipe's comment thread, and you \
are replying in that thread.

How to answer:
- Answer the question directly, like a friend who really knows their way around a kitchen: warm, confident, practical. Don't restate the question and don't sign off.
- Keep it short: usually two to five sentences. Use a few short lines only when a step-by-step genuinely needs them.
- Plain text only. No markdown, no headings, no bold, no bullet symbols.
- UK English and UK conventions: metric units (g, ml), Celsius oven temperatures with fan where it matters, British ingredient names.
- When it helps, give a sensory cue (colour, smell, texture, sound) rather than just a time.
- Substitutions: prefer things the household has in stock or in the staples. NEVER suggest anything on the allergy list, or anything containing it. Avoid the dislikes.
- The cook may be viewing the recipe scaled to a different number of servings than it was written for; answer for the servings they're viewing.
- You only answer questions about cooking this recipe (technique, timing, swaps, storage, reheating, scaling, serving). If the question is about anything else, say kindly in one sentence that you can only help with this recipe.
- If you're not sure (e.g. an exact food-safety time), say so plainly and give the safe, conservative answer.
- Never rewrite the whole recipe in your answer.

Flagging a bigger change:
- The app can turn your suggestion into a new, rewritten version of the recipe. Only flag it when your answer proposes a MAJOR change: one that alters the dish enough that the ingredients list and method would really need rewriting. Examples: making it vegetarian or vegan, a different cooking method or appliance (slow cooker, air fryer, oven instead of hob), turning it into a different kind of dish (a pasta bake, a soup, a traybake), swapping the main ingredient for one that cooks quite differently, or adding a whole new component.
- Do NOT flag like-for-like swaps or small tweaks the cook can simply make as they go: lemon for lime, dried herbs for fresh, chicken thighs for breasts, one cheese or oil for another, a bit more or less of something, a garnish. Never flag questions about storage, freezing, reheating, timings, doneness, technique or serving.
- To flag, end your answer with one final line on its own, exactly: CHANGE: <a short instruction for the rewrite, under 15 words, e.g. "Make it vegetarian, using chickpeas instead of the chicken">
- If it isn't a major change, don't write a CHANGE line at all. When in doubt, don't flag."""


def _contract(recipe):
    # Local import: service imports from this package's siblings.
    from .service import recipe_to_contract
    return recipe_to_contract(recipe)


def _household_dietary():
    allergies, avoid = set(), set()
    for u in User.query.filter_by(is_active=True).all():
        for tag in u.dietary_tags:
            if tag.type == "allergy":
                allergies.add(tag.name)
            elif tag.type == "avoid":
                avoid.add(tag.name)
    return sorted(allergies), sorted(avoid)


def build_qa_prompt(recipe, question, viewing_servings=None, history=()):
    lines = ["RECIPE (JSON):", json.dumps(_contract(recipe), ensure_ascii=False), ""]
    base = recipe.servings
    if viewing_servings and base and viewing_servings != base:
        lines.append(f"The recipe is written for {base}, but the cook is viewing it "
                     f"scaled to {viewing_servings} servings.")
    elif base:
        lines.append(f"The recipe serves {base}.")

    allergies, avoid = _household_dietary()
    if allergies:
        lines.append("ALLERGIES in the household — never suggest these or anything "
                     "containing them: " + ", ".join(allergies) + ".")
    if avoid:
        lines.append("Dislikes in the household — avoid suggesting: " + ", ".join(avoid) + ".")

    in_stock = [i.name for i in Ingredient.query.filter_by(
        in_stock=True, is_staple=False, is_active=True).order_by(Ingredient.name)]
    staples = [i.name for i in Ingredient.query.filter_by(
        is_staple=True, is_active=True).order_by(Ingredient.name)]
    if in_stock:
        lines.append("In stock: " + ", ".join(in_stock) + ".")
    if staples:
        lines.append("Staples (always on hand): " + ", ".join(staples) + ".")

    if history:
        lines.append("")
        lines.append("Earlier questions on this recipe (oldest first):")
        for q, a in history:
            lines.append(f"Q: {q}")
            lines.append(f"A: {a}")

    lines.append("")
    lines.append("THE COOK'S QUESTION, between the markers:")
    lines.append("<<<")
    lines.append(question.replace("<<<", "").replace(">>>", ""))
    lines.append(">>>")
    return "\n".join(lines)


CHANGE_MAX_CHARS = 200     # the refine box's own limit is larger; this is a one-liner
# One line only ([ \t], never \s, so an empty marker can't swallow the next
# line); tolerates markdown bold around the label.
_CHANGE_LINE = re.compile(r"^[ \t]*\**[ \t]*CHANGE[ \t]*\**[ \t]*:[ \t]*\**[ \t]*(.*?)[ \t]*\**[ \t]*$", re.I | re.M)


def _clean_answer(text):
    """Plain text for a pre-wrap block: drop markdown emphasis and headings the
    model sometimes adds anyway, trim, cap."""
    s = (text or "").replace("**", "").replace("__", "")
    s = re.sub(r"^\s{0,3}#{1,6}\s*", "", s, flags=re.M)
    return s.strip()[:ANSWER_MAX_CHARS]


def split_change(text):
    """(answer, change). Pulls a `CHANGE: ...` line out of the model's text,
    wherever it landed, so it never shows in the reply. The LAST such line wins;
    an empty or garbled one just means no button. Pure, so the eval and the
    background job share it."""
    raw = text or ""
    matches = list(_CHANGE_LINE.finditer(raw))
    if not matches:
        return raw, None
    change = matches[-1].group(1).strip().strip('*"\u201c\u201d\' ').strip()
    answer = _CHANGE_LINE.sub("", raw)
    change = change[:CHANGE_MAX_CHARS]
    if not change:
        return answer, None
    return answer, change[0].upper() + change[1:]


def qa_models(cfg):
    """The models to try, in order: the QA model, then the main model once if
    they differ. Shared by the background job and `flask eval-kitchen`."""
    provider_name = (cfg.get("LLM_PROVIDER") or "mock").lower()
    main_model = cfg.get("LLM_MODEL") or None
    qa_model = cfg.get("LLM_QA_MODEL") or DEFAULT_QA_MODELS.get(provider_name) or main_model
    return [qa_model] if qa_model == main_model else [qa_model, main_model]


def answer_question(app, comment_id, viewing_servings=None):
    """Background job: answer one question and write it onto its row. Runs in
    its own app context and session, like generation, and always leaves the row
    'done' or 'error', never 'pending'."""
    with app.app_context():
        try:
            c = db.session.get(RecipeComment, comment_id)
            if c is None:
                return
            recipe = db.session.get(Recipe, c.recipe_id)
            earlier = [(q.body, q.answer) for q in recipe.comments
                       if q.is_question and q.answer_status == "done"
                       and q.id != c.id and q.created_at <= c.created_at][-HISTORY_TURNS:]
            prompt = build_qa_prompt(recipe, c.body, viewing_servings, earlier)

            cfg = app.config
            attempts = qa_models(cfg)

            text, last_error = None, None
            for model in attempts:
                try:
                    provider = get_provider(cfg, model=model, max_tokens=QA_MAX_TOKENS,
                                            temperature=QA_TEMPERATURE)
                    try:
                        text = provider.generate(QA_SYSTEM_PROMPT, prompt,
                                                 json_mode=False, thinking="low")
                    finally:
                        usage = getattr(provider, "last_usage", None) or {}
                        if usage:
                            c.input_tokens = (c.input_tokens or 0) + int(usage.get("input") or 0)
                            c.output_tokens = (c.output_tokens or 0) + int(usage.get("output") or 0)
                    c.model = f"{provider.name}:{provider.model}"
                    break
                except ProviderError as e:
                    # A refused Lite model (renamed, not enabled on the key) falls
                    # back to the main model once, so questions keep working.
                    last_error = e
                    continue

            body, change = split_change(text)
            answer = _clean_answer(body)
            if answer:
                c.answer = answer
                c.suggested_change = change
                c.answer_status = "done"
            else:
                c.answer_status = "error"
                app.logger.warning("@kitchen answer failed for comment %s: %s",
                                   comment_id, last_error or "empty answer")
            c.answered_at = utcnow()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.exception("@kitchen answer crashed for comment %s: %s", comment_id, e)
            try:
                c = db.session.get(RecipeComment, comment_id)
                if c is not None:
                    c.answer_status = "error"
                    db.session.commit()
            except Exception:
                db.session.rollback()
        finally:
            db.session.remove()
