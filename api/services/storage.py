# api/services/storage.py
import os
import boto3
from botocore.config import Config

AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION    = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
S3_BUCKET             = os.getenv("S3_BUCKET")
S3_PREFIX             = os.getenv("S3_PREFIX", "")

_s3 = boto3.client(
    "s3",
    region_name=AWS_DEFAULT_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
)

def s3_put_bytes(client_id: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """上傳 bytes 到 S3，回傳 s3 路徑。"""
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET not set")
    prefix = (S3_PREFIX or "").rstrip("/")
    tenant_prefix = f"{prefix}/{client_id}".lstrip("/")
    full_key = f"{tenant_prefix}/{key}".lstrip("/")
    _s3.put_object(Bucket=S3_BUCKET, Key=full_key, Body=data, ContentType=content_type)
    return f"s3://{S3_BUCKET}/{full_key}"
