import os
import paramiko
import stat
from pathlib import Path
from typing import List
from urllib.parse import urlparse
from .base import StorageBackend

class SFTPStorage(StorageBackend):
    def __init__(self, path: str, **kwargs):
        super().__init__(path, **kwargs)
        
        # Expect path like sftp://hostname/path/to/repo
        if not path.startswith("sftp://"):
            raise ValueError("SFTP path must start with sftp://")

        parsed = urlparse(path)
        self.hostname = parsed.hostname
        self.port = parsed.port or 22
        self.username = kwargs.get("username") or parsed.username
        self.password = kwargs.get("password") or parsed.password
        # Used for key-based auth if needed, though simple implementation uses password or agent
        self.key_filename = kwargs.get("key_filename") 
        
        # Remote path
        self.remote_root = parsed.path
        if not self.remote_root:
             self.remote_root = "."
        elif not self.remote_root.endswith("/"):
             self.remote_root += "/"

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            connect_params = {
                "hostname": self.hostname,
                "port": self.port,
                "username": self.username,
            }
            if self.password:
                connect_params["password"] = self.password
            if self.key_filename:
                connect_params["key_filename"] = self.key_filename
                
            self.ssh.connect(**connect_params)
            self.sftp = self.ssh.open_sftp()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to SFTP server: {e}")

    def __del__(self):
        if hasattr(self, "sftp"):
            self.sftp.close()
        if hasattr(self, "ssh"):
            self.ssh.close()

    def _get_remote_path(self, model_name: str, version: str = None) -> str:
        # Join cleanly with forward slashes for SFTP
        p = f"{self.remote_root}{model_name}/"
        if version:
            p += f"{version}/"
        # Ensure only single slashes
        return p.replace("//", "/")

    def _list_dirs(self, remote_path: str) -> List[str]:
        try:
            return [
                f for f in self.sftp.listdir(remote_path)
                if self._is_dir(remote_path, f)
            ]
        except FileNotFoundError:
            return []

    def _is_dir(self, remote_base: str, filename: str) -> bool:
        try:
            file_attr = self.sftp.stat(f"{remote_base}/{filename}".replace("//", "/"))
            return stat.S_ISDIR(file_attr.st_mode)
        except OSError:
            return False

    def list_models(self) -> List[str]:
        # models are directories in the root
        return sorted(self._list_dirs(self.remote_root))

    def get_model_versions(self, model_name: str) -> List[str]:
        model_path = self._get_remote_path(model_name)
        return sorted(self._list_dirs(model_path))

    def _mkdir_p(self, remote_directory):
        """Make remote directories recursively"""
        if remote_directory == '/':
            self.sftp.chdir('/')
            return
        if remote_directory == '':
            return
        
        try:
            self.sftp.chdir(remote_directory)
        except IOError:
            dirname, basename = os.path.split(remote_directory.rstrip('/'))
            self._mkdir_p(dirname)
            try:
                self.sftp.mkdir(basename)
                self.sftp.chdir(basename)
                return True
            except IOError:
                # Should already exist
                pass

    def upload_version(self, model_name: str, version: str, local_path: Path):
        dest_remote = self._get_remote_path(model_name, version)
        
        # Check if exists
        try:
            self.sftp.stat(dest_remote)
            raise FileExistsError(f"Version {version} for model {model_name} already exists on SFTP.")
        except FileNotFoundError:
            pass

        local_path = Path(local_path)
        
        # Walk local
        for root, dirs, files in os.walk(local_path):
            for file in files:
                full_local_path = Path(root) / file
                rel_path = full_local_path.relative_to(local_path)
                
                # Construct remote path
                remote_file_path = f"{dest_remote}{rel_path}".replace("\\", "/") # Ensure forward slashes
                remote_dir = os.path.dirname(remote_file_path)
                
                self._mkdir_p(remote_dir)
                self.sftp.put(str(full_local_path), remote_file_path)

    def download_version(self, model_name: str, version: str, dest_path: Path):
        source_remote = self._get_remote_path(model_name, version)
        dest_path = Path(dest_path)
        
        try:
            self.sftp.stat(source_remote)
        except FileNotFoundError:
            raise FileNotFoundError(f"Version {version} for model {model_name} not found on SFTP.")

        # Recursive download is tricky with paramiko, need to walk remote
        # A simple recursive walker
        self._download_dir(source_remote, dest_path)

    def _download_dir(self, remote_dir: str, local_dir: Path):
        local_dir.mkdir(parents=True, exist_ok=True)
        
        for item in self.sftp.listdir_attr(remote_dir):
            remote_path = f"{remote_dir}/{item.filename}".replace("//", "/")
            local_path = local_dir / item.filename
            
            if stat.S_ISDIR(item.st_mode):
                self._download_dir(remote_path, local_path)
            else:
                self.sftp.get(remote_path, str(local_path))

    def _rmtree(self, remote_path):
        """Recursively delete a directory tree on remote."""
        for item in self.sftp.listdir_attr(remote_path):
             path = f"{remote_path}/{item.filename}".replace("//", "/")
             if stat.S_ISDIR(item.st_mode):
                 self._rmtree(path)
             else:
                 self.sftp.remove(path)
        self.sftp.rmdir(remote_path)

    def delete_model(self, model_name: str):
        model_path = self._get_remote_path(model_name)
        try:
            self._rmtree(model_path)
        except FileNotFoundError:
             pass # Already gone

    def delete_version(self, model_name: str, version: str):
        version_path = self._get_remote_path(model_name, version)
        try:
            self._rmtree(version_path)
        except FileNotFoundError:
             raise FileNotFoundError(f"Version {version} for model {model_name} not found.")

