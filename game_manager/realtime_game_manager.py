# -*- coding: utf-8 -*-
from abc import abstractmethod
import asyncio
from .base import GameManager
from .ttl_cache_manager import TTLConfig, TTLCacheManager, DataType
from dataclasses import dataclass
from typing import Dict, List, Optional
import aiohttp
import logging

@dataclass
class RealtimeConfig:
    max_concurrent_requests: int = 10
    request_timeout: int = 30
    rate_limit_delay: float = 0.1
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_request_logging: bool = False

class RealtimeGameManager(GameManager):
    def __init__(self, api_key: str, cache_dir: str, **kwargs):
        super().__init__(api_key, cache_dir)
        self.realtime_config = kwargs.get("realtime_config", RealtimeConfig())
        self._session = kwargs.get("global_session")
        self._owns_session = self._session is None
        self._semaphore = asyncio.Semaphore(self.realtime_config.max_concurrent_requests)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            if self._owns_session:
                timeout = aiohttp.ClientTimeout(total=self.realtime_config.request_timeout)
                self._session = aiohttp.ClientSession(timeout=timeout)

    async def _close_session(self):
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()

    async def _http_get_async(self, url: str, params: Dict) -> Dict:
        await self._ensure_session()
        headers = self._prepare_headers({})
        async with self._semaphore:
            for attempt in range(self.realtime_config.retry_attempts):
                try:
                    async with self._session.get(url, headers=headers, params=params) as response:
                        response.raise_for_status()
                        return await response.json()
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    if attempt >= self.realtime_config.retry_attempts - 1:
                        raise e
                    await asyncio.sleep(self.realtime_config.retry_delay * (2 ** attempt))
        return {}

    @abstractmethod
    async def _fetch_games_async(self, date, **kwargs) -> List[Dict]:
        pass

    @abstractmethod
    async def _fetch_odds_async(self, game_id: str, **kwargs) -> Optional[Dict]:
        pass

    async def get_games_realtime(self, date, **kwargs) -> List[Dict]:
        return await self._fetch_games_async(date, **kwargs)

    async def get_odds_realtime(self, game_id: str, **kwargs) -> Optional[Dict]:
        return await self._fetch_odds_async(game_id, **kwargs)
