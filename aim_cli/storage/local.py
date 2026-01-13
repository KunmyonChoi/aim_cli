import shutil
import os
from pathlib import Path
from typing import List
from .base import StorageBackend

class LocalStorage(StorageBackend):
    def __init__(self, path: str, **kwargs):
        super().__init__(path, **kwargs)
        self.root_path = Path(path)
        if not self.root_path.exists():
            # For NFS/Local, might want to create it if it doesn't exist?
            # Or assume admin mounted it already. Let's try to create for user friendliness.
            try:
                self.root_path.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass # Might be permission issue if it's a strict mount, ignore for now

    def _model_path(self, model_name: str) -> Path:
        return self.root_path / model_name

    def list_models(self) -> List[str]:
        if not self.root_path.exists():
            return []
        
        models = []
        for x in self.root_path.iterdir():
            if x.is_dir() and not x.name.startswith("."):
                models.append(x.name)
        return sorted(models)

    def get_model_versions(self, model_name: str) -> List[str]:
        model_path = self._model_path(model_name)
        if not model_path.exists():
            return []
        
        versions = []
        for x in model_path.iterdir():
            if x.is_dir() and not x.name.startswith("."):
                versions.append(x.name)
        return sorted(versions)

    def upload_version(self, model_name: str, version: str, local_path: Path):
        dest_path = self._model_path(model_name) / version
        if dest_path.exists():
            raise FileExistsError(f"Version {version} for model {model_name} already exists.")
        
        local_path = Path(local_path)
        if not local_path.exists():
             raise FileNotFoundError(f"Source path {local_path} does not exist.")

        # Copy directory
        shutil.copytree(local_path, dest_path)

    def download_version(self, model_name: str, version: str, dest_path: Path):
        source_path = self._model_path(model_name) / version
        if not source_path.exists():
            raise FileNotFoundError(f"Version {version} for model {model_name} not found.")

        dest_path = Path(dest_path)
        if dest_path.exists():
             # Option: overwrite or error. For safety error.
             if any(dest_path.iterdir()):
                 raise FileExistsError(f"Destination {dest_path} is not empty.")
        
        # copytree requires dest not to exist usually, or dirs_exist_ok in newer python
        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)

    def delete_model(self, model_name: str):
        model_path = self._model_path(model_name)
        if model_path.exists():
            shutil.rmtree(model_path)

    def delete_version(self, model_name: str, version: str):
        version_path = self._model_path(model_name) / version
        if version_path.exists():
            shutil.rmtree(version_path)
        else:
             raise FileNotFoundError(f"Version {version} for model {model_name} not found.")
