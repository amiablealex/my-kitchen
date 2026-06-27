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
# (spec §3); category *names* are configurable. Herb / Fruit / Condiment are new
# in 3a, slotted alongside the original seven.
CATEGORIES = [
    ("Protein", "protein", 1),
    ("Carbohydrate", "carb", 2),
    ("Vegetable", "veg", 3),
    ("Herb", "veg", 4),          # new in 3a — fresh herbs (veg lane)
    ("Fruit", "other", 5),       # new in 3a
    ("Dairy", "other", 6),
    ("Spice", "other", 7),
    ("Oil", "other", 8),
    ("Condiment", "other", 9),   # new in 3a
    ("Pantry", "other", 10),
]

# (name, category, is_staple). in_stock is derived by the seed (= is_staple).
INGREDIENTS = [
    # --- Protein (section: protein) ---
    ("Chicken breast", "Protein", False),
    ("Chicken thigh", "Protein", False),
    ("Chicken mince", "Protein", False),
    ("Beef mince", "Protein", False),
    ("Beef steak", "Protein", False),
    ("Sausages", "Protein", False),
    ("Bacon", "Protein", False),
    ("Pork chop", "Protein", False),
    ("Lamb mince", "Protein", False),
    ("Salmon fillet", "Protein", False),
    ("White fish fillet", "Protein", False),
    ("Seabass fillet", "Protein", False),
    ("Cod fillet", "Protein", False),
    ("Tuna (tinned)", "Protein", False),
    ("Prawns", "Protein", False),
    ("Eggs", "Protein", False),
    ("Tofu", "Protein", False),
    ("Chickpeas", "Protein", False),
    ("Red lentils", "Protein", False),
    ("Green lentils", "Protein", False),
    ("Kidney beans", "Protein", False),
    ("Black beans", "Protein", False),
    ("Cannellini beans", "Protein", False),
    ("Butter beans", "Protein", False),

    # --- Carbohydrate (section: carb) ---
    ("Rice", "Carbohydrate", False),
    ("Pasta", "Carbohydrate", False),
    ("Egg noodles", "Carbohydrate", False),
    ("Rice noodles", "Carbohydrate", False),
    ("Potatoes", "Carbohydrate", False),
    ("New potatoes", "Carbohydrate", False),
    ("Sweet potato", "Carbohydrate", False),
    ("Couscous", "Carbohydrate", False),
    ("Quinoa", "Carbohydrate", False),
    ("Bulgur wheat", "Carbohydrate", False),
    ("Bread", "Carbohydrate", False),
    ("Tortilla wraps", "Carbohydrate", False),
    ("Gnocchi", "Carbohydrate", False),
    ("Oats", "Carbohydrate", False),

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
    ("Vanilla extract", "Spice", True),

    # --- Oil (section: other) — all staples ---
    ("Olive oil", "Oil", True),
    ("Vegetable oil", "Oil", True),
    ("Sunflower oil", "Oil", True),
    ("Sesame oil", "Oil", True),
    ("Coconut oil", "Oil", True),

    # --- Condiment (category: Condiment; section: other) ---
    ("Soy sauce", "Condiment", True),
    ("Fish sauce", "Condiment", False),
    ("Oyster sauce", "Condiment", False),
    ("Worcestershire sauce", "Condiment", False),
    ("Tomato ketchup", "Condiment", False),
    ("Mayonnaise", "Condiment", False),
    ("Dijon mustard", "Condiment", False),
    ("Wholegrain mustard", "Condiment", False),
    ("Balsamic vinegar", "Condiment", True),
    ("Red wine vinegar", "Condiment", True),
    ("White wine vinegar", "Condiment", True),
    ("Honey", "Condiment", True),
    ("Maple syrup", "Condiment", False),
    ("Tomato purée", "Condiment", True),
    ("Tahini", "Condiment", False),
    ("Harissa", "Condiment", False),
    ("Pesto", "Condiment", False),
    ("Thai red curry paste", "Condiment", False),
    ("Thai green curry paste", "Condiment", False),
    ("Hot sauce", "Condiment", False),

    # --- Pantry & baking (category: Pantry; section: other) ---
    ("Plain flour", "Pantry", True),
    ("Self-raising flour", "Pantry", True),
    ("Caster sugar", "Pantry", True),
    ("Brown sugar", "Pantry", True),
    ("Cornflour", "Pantry", True),
    ("Baking powder", "Pantry", True),
    ("Bicarbonate of soda", "Pantry", True),
    ("Cocoa powder", "Pantry", False),
    ("Dark chocolate", "Pantry", False),
    ("Breadcrumbs", "Pantry", False),
    ("Stock cubes", "Pantry", True),
    ("Tinned tomatoes", "Pantry", False),
    ("Passata", "Pantry", False),
    ("Coconut milk", "Pantry", False),
    ("Peanut butter", "Pantry", False),
    ("Raisins", "Pantry", False),
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
