from opensearchpy import OpenSearch
from app.core.config import settings

def os_client():
    return OpenSearch(settings.opensearch_url)

def ensure_index():
    client = os_client()
    index = settings.opensearch_index
    if client.indices.exists(index=index):
        return

    body = {
        "settings": {
            "index": {"number_of_shards": 1, "number_of_replicas": 0},
            "analysis": {
                "analyzer": {
                    "pt_analyzer": {"type": "standard"}
                }
            }
        },
        "mappings": {
            "properties": {
                "project_id": {"type": "keyword"},
                "item_id": {"type": "keyword"},
                "source_name": {"type": "keyword"},
                "url": {"type": "keyword"},
                "canonical_url": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "pt_analyzer"},
                "body": {"type": "text", "analyzer": "pt_analyzer"},
                "published_at": {"type": "date"},
                "fetched_at": {"type": "date"},
                "severity": {"type": "keyword"},
                "score": {"type": "float"},
                "matched_terms": {"type": "keyword"}
            }
        }
    }
    client.indices.create(index=index, body=body)

def index_item(doc: dict):
    client = os_client()
    ensure_index()
    client.index(index=settings.opensearch_index, id=doc["item_id"], body=doc, refresh=True)

def search_items(project_id: str, q: str | None, filters: dict, size: int, offset: int):
    client = os_client()
    ensure_index()

    must = [{"term": {"project_id": project_id}}]
    if q:
        must.append({"multi_match": {"query": q, "fields": ["title^2", "body"]}})

    if filters.get("source_name"):
        must.append({"term": {"source_name": filters["source_name"]}})
    if filters.get("severity"):
        must.append({"term": {"severity": filters["severity"]}})

    body = {
        "from": offset,
        "size": size,
        "query": {"bool": {"must": must}},
        "sort": [{"published_at": {"order": "desc", "unmapped_type": "date"}}, {"fetched_at": {"order": "desc"}}],
    }
    resp = client.search(index=settings.opensearch_index, body=body)
    total = resp["hits"]["total"]["value"] if isinstance(resp["hits"]["total"], dict) else resp["hits"]["total"]
    hits = [h["_source"] for h in resp["hits"]["hits"]]
    return total, hits