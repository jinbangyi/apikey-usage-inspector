from urllib.parse import urlencode, urlparse, urlunparse

import aiohttp

from src.settings import settings


def resolve_url(url: str) -> str:
    """
    Replace the hostname in the URL with its mapped IP address if it exists in DNS_MAP.

    Args:
        url: Original URL

    Returns:
        Modified URL with resolved IP address
    """
    parsed = urlparse(url)
    hostname = parsed.hostname

    if hostname is None:  # Local file or invalid URL
        return url

    if hostname in settings.dns_map:
        ip = settings.dns_map[hostname]
        # Replace hostname with IP in netloc
        if parsed.port:
            new_netloc = f"{ip}:{parsed.port}"
        else:
            new_netloc = ip

        # Reconstruct the URL
        parts = list(parsed)
        parts[1] = new_netloc  # Replace netloc
        return urlunparse(parts)

    return url


async def async_request(method: str, url: str, **kwargs) -> aiohttp.ClientResponse:
    """
    Make an async request with custom DNS resolution using aiohttp.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: URL to request
        **kwargs: Additional arguments passed to aiohttp client session request

    Returns:
        aiohttp.ClientResponse object
    """
    # Parse the original URL to get the hostname
    parsed = urlparse(url)
    hostname = parsed.hostname

    if hostname is not None and hostname in settings.dns_map:
        # Resolve the URL
        resolved_url = resolve_url(url)

        # Ensure we have headers
        if "headers" not in kwargs:
            kwargs["headers"] = {}

        # Set Host header to original hostname
        kwargs["headers"]["Host"] = hostname

        url = resolved_url

    if settings.flaresolver_enabled:
        url = settings.flaresolver_endpoint
        kwargs["headers"] = {"Content-Type": "application/json"}
        data = {"cmd": f"request.{method.lower()}", "url": url, "maxTimeout": 60000}
        if settings.flaresolver_proxy:
            data["proxy"] = {"url": settings.flaresolver_proxy}

        if method == "POST" and "data" in kwargs:
            postData = kwargs.pop("data", {})
        elif method == "POST" and "json" in kwargs:
            postData = kwargs.pop("json", {})
        else:
            postData = {}
        if postData:
            if isinstance(postData, dict):
                postData = urlencode(postData)
            elif isinstance(postData, str):
                postData = postData
            else:
                raise ValueError("postData must be a dict or str")
            data["postData"] = postData

        kwargs["json"] = data

    # Make regular request if no resolution needed
    async with aiohttp.ClientSession() as session:
        return await session.request(method, url, **kwargs)


async def async_get(url: str, params=None, **kwargs) -> aiohttp.ClientResponse:
    """Make an async GET request with custom DNS resolution."""
    if params:
        kwargs["params"] = params
    return await async_request("GET", url, **kwargs)


async def async_post(
    url: str, data=None, json=None, **kwargs
) -> aiohttp.ClientResponse:
    """Make an async POST request with custom DNS resolution."""
    if data is not None:
        kwargs["data"] = data
    if json is not None:
        kwargs["json"] = json
    return await async_request("POST", url, **kwargs)


async def async_put(url: str, data=None, **kwargs) -> aiohttp.ClientResponse:
    """Make an async PUT request with custom DNS resolution."""
    if data is not None:
        kwargs["data"] = data
    return await async_request("PUT", url, **kwargs)


async def async_delete(url: str, **kwargs) -> aiohttp.ClientResponse:
    """Make an async DELETE request with custom DNS resolution."""
    return await async_request("DELETE", url, **kwargs)
