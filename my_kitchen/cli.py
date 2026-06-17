import click

from .extensions import db
from . import models


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables (safe to re-run)."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Drop ALL tables, recreate, then seed.")
    def seed(reset):
        """Seed placeholder categories, one user, and a starter ingredient list."""
        if reset:
            db.drop_all()
            db.create_all()
            click.echo("Dropped and recreated all tables.")
        else:
            db.create_all()

        if models.User.query.first():
            click.echo("Data already present — nothing to do. Use --reset to wipe and reseed.")
            return

        # One placeholder user (id 1). Auth/password arrives in Phase 1.
        db.session.add(models.User(name="Home Cook", is_active=True))

        # Category names are freely editable; the four sections are fixed.
        category_rows = [
            ("Protein", "protein", 1),
            ("Carbohydrate", "carb", 2),
            ("Vegetable", "veg", 3),
            ("Dairy", "other", 4),
            ("Spice", "other", 5),
            ("Oil", "other", 6),
            ("Pantry", "other", 7),
        ]
        cats = {}
        for name, section, order in category_rows:
            c = models.Category(name=name, section=section, display_order=order)
            db.session.add(c)
            cats[name] = c
        db.session.flush()  # assign category ids before linking ingredients

        # Placeholder ingredients: (name, category, is_staple, in_stock).
        # Staples (Spice/Oil/Pantry) are assumed available; core items must be chosen.
        # A spread of in-stock items so every wizard lane has something to add.
        ingredient_rows = [
            ("Chicken breast", "Protein", False, True),
            ("Salmon fillet", "Protein", False, False),
            ("Eggs", "Protein", False, True),
            ("Tofu", "Protein", False, False),
            ("Rice", "Carbohydrate", False, True),
            ("Pasta", "Carbohydrate", False, True),
            ("Potatoes", "Carbohydrate", False, True),
            ("Onion", "Vegetable", False, True),
            ("Carrot", "Vegetable", False, True),
            ("Broccoli", "Vegetable", False, False),
            ("Spinach", "Vegetable", False, False),
            ("Tomato", "Vegetable", False, True),
            ("Milk", "Dairy", False, True),
            ("Cheddar cheese", "Dairy", False, True),
            ("Butter", "Dairy", False, True),
            ("Salt", "Spice", True, True),
            ("Black pepper", "Spice", True, True),
            ("Cumin", "Spice", True, True),
            ("Paprika", "Spice", True, True),
            ("Olive oil", "Oil", True, True),
            ("Vegetable oil", "Oil", True, True),
            ("Plain flour", "Pantry", True, True),
            ("Stock cubes", "Pantry", True, True),
        ]
        for name, cat_name, staple, in_stock in ingredient_rows:
            db.session.add(models.Ingredient(
                name=name, category=cats[cat_name],
                is_staple=staple, in_stock=in_stock,
            ))

        db.session.commit()
        click.echo(
            f"Seeded {models.User.query.count()} user, "
            f"{models.Category.query.count()} categories, "
            f"{models.Ingredient.query.count()} ingredients "
            "(dietary_tags + equipment intentionally left empty for later phases)."
        )

    @app.shell_context_processor
    def shell_context():
        return {
            "db": db,
            "User": models.User,
            "DietaryTag": models.DietaryTag,
            "Category": models.Category,
            "Ingredient": models.Ingredient,
            "Equipment": models.Equipment,
            "Generation": models.Generation,
            "Recipe": models.Recipe,
        }
