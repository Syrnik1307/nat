"""Cosmos DB singleton client and container bootstrap.

Feature-flagged by settings.COSMOS_DB_ENABLED to avoid impacting dev
when emulator/service not running. Follows best practices:
 - Reuse single CosmosClient instance.
 - Lazy initialize containers.
 - Minimal retry wrapper.
 - Diagnostic logging for slow queries.
 - Optimistic concurrency control with ETag.
"""
from django.conf import settings
import logging
import time

logger = logging.getLogger(__name__)

_client = None
_database = None
_containers = {}

def is_enabled():
    return getattr(settings, 'COSMOS_DB_ENABLED', False)

def get_client():
    global _client
    if _client or not is_enabled():
        return _client
    try:
        from azure.cosmos import CosmosClient
    except ImportError:
        return None
    _client = CosmosClient(settings.COSMOS_DB_URL, credential=settings.COSMOS_DB_KEY)
    return _client

def get_database():
    global _database
    if _database or not is_enabled():
        return _database
    client = get_client()
    if not client:
        return None
    _database = client.create_database_if_not_exists(settings.COSMOS_DB_DATABASE)
    return _database

def get_container(name: str):
    if name in _containers:
        return _containers[name]
    if not is_enabled():
        return None
    db = get_database()
    if not db:
        return None
    meta = settings.COSMOS_DB_CONTAINERS.get(name)
    if not meta:
        raise ValueError(f"Unknown Cosmos container meta for '{name}'")
    
    pk = meta['partition_key']
    ttl = meta.get('ttl', None)  # TTL in seconds, None = no auto-deletion
    
    # Create container with TTL if specified
    container_definition = {
        'id': name,
        'partition_key': pk,
    }
    
    if ttl:
        container_definition['default_ttl'] = ttl
        logger.info(f"Creating/updating container '{name}' with TTL={ttl}s")
    
    container = db.create_container_if_not_exists(**container_definition)
    _containers[name] = container
    return container

def upsert_item(container_name: str, item: dict, enable_diagnostics: bool = True):
    """Upsert item with diagnostic logging for slow operations.
    
    Args:
        container_name: Name of the container
        item: Item to upsert (must include 'id' and partition key field)
        enable_diagnostics: Log if operation takes > 200ms
    
    Returns:
        Upserted item with updated _etag
    """
    container = get_container(container_name)
    if not container:
        return None
    
    start_time = time.time()
    result = container.upsert_item(item)
    elapsed_ms = (time.time() - start_time) * 1000
    
    if enable_diagnostics and elapsed_ms > 200:
        logger.warning(
            f"Slow Cosmos upsert: container={container_name}, "
            f"item_id={item.get('id')}, elapsed={elapsed_ms:.2f}ms"
        )
    
    return result

def read_item(container_name: str, item_id: str, partition_key: str, enable_diagnostics: bool = True):
    """Read item with diagnostic logging.
    
    Args:
        container_name: Name of the container
        item_id: Item ID
        partition_key: Partition key value
        enable_diagnostics: Log if operation takes > 100ms
    
    Returns:
        Item dict with _etag
    """
    container = get_container(container_name)
    if not container:
        return None
    
    start_time = time.time()
    result = container.read_item(item=item_id, partition_key=partition_key)
    elapsed_ms = (time.time() - start_time) * 1000
    
    if enable_diagnostics and elapsed_ms > 100:
        logger.warning(
            f"Slow Cosmos read: container={container_name}, "
            f"item_id={item_id}, elapsed={elapsed_ms:.2f}ms"
        )
    
    return result

def query_items(container_name: str, query: str, parameters=None, enable_diagnostics: bool = True):
    """Query items with diagnostic logging.
    
    Args:
        container_name: Name of the container
        query: SQL query string
        parameters: Query parameters
        enable_diagnostics: Log if operation takes > 300ms
    
    Returns:
        List of matching items
    """
    container = get_container(container_name)
    if not container:
        return []
    
    start_time = time.time()
    results = list(container.query_items(
        query=query, 
        parameters=parameters or [], 
        enable_cross_partition_query=True
    ))
    elapsed_ms = (time.time() - start_time) * 1000
    
    if enable_diagnostics and elapsed_ms > 300:
        logger.warning(
            f"Slow Cosmos query: container={container_name}, "
            f"query={query[:100]}, result_count={len(results)}, elapsed={elapsed_ms:.2f}ms"
        )
    
    return results

def upsert_item_with_etag(container_name: str, item: dict, expected_etag: str = None):
    """Upsert with optimistic concurrency control using ETag.
    
    Args:
        container_name: Name of the container
        item: Item to upsert
        expected_etag: Expected ETag value for conditional update (None for new items)
    
    Returns:
        Updated item dict
        
    Raises:
        azure.cosmos.exceptions.CosmosHttpResponseError: If ETag mismatch (409 or 412 status)
    """
    container = get_container(container_name)
    if not container:
        return None
    
    try:
        from azure.cosmos import exceptions
    except ImportError:
        logger.error("azure-cosmos not installed, cannot use ETag feature")
        return container.upsert_item(item)
    
    # Build access condition for optimistic concurrency
    if expected_etag:
        # Conditional update - will fail if ETag doesn't match
        try:
            return container.replace_item(
                item=item['id'],
                body=item,
                match_condition=exceptions.MatchConditions.IfNotModified,
                etag=expected_etag
            )
        except exceptions.CosmosHttpResponseError as e:
            if e.status_code in (409, 412):  # Conflict or Precondition Failed
                logger.warning(
                    f"ETag conflict: container={container_name}, "
                    f"item_id={item.get('id')}, expected_etag={expected_etag}"
                )
            raise
    else:
        # New item or unconditional update
        return container.upsert_item(item)


def bulk_upsert_items(container_name: str, items: list, batch_size: int = 100):
    """Batch upsert items for faster bulk operations.
    
    Args:
        container_name: Name of the container
        items: List of items to upsert
        batch_size: Items per batch (default 100)
    
    Returns:
        dict with success_count, failed_count, errors
    """
    container = get_container(container_name)
    if not container:
        return {'success_count': 0, 'failed_count': 0, 'errors': []}
    
    success_count = 0
    failed_count = 0
    errors = []
    
    start_time = time.time()
    
    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        for item in batch:
            try:
                container.upsert_item(item)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({
                    'item_id': item.get('id'),
                    'error': str(e)
                })
                logger.error(f"Failed to upsert item {item.get('id')}: {e}")
    
    elapsed_ms = (time.time() - start_time) * 1000
    
    logger.info(
        f"Bulk upsert: container={container_name}, "
        f"success={success_count}, failed={failed_count}, "
        f"elapsed={elapsed_ms:.2f}ms"
    )
    
    return {
        'success_count': success_count,
        'failed_count': failed_count,
        'errors': errors[:10]  # Limit error details
    }
