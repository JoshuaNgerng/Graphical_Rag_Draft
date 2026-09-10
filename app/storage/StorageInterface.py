from abc import ABC, abstractmethod

from app.core.config import Config

class StorageInterface(ABC):
    @abstractmethod
    def __init__(self, config: Config) -> None: ...
    @abstractmethod
    def upload_file(self, file_name: str | None, file_bytes: bytes) -> str: ...
    @abstractmethod
    def download_file(self, object_key: str) -> bytes: ...