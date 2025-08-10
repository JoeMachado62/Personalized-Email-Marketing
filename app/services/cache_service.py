"""
Cache service for optimizing enrichment costs and performance.

This service provides caching capabilities to avoid duplicate API calls
and web scraping operations. It uses both in-memory and persistent caching
to minimize costs associated with LLM API calls and web scraping.
"""

import asyncio
import json
import logging
import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    hit_count: int = 0
    cost_saved: float = 0.0
    source: str = "unknown"


class CacheService:
    """
    Caching service for enrichment operations.
    
    Provides both in-memory and persistent caching to optimize costs
    and performance for enrichment operations including:
    - Website discovery results
    - AI-generated content
    - Contact information extraction
    """
    
    def __init__(self, cache_db_path: str = "data/cache.db", 
                 max_memory_entries: int = 1000,
                 default_ttl_hours: int = 24):
        self.cache_db_path = Path(cache_db_path)
        self.max_memory_entries = max_memory_entries
        self.default_ttl_hours = default_ttl_hours
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "cost_saved": 0.0
        }
        
        # Ensure cache directory exists
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the cache database."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache_entries (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT,
                        hit_count INTEGER DEFAULT 0,
                        cost_saved REAL DEFAULT 0.0,
                        source TEXT DEFAULT 'unknown'
                    )
                """)
                
                # Create index for efficient expiration cleanup
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at 
                    ON cache_entries(expires_at)
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize cache database: {e}")
    
    def _generate_cache_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Generate a consistent cache key for given operation and parameters."""
        # Sort parameters for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True)
        key_string = f"{operation}:{sorted_params}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def get(self, operation: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Retrieve cached value for the given operation and parameters.
        
        Args:
            operation: The operation type (e.g., 'website_search', 'ai_content')
            params: Parameters that uniquely identify the operation
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        cache_key = self._generate_cache_key(operation, params)
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if self._is_entry_valid(entry):
                entry.hit_count += 1
                self._cache_stats["hits"] += 1
                self._cache_stats["cost_saved"] += entry.cost_saved
                logger.debug(f"Memory cache hit for {operation}")
                return entry.value
            else:
                # Remove expired entry
                del self._memory_cache[cache_key]
        
        # Check persistent cache
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.execute("""
                    SELECT value, created_at, expires_at, hit_count, cost_saved, source
                    FROM cache_entries WHERE key = ?
                """, (cache_key,))
                
                row = cursor.fetchone()
                if row:
                    value_json, created_at_str, expires_at_str, hit_count, cost_saved, source = row
                    
                    created_at = datetime.fromisoformat(created_at_str)
                    expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else None
                    
                    entry = CacheEntry(
                        key=cache_key,
                        value=json.loads(value_json),
                        created_at=created_at,
                        expires_at=expires_at,
                        hit_count=hit_count,
                        cost_saved=cost_saved,
                        source=source
                    )
                    
                    if self._is_entry_valid(entry):
                        # Update hit count
                        entry.hit_count += 1
                        self._cache_stats["hits"] += 1
                        self._cache_stats["cost_saved"] += cost_saved
                        
                        # Store in memory cache for faster future access
                        self._store_in_memory(entry)
                        
                        # Update hit count in database
                        conn.execute("""
                            UPDATE cache_entries SET hit_count = ? WHERE key = ?
                        """, (entry.hit_count, cache_key))
                        conn.commit()
                        
                        logger.debug(f"Persistent cache hit for {operation}")
                        return entry.value
                    else:
                        # Remove expired entry
                        conn.execute("DELETE FROM cache_entries WHERE key = ?", (cache_key,))
                        conn.commit()
        
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
        
        self._cache_stats["misses"] += 1
        return None
    
    async def set(self, operation: str, params: Dict[str, Any], value: Any,
                  ttl_hours: Optional[int] = None, cost_saved: float = 0.0) -> None:
        """
        Store value in cache for the given operation and parameters.
        
        Args:
            operation: The operation type
            params: Parameters that uniquely identify the operation
            value: Value to cache
            ttl_hours: Time to live in hours (uses default if not specified)
            cost_saved: Estimated cost saved by caching this result
        """
        cache_key = self._generate_cache_key(operation, params)
        ttl = ttl_hours or self.default_ttl_hours
        
        now = datetime.now()
        expires_at = now + timedelta(hours=ttl)
        
        entry = CacheEntry(
            key=cache_key,
            value=value,
            created_at=now,
            expires_at=expires_at,
            hit_count=0,
            cost_saved=cost_saved,
            source=operation
        )
        
        # Store in memory cache
        self._store_in_memory(entry)
        
        # Store in persistent cache
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, value, created_at, expires_at, hit_count, cost_saved, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    cache_key,
                    json.dumps(value),
                    now.isoformat(),
                    expires_at.isoformat(),
                    entry.hit_count,
                    cost_saved,
                    operation
                ))
                conn.commit()
                logger.debug(f"Cached result for {operation}")
        
        except Exception as e:
            logger.error(f"Error storing in cache: {e}")
    
    def _store_in_memory(self, entry: CacheEntry) -> None:
        """Store entry in memory cache with size limit."""
        if len(self._memory_cache) >= self.max_memory_entries:
            # Remove least recently used entry (simple LRU approximation)
            oldest_key = min(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k].hit_count
            )
            del self._memory_cache[oldest_key]
        
        self._memory_cache[entry.key] = entry
    
    def _is_entry_valid(self, entry: CacheEntry) -> bool:
        """Check if cache entry is still valid."""
        if entry.expires_at is None:
            return True
        return datetime.now() < entry.expires_at
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache. Returns number of entries removed."""
        now = datetime.now()
        
        # Clean memory cache
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if not self._is_entry_valid(entry)
        ]
        
        for key in expired_keys:
            del self._memory_cache[key]
        
        # Clean persistent cache
        removed_count = 0
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM cache_entries 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                """, (now.isoformat(),))
                removed_count = cursor.rowcount
                conn.commit()
        
        except Exception as e:
            logger.error(f"Error cleaning up expired cache entries: {e}")
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired cache entries")
        
        return removed_count + len(expired_keys)
    
    async def get_website_cache(self, dealer_name: str, city: str) -> Optional[str]:
        """Get cached website discovery result."""
        params = {"dealer_name": dealer_name, "city": city}
        return await self.get("website_search", params)
    
    async def set_website_cache(self, dealer_name: str, city: str, 
                               website: Optional[str], cost_saved: float = 0.1) -> None:
        """Cache website discovery result."""
        params = {"dealer_name": dealer_name, "city": city}
        await self.set("website_search", params, website, cost_saved=cost_saved)
    
    async def get_ai_content_cache(self, dealer_name: str, city: str,
                                  website: Optional[str], owner_email: Optional[str]) -> Optional[Tuple[str, str, str]]:
        """Get cached AI-generated content."""
        params = {
            "dealer_name": dealer_name,
            "city": city,
            "website": website,
            "owner_email": owner_email
        }
        result = await self.get("ai_content", params)
        if result:
            return tuple(result)  # Convert list back to tuple
        return None
    
    async def set_ai_content_cache(self, dealer_name: str, city: str,
                                  website: Optional[str], owner_email: Optional[str],
                                  content: Tuple[str, str, str], cost_saved: float = 0.05) -> None:
        """Cache AI-generated content."""
        params = {
            "dealer_name": dealer_name,
            "city": city,
            "website": website,
            "owner_email": owner_email
        }
        await self.set("ai_content", params, list(content), cost_saved=cost_saved)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "cost_saved": round(self._cache_stats["cost_saved"], 4),
            "memory_entries": len(self._memory_cache)
        }
    
    async def clear_cache(self, operation: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            operation: If specified, only clear entries for this operation type
            
        Returns:
            Number of entries removed
        """
        removed_count = 0
        
        if operation:
            # Clear specific operation from memory cache
            keys_to_remove = []
            for key, entry in self._memory_cache.items():
                if entry.source == operation:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._memory_cache[key]
            
            # Clear from persistent cache
            try:
                with sqlite3.connect(self.cache_db_path) as conn:
                    cursor = conn.execute("""
                        DELETE FROM cache_entries WHERE source = ?
                    """, (operation,))
                    removed_count = cursor.rowcount
                    conn.commit()
            except Exception as e:
                logger.error(f"Error clearing cache for operation {operation}: {e}")
        else:
            # Clear all cache
            removed_count = len(self._memory_cache)
            self._memory_cache.clear()
            
            try:
                with sqlite3.connect(self.cache_db_path) as conn:
                    cursor = conn.execute("DELETE FROM cache_entries")
                    removed_count += cursor.rowcount
                    conn.commit()
            except Exception as e:
                logger.error(f"Error clearing all cache: {e}")
        
        # Reset stats
        self._cache_stats = {"hits": 0, "misses": 0, "cost_saved": 0.0}
        
        logger.info(f"Cleared {removed_count} cache entries")
        return removed_count


# Global cache instance
_cache_instance: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get the global cache service instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheService()
    return _cache_instance


async def cleanup_cache_task():
    """Background task to clean up expired cache entries."""
    cache_service = get_cache_service()
    while True:
        try:
            await cache_service.cleanup_expired()
            # Run cleanup every hour
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cache cleanup task: {e}")
            await asyncio.sleep(3600)  # Still wait before retry