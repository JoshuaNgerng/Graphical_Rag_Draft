from uuid import uuid4
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Config
from app.files.FileManagerInterface import FileManagerInterface

class MinIOManager(FileManagerInterface):
    def __init__(self, config: Config) -> None:
        self.bucket = config.MINIO_BUCKET

        self.client = boto3.client(
            "s3",
            endpoint_url=config.MINIO_ENDPOINT,
            aws_access_key_id=config.MINIO_ROOT_USER,
            aws_secret_access_key=config.MINIO_ROOT_PASSWORD,
            region_name=config.MINIO_REGION,
        )

        # self._ensure_bucket_exists()

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

    def _ensure_bucket_exists(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response["Error"].get("Code")

            if error_code in ("404", "NoSuchBucket"):
                self.client.create_bucket(Bucket=self.bucket)
            else:
                raise