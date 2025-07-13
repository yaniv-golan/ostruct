"""URL validation utilities for security constraints.

This module provides URL validation to prevent SSRF attacks by blocking
private IP ranges, loopback addresses, and other insecure URLs.
"""

import ipaddress
import socket
from typing import List, Optional
from urllib.parse import urlparse

from .errors import InsecureURLRejected


def validate_url_security(
    url: str,
    strict_mode: bool = True,
    allowed_insecure_urls: Optional[List[str]] = None,
) -> None:
    """Validate URL against security constraints.

    Args:
        url: URL to validate
        strict_mode: Whether to enforce strict security checks
        allowed_insecure_urls: List of explicitly allowed insecure URLs

    Raises:
        InsecureURLRejected: If URL violates security constraints
    """
    if not strict_mode:
        return

    allowed_insecure_urls = allowed_insecure_urls or []

    # Check if URL is explicitly allowed
    if url in allowed_insecure_urls:
        return

    parsed = urlparse(url)

    # Require HTTPS scheme
    if parsed.scheme != "https":
        raise InsecureURLRejected(
            f"URL scheme '{parsed.scheme}' not allowed, must use HTTPS",
            url=url,
            context={
                "reason": "non_https_scheme",
                "scheme": parsed.scheme,
            },
        )

    # Check hostname/IP restrictions
    hostname = parsed.hostname
    if not hostname:
        raise InsecureURLRejected(
            "URL must have a valid hostname",
            url=url,
            context={"reason": "missing_hostname"},
        )

    # Try to resolve hostname to IP address
    try:
        # Get all IP addresses for the hostname
        addr_info = socket.getaddrinfo(
            hostname, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
        )
        ip_addresses = [info[4][0] for info in addr_info]
    except (socket.gaierror, socket.error) as e:
        raise InsecureURLRejected(
            f"Cannot resolve hostname '{hostname}': {e}",
            url=url,
            context={
                "reason": "dns_resolution_failed",
                "hostname": hostname,
                "error": str(e),
            },
        )

    # Check each resolved IP address
    for ip_str in ip_addresses:
        try:
            ip_addr = ipaddress.ip_address(ip_str)
            _validate_ip_address(ip_addr, url, hostname)
        except ValueError as e:
            raise InsecureURLRejected(
                f"Invalid IP address '{ip_str}' for hostname '{hostname}': {e}",
                url=url,
                context={
                    "reason": "invalid_ip_address",
                    "hostname": hostname,
                    "ip_address": ip_str,
                    "error": str(e),
                },
            )


def _validate_ip_address(
    ip_addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
    url: str,
    hostname: str,
) -> None:
    """Validate a single IP address against security constraints.

    Args:
        ip_addr: IP address to validate
        url: Original URL for error context
        hostname: Original hostname for error context

    Raises:
        InsecureURLRejected: If IP address violates security constraints
    """
    # Check for private/internal IP ranges
    if ip_addr.is_private:
        raise InsecureURLRejected(
            f"Private IP address not allowed: {ip_addr} (hostname: {hostname})",
            url=url,
            context={
                "reason": "private_ip_address",
                "ip_address": str(ip_addr),
                "hostname": hostname,
                "ip_type": "private",
            },
        )

    if ip_addr.is_loopback:
        raise InsecureURLRejected(
            f"Loopback IP address not allowed: {ip_addr} (hostname: {hostname})",
            url=url,
            context={
                "reason": "loopback_ip_address",
                "ip_address": str(ip_addr),
                "hostname": hostname,
                "ip_type": "loopback",
            },
        )

    if ip_addr.is_link_local:
        raise InsecureURLRejected(
            f"Link-local IP address not allowed: {ip_addr} (hostname: {hostname})",
            url=url,
            context={
                "reason": "link_local_ip_address",
                "ip_address": str(ip_addr),
                "hostname": hostname,
                "ip_type": "link_local",
            },
        )

    # For IPv6, also check for unique local addresses (ULA)
    if isinstance(ip_addr, ipaddress.IPv6Address):
        # ULA range: fc00::/7 (fc00:: to fdff::)
        if ip_addr in ipaddress.IPv6Network("fc00::/7"):
            raise InsecureURLRejected(
                f"Unique Local Address (ULA) not allowed: {ip_addr} (hostname: {hostname})",
                url=url,
                context={
                    "reason": "ula_ip_address",
                    "ip_address": str(ip_addr),
                    "hostname": hostname,
                    "ip_type": "unique_local",
                },
            )

    # Additional checks for reserved ranges
    if ip_addr.is_reserved:
        raise InsecureURLRejected(
            f"Reserved IP address not allowed: {ip_addr} (hostname: {hostname})",
            url=url,
            context={
                "reason": "reserved_ip_address",
                "ip_address": str(ip_addr),
                "hostname": hostname,
                "ip_type": "reserved",
            },
        )

    if ip_addr.is_multicast:
        raise InsecureURLRejected(
            f"Multicast IP address not allowed: {ip_addr} (hostname: {hostname})",
            url=url,
            context={
                "reason": "multicast_ip_address",
                "ip_address": str(ip_addr),
                "hostname": hostname,
                "ip_type": "multicast",
            },
        )


def is_url_secure(
    url: str,
    strict_mode: bool = True,
    allowed_insecure_urls: Optional[List[str]] = None,
) -> bool:
    """Check if a URL passes security validation.

    Args:
        url: URL to check
        strict_mode: Whether to enforce strict security checks
        allowed_insecure_urls: List of explicitly allowed insecure URLs

    Returns:
        True if URL is secure, False otherwise
    """
    try:
        validate_url_security(url, strict_mode, allowed_insecure_urls)
        return True
    except InsecureURLRejected:
        return False
