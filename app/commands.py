import click
from flask.cli import with_appcontext
from app import db
from app.models import Utilisateur, RoleEnum

def init_app(app):
    """Enregistre les commandes CLI avec l'application Flask."""
    app.cli.add_command(create_admin_command)

@click.command('create-admin')
@with_appcontext
@click.argument('prenom')
@click.argument('nom')
@click.argument('email')
@click.argument('password')
def create_admin_command(prenom, nom, email, password):
    """Crée un nouvel utilisateur avec le rôle administrateur."""
    if Utilisateur.query.filter_by(email=email).first():
        click.echo(f"L'utilisateur avec l'email {email} existe déjà.")
        return

    admin_user = Utilisateur(
        prenom=prenom,
        nom=nom,
        email=email,
        role=RoleEnum.ADMINISTRATEUR
    )
    admin_user.set_password(password)
    db.session.add(admin_user)
    db.session.commit()
    click.echo(f"Administrateur '{prenom} {nom}' créé avec succès.")