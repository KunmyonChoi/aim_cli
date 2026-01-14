import os
import yaml
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE_NAME = "model_repos.yaml"

class RepoConfig(BaseModel):
    name: str
    type: Literal["local", "s3", "sftp"]
    path: str
    region: Optional[str] = None
    # Passwords/Secrets are excluded from YAML dump but loaded from Env
    access_key: Optional[str] = Field(None, exclude=True) 
    secret_key: Optional[str] = Field(None, exclude=True)
    username: Optional[str] = None
    password: Optional[str] = Field(None, exclude=True)

    def load_secrets(self):
        """Populate secrets from environment variables based on convention."""
        # Convention: AIM_REPO_{NAME}_PASSWORD / SECRET_KEY / ACCESS_KEY
        normalized_name = self.name.upper().replace("-", "_")
        
        if not self.password:
            self.password = os.getenv(f"AIM_REPO_{normalized_name}_PASSWORD")
        if not self.secret_key:
            self.secret_key = os.getenv(f"AIM_REPO_{normalized_name}_SECRET_KEY")
        if not self.access_key:
            self.access_key = os.getenv(f"AIM_REPO_{normalized_name}_ACCESS_KEY")


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
            
            gc = GlobalConfig(**data)
            for repo in gc.repos:
                repo.load_secrets()
            return gc
    except Exception as e:
        print(f"Warning: Failed to load config file: {e}")
        return GlobalConfig()

def save_config(config: GlobalConfig):
    config_path = get_config_path()
    with open(config_path, "w") as f:
        # exclude_defaults=True to keep config clean, and use Field(exclude=True) for secrets
        data = config.model_dump(mode="json", exclude_none=True)
        yaml.dump(data, f, sort_keys=False)
