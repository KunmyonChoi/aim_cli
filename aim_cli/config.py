import os
import yaml
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from pathlib import Path

CONFIG_FILE_NAME = "model_repos.yaml"

class RepoConfig(BaseModel):
    name: str
    type: Literal["local", "s3"]
    path: str
    region: Optional[str] = None
    access_key: Optional[str] = None  # In real apps, be careful with secrets
    secret_key: Optional[str] = None

class GlobalConfig(BaseModel):
    repos: List[RepoConfig] = Field(default_factory=list)

    def get_repo(self, name: str) -> Optional[RepoConfig]:
        for repo in self.repos:
            if repo.name == name:
                return repo
        return None

    def add_repo(self, repo: RepoConfig):
        # Remove existing if same name to update
        self.repos = [r for r in self.repos if r.name != repo.name]
        self.repos.append(repo)
    
    def remove_repo(self, name: str) -> bool:
        original_len = len(self.repos)
        self.repos = [r for r in self.repos if r.name != name]
        return len(self.repos) < original_len

def get_config_path() -> Path:
    # Look for config in current dir or user home
    # For MVP, simplify to current working directory or specific global path
    # Using current dir allows easy sharing via git
    return Path(os.getcwd()) / CONFIG_FILE_NAME

def load_config() -> GlobalConfig:
    config_path = get_config_path()
    if not config_path.exists():
        return GlobalConfig()
    
    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
            # Handle empty file case
            if not data:
                return GlobalConfig()
            return GlobalConfig(**data)
    except Exception as e:
        print(f"Warning: Failed to load config file: {e}")
        return GlobalConfig()

def save_config(config: GlobalConfig):
    config_path = get_config_path()
    with open(config_path, "w") as f:
        # exclude_none=True to keep config clean
        data = config.model_dump(mode="json", exclude_none=True)
        yaml.dump(data, f, sort_keys=False)
