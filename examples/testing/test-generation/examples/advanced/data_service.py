import asyncio
from datetime import datetime
from typing import Any, Dict, Optional


class DataService:
    """Async data service demonstrating complex testing scenarios."""

    def __init__(self, cache_timeout: int = 60):
        self._cache: Dict[str, Any] = {}
        self._cache_times: Dict[str, datetime] = {}
        self.cache_timeout = cache_timeout

    async def get_data(self, key: str) -> Optional[Any]:
        """Get data from cache or fetch if needed."""
        # Check cache
        if key in self._cache:
            cache_time = self._cache_times[key]
            if (datetime.utcnow() - cache_time).seconds < self.cache_timeout:
                return self._cache[key]

        # Simulate async data fetch
        await asyncio.sleep(1)  # Simulated external API call
        data = await self._fetch_data(key)

        # Update cache
        if data is not None:
            self._cache[key] = data
            self._cache_times[key] = datetime.utcnow()

        return data

    async def _fetch_data(self, key: str) -> Optional[Any]:
        """Simulate fetching data from external source."""
        # Simulate some async processing
        await asyncio.sleep(0.5)
        return {
            "key": key,
            "value": f"data_{key}",
            "timestamp": datetime.utcnow(),
        }
