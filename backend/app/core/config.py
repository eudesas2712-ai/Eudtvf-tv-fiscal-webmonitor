import os

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://webmonitor:webmonitor@postgres:5432/webmonitor")
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
    OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
    OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "webmonitor-items")
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "evidence")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()