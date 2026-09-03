import logging
from typing import Any
from typing import Self

from hishel import AsyncSqliteStorage
from hishel import CacheOptions
from hishel import SpecificationPolicy
from hishel import SyncSqliteStorage
from hishel.httpx import AsyncCacheClient
from hishel.httpx import SyncCacheClient
from httpx import HTTPStatusError

from proxima.data import FluvialItem

logger = logging.getLogger(__name__)

MAX_N_RESULTS = 100
DEFAULT_CACHE_TTL = 60 * 30  # 30min
DEFAULT_CACHE_PATH = ".cache/hishel/fluvial_cache.db"
DEFAULT_CACHE_POLICY = SpecificationPolicy(cache_options=CacheOptions(shared=False))

AVAILABLE_SITES = (
    "torrentproject",  # Supports search only
    "piratebay",  # Supports search, trending (no paging), and recent (no paging)
    # "torlock", # Responds ok, but items have no magnet link
)


class FluvialClient:
    def __init__(self, fluvial_api_url: str, cache_storage_path: str = DEFAULT_CACHE_PATH):
        self.base_url = f"{fluvial_api_url}/api/v1/"

        self.client = SyncCacheClient(
            storage=SyncSqliteStorage(database_path=cache_storage_path, default_ttl=DEFAULT_CACHE_TTL),
            policy=DEFAULT_CACHE_POLICY,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_details: object) -> None:
        self.client.close()

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self.client.get(
            url=f"{self.base_url}{endpoint}",
            params=params,
            extensions=extensions,
            timeout=10,
        )
        logger.debug(f"url endpoint '{endpoint}'")
        logger.debug(f"status_code: {response.status_code}")
        logger.debug(f"request params: {params}")
        logger.debug(f"response extensions {response.extensions}")
        logger.debug(f"response headers {response.headers}")

        response.raise_for_status()
        return response.json()

    def _aggregate_results(self, endpoint: str, params: dict[str, Any], n_results: int) -> list[dict[str, Any]]:
        if n_results > MAX_N_RESULTS:
            logger.warning(
                f"Max number of results queried at once is {MAX_N_RESULTS}. Capped query to {MAX_N_RESULTS}.",
            )
            n_results = MAX_N_RESULTS

        results: list[dict[str, Any]] = []
        page = 0
        while len(results) < n_results:
            page += 1
            params["page"] = page
            logger.debug(f"querying page {page}")

            try:
                data = self._get(endpoint, params)
                results.extend(data["data"])
            except HTTPStatusError as e:
                if e.response.status_code == 404 or e.response.status_code == 403:
                    logger.debug(f"page {page} not found: status code {e.response.status_code}")
                    break
                raise

            logger.debug(f"results so far {len(results)}")

        return results[:n_results]

    def search(self, site: str, query: str, n_results: int = 20, sort: bool = True) -> list[FluvialItem]:
        if site not in AVAILABLE_SITES:
            raise ValueError(f"Unknown site: '{site}'.")

        params = {"site": site, "query": query}

        data = self._aggregate_results(endpoint="search", params=params, n_results=n_results)

        parsed = [FluvialItem.model_validate(d) for d in data]

        return sorted(parsed, key=lambda x: x.seeders, reverse=True) if sort else parsed


class AsyncFluvialClient:
    def __init__(self, fluvial_api_url: str, cache_storage_path: str = DEFAULT_CACHE_PATH):
        self.base_url = f"{fluvial_api_url}/api/v1/"

        self.client = AsyncCacheClient(
            storage=AsyncSqliteStorage(database_path=cache_storage_path, default_ttl=DEFAULT_CACHE_TTL),
            policy=DEFAULT_CACHE_POLICY,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_details: object) -> None:
        await self.client.aclose()

    async def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self.client.get(
            url=f"{self.base_url}{endpoint}",
            params=params,
            extensions=extensions,
            timeout=10,
        )
        logger.debug(f"url endpoint '{endpoint}'")
        logger.debug(f"status_code: {response.status_code}")
        logger.debug(f"request params: {params}")
        logger.debug(f"response extensions {response.extensions}")
        logger.debug(f"response headers {response.headers}")

        response.raise_for_status()
        return response.json()

    async def _aggregate_results(self, endpoint: str, params: dict[str, Any], n_results: int) -> list[dict[str, Any]]:
        if n_results > MAX_N_RESULTS:
            logger.warning(
                f"Max number of results queried at once is {MAX_N_RESULTS}. Capped query to {MAX_N_RESULTS}.",
            )
            n_results = MAX_N_RESULTS

        results: list[dict[str, Any]] = []
        page = 0
        while len(results) < n_results:
            page += 1
            params["page"] = page
            logger.debug(f"querying page {page}")

            try:
                data = await self._get(endpoint, params)
                results.extend(data["data"])
            except HTTPStatusError as e:
                if e.response.status_code == 404 or e.response.status_code == 403:
                    logger.debug(f"page {page} not found: status code {e.response.status_code}")
                    break
                raise

            logger.debug(f"results so far {len(results)}")

        return results[:n_results]

    async def search(self, site: str, query: str, n_results: int = 20, sort: bool = True) -> list[FluvialItem]:
        if site not in AVAILABLE_SITES:
            raise ValueError(f"Unknown site: '{site}'.")

        params = {"site": site, "query": query}

        data = await self._aggregate_results(endpoint="search", params=params, n_results=n_results)

        parsed = [FluvialItem.model_validate(d) for d in data]

        return sorted(parsed, key=lambda x: x.seeders, reverse=True) if sort else parsed
