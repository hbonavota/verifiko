from typing import Any


def build_redis_client(redis_url: str) -> Any:
    try:
        import redis
    except (
        ImportError
    ) as exc:  # pragma: no cover - exercised only when Redis is configured without deps
        raise RuntimeError(
            "REDIS_URL is configured but the redis package is not installed."
        ) from exc

    return redis.Redis.from_url(redis_url, decode_responses=True)
