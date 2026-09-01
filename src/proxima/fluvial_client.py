import logging
from typing import Annotated
from typing import Any
from typing import Self

from hishel import CacheOptions
from hishel import SpecificationPolicy
from hishel import SyncSqliteStorage
from hishel.httpx import SyncCacheClient
from pydantic import BaseModel
from pydantic import BeforeValidator

logger = logging.getLogger(__name__)

MAX_N_RESULTS = 100
DEFAULT_CACHE_TTL = 60 * 30  # 30min
DEFAULT_CACHE_PATH = ".cache/hishel/fluvial_cache.db"

AVAILABLE_SITES = (
    "torrentproject",  # Supports search only
    "piratebay",  # Supports search, trending (no paging), and recent (no paging)
    # "torlock", # Responds ok, but items have no magnet link
)


def _clean_scraped_string(value: Any) -> Any:
    if isinstance(value, str):
        value = value.replace("\u00a0", " ").replace("N/A", "").strip()
        return value or "0"
    return value


class FluvialItem(BaseModel):
    name: Annotated[str, BeforeValidator(_clean_scraped_string)]
    size: Annotated[str, BeforeValidator(_clean_scraped_string)]
    date: Annotated[str, BeforeValidator(_clean_scraped_string)]
    seeders: Annotated[int, BeforeValidator(_clean_scraped_string)]
    leechers: Annotated[int, BeforeValidator(_clean_scraped_string)]
    url: str
    category: str = ""
    uploader: str = ""
    hash: str = ""
    magnet: str = ""


class FluvialClient:
    def __init__(self, fluvial_api_url: str):
        self.base_url = fluvial_api_url

        self.client = SyncCacheClient(
            storage=SyncSqliteStorage(database_path=DEFAULT_CACHE_PATH, default_ttl=DEFAULT_CACHE_TTL),
            policy=SpecificationPolicy(cache_options=CacheOptions(shared=False, allow_stale=True)),
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
            data = self._get(endpoint, params)

            results.extend(data["data"])
            logger.debug(f"results so far {len(results)}")

        return results[:n_results]

    def search(self, site: str, query: str, n_results: int = 20, sort: bool = True) -> list[FluvialItem]:
        if site not in AVAILABLE_SITES:
            raise ValueError(f"Unknown site: '{site}'.")

        params = {"site": site, "query": query}

        data = self._aggregate_results(endpoint="search", params=params, n_results=n_results)

        parsed = [FluvialItem.model_validate(d) for d in data]

        return sorted(parsed, key=lambda x: x.seeders, reverse=True) if sort else parsed
