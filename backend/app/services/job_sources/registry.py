from app.services.job_sources.base import JobSourceAdapter
from app.services.job_sources.bytedance import UnsupportedJobSourceUrlError


class JobSourceRegistry:
    def __init__(self, adapters: list[JobSourceAdapter]):
        self.adapters = adapters

    def for_url(self, search_url: str) -> JobSourceAdapter:
        for adapter in self.adapters:
            if adapter.supports(search_url):
                return adapter
        raise UnsupportedJobSourceUrlError()

    def for_query(self, provider: str) -> JobSourceAdapter:
        for adapter in self.adapters:
            if getattr(adapter, "provider", adapter.source) == provider:
                return adapter
        raise UnsupportedJobSourceUrlError(f"Unsupported source provider: {provider}")

    def close(self) -> None:
        for adapter in self.adapters:
            close = getattr(adapter, "close", None)
            if callable(close):
                close()
