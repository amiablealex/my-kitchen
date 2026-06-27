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
        from .seed_data import seed_reference_data

        if reset:
            db.drop_all()
            db.create_all()
            click.echo("Dropped and recreated all tables.")
        else:
            db.create_all()

        if models.User.query.first():
            click.echo("Data already present — nothing to do. Use --reset to wipe and reseed.")
            return

        # One placeholder user (id 1). Set its password with `flask set-password`.
        db.session.add(models.User(name="Home Cook", is_active=True))
        db.session.commit()

        seed_reference_data()

        click.echo(
            f"Seeded {models.User.query.count()} user, "
            f"{models.Category.query.count()} categories, "
            f"{models.Ingredient.query.count()} ingredients. "
            'Set the user password with: flask set-password "Home Cook"'
        )

    @app.cli.command("first-run-seed")
    def first_run_seed():
        """Idempotent first-run bootstrap for the HA add-on. Seeds the starter
        catalogue and creates one user with a generated password (printed once
        to the add-on log) ONLY when there are no users yet."""
        from .seed_data import seed_reference_data, ensure_first_user

        if models.User.query.first():
            click.echo("first-run-seed: users already present — skipping.")
            return

        seed_reference_data()
        created = ensure_first_user(name="Home Cook")
        if created:
            name, password = created
            click.echo("=" * 56)
            click.echo("  My Kitchen — first-run setup")
            click.echo(f"  Login user:     {name}")
            click.echo(f"  Temp password:  {password}")
            click.echo("  Change it in the app once you're in.")
            click.echo("=" * 56)

    @app.cli.command("set-password")
    @click.argument("name")
    @click.option("--password", default=None,
                  help="Set non-interactively (e.g. for scripts). Omit to be "
                       "prompted with hidden input + confirmation.")
    def set_password(name, password):
        """Set or reset a user's login password (by name, case-insensitive).

        This is the first-login bootstrap and the reset mechanism. There is no
        public/self-registration; passwords are only ever set here or in the
        in-app My Kitchen area.
        """
        user = models.User.query.filter(
            db.func.lower(models.User.name) == name.strip().lower()
        ).first()
        if user is None:
            known = ", ".join(
                u.name for u in models.User.query.order_by(models.User.name).all()
            )
            click.echo(f'No user named "{name}". Known users: {known or "(none)"}.')
            raise SystemExit(1)
        if password is None:
            password = click.prompt(
                f'New password for "{user.name}"',
                hide_input=True, confirmation_prompt=True,
            )
        if not password:
            click.echo("Password cannot be empty.")
            raise SystemExit(1)
        user.set_password(password)
        db.session.commit()
        click.echo(f'Password set for "{user.name}". They can log in now.')

    @app.cli.command("create-user")
    @click.argument("name")
    @click.option("--password", default=None,
                  help="Optionally set the password at creation. Omit to create "
                       "now and set it later with set-password.")
    def create_user(name, password):
        """Create a household user (idempotent — safe to re-run).

        If a user with that name already exists (active or retired), it's left
        completely untouched. New users are created active.
        """
        name = name.strip()
        if not name:
            click.echo("Name cannot be empty.")
            raise SystemExit(1)
        existing = models.User.query.filter(
            db.func.lower(models.User.name) == name.lower()
        ).first()
        if existing is not None:
            state = "active" if existing.is_active else "retired"
            click.echo(f'User "{existing.name}" already exists ({state}) — left untouched.')
            return
        user = models.User(name=name, is_active=True)
        if password:
            user.set_password(password)
        db.session.add(user)
        db.session.commit()
        if password:
            click.echo(f'Created "{name}" with a password — they can log in now.')
        else:
            click.echo(f'Created "{name}". Set a password with:  flask set-password "{name}"')

    @app.cli.command("eval-recipes")
    @click.option("--provider", "provider_name", default=None,
                  help="Override LLM_PROVIDER for this run (mock | anthropic | gemini). "
                       "Defaults to the configured provider.")
    @click.option("--temperature", type=float, default=None,
                  help="Override temperature. Defaults to a low eval value (0.2) for "
                       "tight, comparable diffs; pass --temperature 0.8 for a "
                       "production sanity pass.")
    @click.option("--only", default=None, help="Run a single golden brief by name.")
    def eval_recipes(provider_name, temperature, only):
        """Run the golden briefs through the provider; print + save PASS/FAIL + output."""
        from .eval.harness import run_eval
        run_eval(app.config, provider_name=provider_name,
                 temperature=temperature, only=only, echo=click.echo)

    @app.cli.command("resolve-eval")
    @click.option("--threshold", type=float, default=None,
                  help="Override the fuzzy match threshold for this run. Defaults "
                       "to the resolver's tuned FUZZY_THRESHOLD. Pure-function, "
                       "DB-free eval — no provider or network needed.")
    def resolve_eval(threshold):
        """Run the ingredient resolver over the golden set; print + save match
        rate, false-links (must be 0), misses, and the per-method breakdown."""
        from .eval.resolver_harness import run_resolver_eval
        ok = run_resolver_eval(threshold=threshold, echo=click.echo)
        raise SystemExit(0 if ok else 1)

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
