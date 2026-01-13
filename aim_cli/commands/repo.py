import typer
from rich.console import Console
from rich.table import Table
from aim_cli.config import load_config, save_config, RepoConfig

app = typer.Typer()
console = Console()

@app.command()
def create(
    name: str = typer.Argument(..., help="Name of the repository to create"),
    type: str = typer.Option(..., help="Type of storage: 'local' or 's3'"),
    path: str = typer.Option(..., help="Path or URL for the storage"),
    region: str = typer.Option(None, help="AWS Region (for S3 only)"),
    access_key: str = typer.Option(None, help="AWS Access Key (for S3 only)"),
    secret_key: str = typer.Option(None, help="AWS Secret Key (for S3 only)"),
):
    """Register a new model repository."""
    if type not in ["local", "s3"]:
        console.print(f"[bold red]Error:[/bold red] Invalid type '{type}'. Must be 'local' or 's3'.")
        raise typer.Exit(code=1)

    config = load_config()
    if config.get_repo(name):
        console.print(f"[bold red]Error:[/bold red] Repo '{name}' already exists.")
        raise typer.Exit(code=1)

    new_repo = RepoConfig(
        name=name,
        type=type,
        path=path,
        region=region,
        access_key=access_key,
        secret_key=secret_key
    )
    
    config.add_repo(new_repo)
    save_config(config)
    console.print(f"[green]Repo '{name}' created successfully![/green]")

@app.command("list")
def list_repos():
    """List all registered repositories."""
    config = load_config()
    if not config.repos:
        console.print("No repositories found.")
        return

    table = Table(title="Model Repositories")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Path", style="green")

    for repo in config.repos:
        table.add_row(repo.name, repo.type, repo.path)
    
    console.print(table)

@app.command()
def delete(name: str):
    """Unregister a repository."""
    config = load_config()
    if config.remove_repo(name):
        save_config(config)
        console.print(f"[green]Repo '{name}' deleted.[/green]")
    else:
        console.print(f"[red]Repo '{name}' not found.[/red]")
