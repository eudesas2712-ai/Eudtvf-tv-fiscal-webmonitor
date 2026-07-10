import boto3
import os
from botocore.client import Config
from app.core.config import settings

def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

def ensure_bucket():
    client = get_minio_client()
    bucket_name = settings.MINIO_BUCKET

    existing = client.list_buckets()
    bucket_names = [b["Name"] for b in existing.get("Buckets", [])]

    if bucket_name not in bucket_names:
        client.create_bucket(Bucket=bucket_name)

def save_html_evidence(key: str, html_content: str):
    client = get_minio_client()
    ensure_bucket()

    client.put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=key,
        Body=html_content.encode("utf-8"),
        ContentType="text/html"
    )

    public_base = os.getenv("EVIDENCE_PUBLIC_BASE_URL") or f"http://localhost:9000/{settings.MINIO_BUCKET}"
    public_url = f"{public_base.rstrip('/')}/{key}"
    return key, public_url

def save_binary_evidence(key: str, content: bytes, content_type: str):
    client = get_minio_client()
    ensure_bucket()

    client.put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type
    )

    public_base = os.getenv("EVIDENCE_PUBLIC_BASE_URL") or f"http://localhost:9000/{settings.MINIO_BUCKET}"
    public_url = f"{public_base.rstrip('/')}/{key}"
    return key, public_url

def get_binary_from_url(url: str):
    import requests
    response = requests.get(url, timeout=30, verify=False)
    response.raise_for_status()
    return response.content