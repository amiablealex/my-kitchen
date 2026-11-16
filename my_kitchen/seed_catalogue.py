"""Pure catalogue data — the single source of truth for BOTH the production
seed (``seed_data.seed_reference_data``) AND the resolver eval fixture
(``eval/golden_ingredients``).

Zero imports on purpose: this module is importable with no Flask app or DB
context, so the resolver eval runs DB-free, exactly like ``render_prompts.py``
imports only ``prompt`` + ``golden_briefs``. The seed builds ORM rows from this
data; the eval fixture reads the canonical names straight out of it. Neither can
drift from the other because there is only one list.

Phase 3a broadens the starter catalogue to realistic UK-household coverage. This
is DATA, not schema — more rows in the existing ``ingredients`` table — so 3a
stays migration-free.

Granularity principle (see ``3a-resolver-inputs.md``): canonical names sit at the
granularity the household distinguishes; aliases (``resolver/aliases.py``)
collapse anything finer; *qualifiers* (fresh / baby / large / chopped / tinned …)
are stripped by the resolver's normalisation, never encoded here.

``(S)`` items (``is_staple=True``) are assumed always available and not addable
in the wizard. The seed gives them ``in_stock=True``; core (non-staple) items
seed ``in_stock=False`` — the initial in-stock set is exactly the staples, and
the household toggles real stock for everything else via the stock UI.
"""

# (name, section, display_order). The four wizard lanes (sections) are fixed
# (spec §3); category *names* are configurable and unique across sections (the
# receipt scanner maps a category back by name), hence "Other carb" / "Other
# protein". display_order is a position within the section (0.30.0). 0.37.0
# split Protein, Carbohydrate and Pantry and paired the vinegars with oils.
# Fresh installs only — the seed never runs against an existing catalogue.
CATEGORIES = [
    ("Meat", "protein", 1),
    ("Fish", "protein", 2),
    ("Beans & pulses", "protein", 3),
    ("Other protein", "protein", 4),
    ("Pasta", "carb", 1),
    ("Bread", "carb", 2),
    ("Grain", "carb", 3),
    ("Other carb", "carb", 4),
    ("Vegetable", "veg", 1),
    ("Herb", "veg", 2),          # fresh herbs (veg lane); dried ones are Spice
    ("Fruit", "other", 1),
    ("Dairy", "other", 2),
    ("Spice", "other", 3),
    ("Oil & vinegar", "other", 4),
    ("Condiment", "other", 5),
    ("Pantry", "other", 6),
    ("Baking", "other", 7),
]

# (name, category, is_staple). in_stock is derived by the seed (= is_staple).
INGREDIENTS = [
    # --- Protein (section: protein): Meat, Fish, Other protein, Beans & pulses ---
    ("Chicken breast", "Meat", False),
    ("Chicken thigh", "Meat", False),
    ("Chicken mince", "Meat", False),
    ("Beef mince", "Meat", False),
    ("Beef steak", "Meat", False),
    ("Sausages", "Meat", False),
    ("Bacon", "Meat", False),
    ("Pork chop", "Meat", False),
    ("Lamb mince", "Meat", False),
    ("Salmon fillet", "Fish", False),
    ("White fish fillet", "Fish", False),
    ("Seabass fillet", "Fish", False),
    ("Cod fillet", "Fish", False),
    ("Tuna (tinned)", "Fish", False),
    ("Prawns", "Fish", False),
    ("Eggs", "Other protein", False),
    ("Tofu", "Other protein", False),
    ("Chickpeas", "Beans & pulses", False),
    ("Red lentils", "Beans & pulses", False),
    ("Green lentils", "Beans & pulses", False),
    ("Kidney beans", "Beans & pulses", False),
    ("Black beans", "Beans & pulses", False),
    ("Cannellini beans", "Beans & pulses", False),
    ("Butter beans", "Beans & pulses", False),

    # --- Carb (section: carb): Grain, Pasta, Other carb, Bread ---
    ("Rice", "Grain", False),
    ("Pasta", "Pasta", False),
    ("Egg noodles", "Other carb", False),
    ("Rice noodles", "Other carb", False),
    ("Potatoes", "Other carb", False),
    ("New potatoes", "Other carb", False),
    ("Sweet potato", "Other carb", False),
    ("Couscous", "Grain", False),
    ("Quinoa", "Grain", False),
    ("Bulgur wheat", "Grain", False),
    ("Bread", "Bread", False),
    ("Tortilla wraps", "Bread", False),
    ("Gnocchi", "Pasta", False),
    ("Oats", "Grain", False),

    # --- Vegetable (section: veg) ---
    ("Onion", "Vegetable", False),
    ("Red onion", "Vegetable", False),
    ("Spring onion", "Vegetable", False),
    ("Shallot", "Vegetable", False),
    ("Garlic", "Vegetable", False),
    ("Ginger", "Vegetable", False),
    ("Carrot", "Vegetable", False),
    ("Celery", "Vegetable", False),
    ("Broccoli", "Vegetable", False),
    ("Cauliflower", "Vegetable", False),
    ("Spinach", "Vegetable", False),
    ("Kale", "Vegetable", False),
    ("Cabbage", "Vegetable", False),
    ("Lettuce", "Vegetable", False),
    ("Cucumber", "Vegetable", False),
    ("Tomato", "Vegetable", False),
    ("Cherry tomatoes", "Vegetable", False),
    ("Bell pepper", "Vegetable", False),
    ("Red chilli", "Vegetable", False),
    ("Mushrooms", "Vegetable", False),
    ("Courgette", "Vegetable", False),
    ("Aubergine", "Vegetable", False),
    ("Sweetcorn", "Vegetable", False),
    ("Peas", "Vegetable", False),
    ("Green beans", "Vegetable", False),
    ("Asparagus", "Vegetable", False),
    ("Leek", "Vegetable", False),
    ("Butternut squash", "Vegetable", False),
    ("Beetroot", "Vegetable", False),
    ("Pak choi", "Vegetable", False),
    ("Mangetout", "Vegetable", False),
    ("Sugar snap peas", "Vegetable", False),
    ("Parsnip", "Vegetable", False),
    ("Rocket", "Vegetable", False),
    ("Avocado", "Vegetable", False),

    # --- Fresh herbs (category: Herb; section: veg) — distinct from dried (Spice) ---
    ("Coriander", "Herb", False),
    ("Parsley", "Herb", False),
    ("Basil", "Herb", False),
    ("Mint", "Herb", False),
    ("Dill", "Herb", False),
    ("Chives", "Herb", False),
    ("Fresh thyme", "Herb", False),
    ("Fresh rosemary", "Herb", False),

    # --- Fruit (category: Fruit; section: other) ---
    ("Lemon", "Fruit", False),
    ("Lime", "Fruit", False),
    ("Orange", "Fruit", False),
    ("Apple", "Fruit", False),
    ("Banana", "Fruit", False),
    ("Mango", "Fruit", False),
    ("Pineapple", "Fruit", False),

    # --- Dairy (section: other) ---
    ("Milk", "Dairy", False),
    ("Butter", "Dairy", False),
    ("Cheddar cheese", "Dairy", False),
    ("Parmesan", "Dairy", False),
    ("Mozzarella", "Dairy", False),
    ("Feta", "Dairy", False),
    ("Halloumi", "Dairy", False),
    ("Double cream", "Dairy", False),
    ("Single cream", "Dairy", False),
    ("Crème fraîche", "Dairy", False),
    ("Soured cream", "Dairy", False),
    ("Greek yoghurt", "Dairy", False),
    ("Natural yoghurt", "Dairy", False),
    ("Cream cheese", "Dairy", False),

    # --- Spice (section: other) — all staples ---
    ("Salt", "Spice", True),
    ("Black pepper", "Spice", True),
    ("Ground cumin", "Spice", True),
    ("Ground coriander", "Spice", True),
    ("Paprika", "Spice", True),
    ("Smoked paprika", "Spice", True),
    ("Turmeric", "Spice", True),
    ("Chilli powder", "Spice", True),
    ("Chilli flakes", "Spice", True),
    ("Cinnamon", "Spice", True),
    ("Nutmeg", "Spice", True),
    ("Ground ginger", "Spice", True),
    ("Garlic powder", "Spice", True),
    ("Garam masala", "Spice", True),
    ("Curry powder", "Spice", True),
    ("Ras el hanout", "Spice", True),
    ("Dried mixed herbs", "Spice", True),
    ("Dried oregano", "Spice", True),
    ("Dried thyme", "Spice", True),
    ("Bay leaves", "Spice", True),
    ("Cumin seeds", "Spice", True),
    ("Fennel seeds", "Spice", True),
    ("Mustard seeds", "Spice", True),
    ("Vanilla extract", "Baking", True),

    # --- Oil & vinegar (section: other) — all staples; vinegars sit with Condiment below ---
    ("Olive oil", "Oil & vinegar", True),
    ("Vegetable oil", "Oil & vinegar", True),
    ("Sunflower oil", "Oil & vinegar", True),
    ("Sesame oil", "Oil & vinegar", True),
    ("Coconut oil", "Oil & vinegar", True),

    # --- Condiment (category: Condiment; section: other) ---
    ("Soy sauce", "Condiment", True),
    ("Fish sauce", "Condiment", False),
    ("Oyster sauce", "Condiment", False),
    ("Worcestershire sauce", "Condiment", False),
    ("Tomato ketchup", "Condiment", False),
    ("Mayonnaise", "Condiment", False),
    ("Dijon mustard", "Condiment", False),
    ("Wholegrain mustard", "Condiment", False),
    ("Balsamic vinegar", "Oil & vinegar", True),
    ("Red wine vinegar", "Oil & vinegar", True),
    ("White wine vinegar", "Oil & vinegar", True),
    ("Honey", "Condiment", True),
    ("Maple syrup", "Condiment", False),
    ("Tomato purée", "Condiment", True),
    ("Tahini", "Condiment", False),
    ("Harissa", "Condiment", False),
    ("Pesto", "Condiment", False),
    ("Thai red curry paste", "Condiment", False),
    ("Thai green curry paste", "Condiment", False),
    ("Hot sauce", "Condiment", False),

    # --- Baking and Pantry (section: other) ---
    ("Plain flour", "Baking", True),
    ("Self-raising flour", "Baking", True),
    ("Caster sugar", "Baking", True),
    ("Brown sugar", "Baking", True),
    ("Cornflour", "Baking", True),
    ("Baking powder", "Baking", True),
    ("Bicarbonate of soda", "Baking", True),
    ("Cocoa powder", "Baking", False),
    ("Dark chocolate", "Baking", False),
    ("Breadcrumbs", "Pantry", False),
    ("Stock cubes", "Pantry", True),
    # 0.36.2: imported recipes list water ("180 ml lukewarm water"); unlinked,
    # it kept them out of suggestions. A staple, so it never blocks anything.
    ("Water", "Pantry", True),
    ("Tinned tomatoes", "Pantry", False),
    ("Passata", "Pantry", False),
    ("Coconut milk", "Pantry", False),
    ("Peanut butter", "Pantry", False),
    ("Raisins", "Baking", False),
    ("Flaked almonds", "Pantry", False),
    ("Cashews", "Pantry", False),
    ("Sesame seeds", "Pantry", False),
    ("Black olives", "Pantry", False),
    ("Capers", "Pantry", False),
    ("Sun-dried tomatoes", "Pantry", False),
]

# Convenience: the canonical names, in catalogue order. The eval fixture and any
# DB-free consumer reads this instead of touching the DB.
CATALOGUE_NAMES = [name for name, _cat, _staple in INGREDIENTS]


# "A kind of" pairs set on a fresh install (0.40.0): (kind, general). Only
# where the starter catalogue already has both and a recipe asking for the
# general one would happily take the kind ("1 onion" with red onions in).
# Deliberately short: the shapes, varieties and types a household buys are
# its own to add. No new ingredient names, so the resolver's catalogue — and
# its eval — is unchanged.
KINDS = [
    ("Red onion", "Onion"),
    ("New potatoes", "Potatoes"),
    ("Cherry tomatoes", "Tomato"),
]
