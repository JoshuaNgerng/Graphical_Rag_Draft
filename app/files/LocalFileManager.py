from pathlib import Path
import tempfile
from uuid import uuid4
from functools import lru_cache

from app.core.config import Config, get_config
from app.files.FileManagerInterface import FileManagerInterface

class LocalStorage(FileManagerInterface):
    def __init__(self, config: Config):
        root = config.STORAGE_ROOT_DIR
        root_dir = Path(root) if root else Path(tempfile.gettempdir()) 
        self.root_dir = root_dir / config.APP_NAME
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def upload_file(self, file_name: str | None, file_bytes: bytes) -> str:
        if not file_name:
            file_name = str(uuid4())
        file_name_ = Path(file_name)
        file_name = f'{file_name_.stem}_{uuid4()}{file_name_.suffix}'
        file_path = self.root_dir / file_name
        try:
            file_path.write_bytes(file_bytes)
        except Exception as e:
            raise RuntimeError(f"Upload file failed: {e}")
        return file_name

    def download_file(self, object_key: str) -> bytes:
        try:
            file_path = self.root_dir / object_key
            return file_path.read_bytes()
        except Exception as e:
            raise RuntimeError(f"Download file failed: {e}")

@lru_cache
def get_local_storage():
    return LocalStorage(get_config())