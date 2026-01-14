import typer
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from aim_cli.config import load_config, RepoConfig
from aim_cli.storage.local import LocalStorage
from aim_cli.storage.s3 import S3Storage
from aim_cli.storage.sftp import SFTPStorage

app = typer.Typer()
console = Console()

def get_storage(repo_name: str):
    config = load_config()
    repo = config.get_repo(repo_name)
    if not repo:
        console.print(f"[bold red]Error:[/bold red] Repo '{repo_name}' not found.")
        raise typer.Exit(code=1)
    
    if repo.type == "local":
        return LocalStorage(repo.path)
    elif repo.type == "s3":
        return S3Storage(repo.path, region=repo.region, access_key=repo.access_key, secret_key=repo.secret_key)
    elif repo.type == "sftp":
        return SFTPStorage(repo.path, username=repo.username, password=repo.password)
    else:
        console.print(f"[bold red]Error:[/bold red] Unknown storage type '{repo.type}'.")
        raise typer.Exit(code=1)

@app.command("list")
def list_models(repo: str):
    """List models in a repository."""
    storage = get_storage(repo)
    models = storage.list_models()
    
    table = Table(title=f"Models in {repo}")
    table.add_column("Model Name")
    
    for m in models:
        table.add_row(m)
    console.print(table)

@app.command()
def create(repo: str, name: str):
    """Create a new model (placeholder command - creating a version actually creates it)."""
    # In this design, models are implicitly created when versions are pushed, 
    # but we could create an empty dir or metadata file if needed.
    # For now, just check if it exists or do nothing.
    storage = get_storage(repo)
    existing = storage.list_models()
    if name in existing:
        console.print(f"[yellow]Model '{name}' already exists in {repo}.[/yellow]")
    else:
        console.print(f"[green]Model '{name}' is ready to accept versions. Use 'push' to upload data.[/green]")

@app.command()
def push(
    repo: str, 
    model: str, 
    path: Path = typer.Argument(..., help="Local path to model directory"), 
    tag: str = typer.Option(..., help="Version tag (e.g. v1, 2023-10-01)")
):
    """Push a local directory as a new version of a model."""
    storage = get_storage(repo)
    if not path.exists():
        console.print(f"[red]Error: Local path '{path}' does not exist.[/red]")
        raise typer.Exit(code=1)
    
    console.print(f"Uploading '{path}' to {repo}/{model}:{tag} ...")
    try:
        storage.upload_version(model, tag, path)
        console.print(f"[green]Successfully pushed {model}:{tag}[/green]")
    except Exception as e:
        console.print(f"[red]Error uploading:[/red] {e}")
        raise typer.Exit(code=1)

@app.command()
def pull(
    repo: str, 
    model: str, 
    dest: Path = typer.Argument(..., help="Destination directory"), 
    tag: str = typer.Option(..., help="Version tag to pull")
):
    """Pull a model version to a local directory."""
    storage = get_storage(repo)
    
    console.print(f"Downloading {repo}/{model}:{tag} to '{dest}' ...")
    try:
        storage.download_version(model, tag, dest)
        console.print(f"[green]Successfully pulled {model}:{tag}[/green]")
    except Exception as e:
        console.print(f"[red]Error downloading:[/red] {e}")
        raise typer.Exit(code=1)

@app.command()
def versions(repo: str, model: str):
    """List versions of a model."""
    storage = get_storage(repo)
    versions = storage.get_model_versions(model)
    
    table = Table(title=f"Versions for {model} in {repo}")
    table.add_column("Version")
    
    for v in versions:
        table.add_row(v)
    console.print(table)

@app.command()
def delete(repo: str, model: str, force: bool = typer.Option(False, "--force", "-f", help="Force delete without confirmation")):
    """Delete a model and ALL its versions."""
    if not force:
        if not typer.confirm(f"Are you sure you want to delete model '{model}' and all its versions from '{repo}'?"):
            raise typer.Abort()
    
    storage = get_storage(repo)
    try:
        storage.delete_model(model)
        console.print(f"[green]Model '{model}' deleted from '{repo}'.[/green]")
    except Exception as e:
        console.print(f"[red]Error deleting model:[/red] {e}")
        raise typer.Exit(code=1)

@app.command("delete-version")
def delete_version(
    repo: str, 
    model: str, 
    tag: str = typer.Option(..., help="Version tag to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Force delete without confirmation")
):
    """Delete a specific version of a model."""
    if not force:
         if not typer.confirm(f"Are you sure you want to delete version '{tag}' of model '{model}' from '{repo}'?"):
            raise typer.Abort()
            
    storage = get_storage(repo)
    try:
        storage.delete_version(model, tag)
        console.print(f"[green]Version '{tag}' of model '{model}' deleted from '{repo}'.[/green]")
    except Exception as e:
        console.print(f"[red]Error deleting version:[/red] {e}")
        raise typer.Exit(code=1)
