import os
import shutil
from pathlib import Path
from typing import List
from .base import StorageBackend

try:
    import boto3
except ImportError:
    boto3 = None

class S3Storage(StorageBackend):
    def __init__(self, path: str, **kwargs):
        super().__init__(path, **kwargs)
        if boto3 is None:
            raise ImportError("boto3 is required for S3 storage. Please install it with `pip install boto3`.")
        
        # Parse path s3://bucket/prefix
        if not path.startswith("s3://"):
             raise ValueError("S3 path must start with s3://")
        
        without_scheme = path[5:]
        parts = without_scheme.split("/", 1)
        self.bucket_name = parts[0]
        self.prefix = parts[1] if len(parts) > 1 else ""
        if self.prefix and not self.prefix.endswith("/"):
            self.prefix += "/"

        # Initialize boto3 client
        self.s3 = boto3.client(
            "s3",
            region_name=kwargs.get("region"),
            aws_access_key_id=kwargs.get("access_key"),
            aws_secret_access_key=kwargs.get("secret_key"),
        )

    def _get_prefix(self, model_name: str, version: str = None) -> str:
        p = f"{self.prefix}{model_name}/"
        if version:
            p += f"{version}/"
        return p

    def list_models(self) -> List[str]:
        # List "directories" under prefix
        # S3 doesn't have dirs, so we look for common prefixes
        paginator = self.s3.get_paginator("list_objects_v2")
        iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix, Delimiter="/")
        
        models = []
        for page in iterator:
            for prefix in page.get("CommonPrefixes", []):
                # Prefix is like "repos/model_name/"
                # Remove self.prefix from start and / from end
                rel = prefix["Prefix"][len(self.prefix):].rstrip("/")
                if rel:
                    models.append(rel)
        return sorted(models)

    def get_model_versions(self, model_name: str) -> List[str]:
        model_prefix = self._get_prefix(model_name)
        paginator = self.s3.get_paginator("list_objects_v2")
        iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=model_prefix, Delimiter="/")
        
        versions = []
        for page in iterator:
             for prefix in page.get("CommonPrefixes", []):
                # Prefix is like "repos/model_name/v1/"
                # Remove model_prefix from start
                rel = prefix["Prefix"][len(model_prefix):].rstrip("/")
                if rel:
                    versions.append(rel)
        return sorted(versions)

    def upload_version(self, model_name: str, version: str, local_path: Path):
        dest_prefix = self._get_prefix(model_name, version)
        
        # Check if exists (check if any object exists with that prefix)
        resp = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=dest_prefix, MaxKeys=1)
        if "Contents" in resp:
             raise FileExistsError(f"Version {version} for model {model_name} already exists in S3.")

        local_path = Path(local_path)
        for root, dirs, files in os.walk(local_path):
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(local_path)
                s3_key = f"{dest_prefix}{rel_path}"
                self.s3.upload_file(str(full_path), self.bucket_name, s3_key)

    def download_version(self, model_name: str, version: str, dest_path: Path):
        source_prefix = self._get_prefix(model_name, version)
        dest_path = Path(dest_path)
        
        paginator = self.s3.get_paginator("list_objects_v2")
        iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=source_prefix)
        
        found = False
        for page in iterator:
            for obj in page.get("Contents", []):
                found = True
                s3_key = obj["Key"]
                # s3_key = repos/model/v1/file.txt
                # rel_path = file.txt
                rel_path = s3_key[len(source_prefix):]
                if not rel_path: continue # is the directory itself?

                local_file = dest_path / rel_path
                local_file.parent.mkdir(parents=True, exist_ok=True)
                self.s3.download_file(self.bucket_name, s3_key, str(local_file))
        
        if not found:
             raise FileNotFoundError(f"Version {version} for model {model_name} not found in S3.")

    def delete_model(self, model_name: str):
         # Delete everything under model prefix
         model_prefix = self._get_prefix(model_name)
         
         paginator = self.s3.get_paginator("list_objects_v2")
         iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=model_prefix)
         
         for page in iterator:
             if "Contents" in page:
                 objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
                 self.s3.delete_objects(Bucket=self.bucket_name, Delete={"Objects": objects})

    def delete_version(self, model_name: str, version: str):
        version_prefix = self._get_prefix(model_name, version)
        
        paginator = self.s3.get_paginator("list_objects_v2")
        iterator = paginator.paginate(Bucket=self.bucket_name, Prefix=version_prefix)
        
        found = False
        for page in iterator:
            if "Contents" in page:
                found = True
                objects = [{"Key": obj["Key"]} for obj in page["Contents"]]
                self.s3.delete_objects(Bucket=self.bucket_name, Delete={"Objects": objects})
        
        if not found:
             # S3 doesn't really have "not found" for delete, but if we want to be strict:
             # Check if we found anything to delete. 
             # However, this might be expensive to check first.
             # The loop above sets found=True if it deleted something.
             raise FileNotFoundError(f"Version {version} for model {model_name} not found (or already deleted).")

