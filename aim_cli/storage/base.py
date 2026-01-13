from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pathlib import Path

class StorageBackend(ABC):
    def __init__(self, path: str, **kwargs):
        self.path = path
        self.config = kwargs

    @abstractmethod
    def list_models(self) -> List[str]:
        """List all model names in the repo."""
        pass

    @abstractmethod
    def get_model_versions(self, model_name: str) -> List[str]:
        """List all versions for a given model."""
        pass

    @abstractmethod
    def upload_version(self, model_name: str, version: str, local_path: Path):
        """Upload a local directory as a new version of the model."""
        pass

    @abstractmethod
    def download_version(self, model_name: str, version: str, dest_path: Path):
        """Download a specific version of the model to a local directory."""
        pass

    @abstractmethod
    def delete_model(self, model_name: str):
        """Delete a model and all its versions."""
        pass

    @abstractmethod
    def delete_version(self, model_name: str, version: str):
        """Delete a specific version of a model."""
        pass
