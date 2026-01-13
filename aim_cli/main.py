import typer
import yaml
from pathlib import Path
from aim_cli.config import load_config, save_config, RepoConfig, GlobalConfig
from aim_cli.commands import repo, model

app = typer.Typer(help="AI Model Manager CLI")

app.add_typer(repo.app, name="repo", help="Manage model repositories")
app.add_typer(model.app, name="model", help="Manage models and versions")

@app.command()
def info():
    """Show global configuration info."""
    config = load_config()
    typer.echo(f"Config loaded from: {Path.cwd()}/model_repos.yaml")
    typer.echo(f"Registered Repos: {len(config.repos)}")
    for r in config.repos:
        typer.echo(f" - {r.name} ({r.type}) -> {r.path}")

if __name__ == "__main__":
    app()
