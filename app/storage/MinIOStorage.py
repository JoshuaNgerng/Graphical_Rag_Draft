from uuid import uuid4
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Config
from app.storage.StorageInterface import StorageInterface

class MinIOStorage(StorageInterface):
    def __init__(self, config: Config) -> None:
        self.bucket = config.MINIO_BUCKET

        self.client = boto3.client(
            "s3",
            endpoint_url=config.MINIO_ENDPOINT,
            aws_access_key_id=config.MINIO_ACCESS_KEY,
            aws_secret_access_key=config.MINIO_SECRET_KEY,
            region_name=config.MINIO_REGION,
        )

    def upload_file(self, file_name: str | None, file_bytes: bytes) -> str:
        if not file_name:
            file_name = str(uuid4())

        file_name_ = Path(file_name)
        object_key = f"{file_name_.stem}_{uuid4()}{file_name_.suffix}"

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=file_bytes,
            )
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Upload file failed: {e}")

        return object_key

    def download_file(self, object_key: str) -> bytes:
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=object_key,
            )
            return response["Body"].read()
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Download file failed: {e}")

    def close(self):
        self.client.close()

