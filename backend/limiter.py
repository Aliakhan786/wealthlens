from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import get_settings

# Uses Redis as shared storage when configured so limits hold across multiple API instances.
_settings = get_settings()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_settings.rate_limit],
    storage_uri=_settings.redis_url or "memory://",
)
