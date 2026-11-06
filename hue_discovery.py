"""Bounded Hue SSDP discovery fallback, using only Python's standard library."""
import ipaddress
import socket
import time
from urllib.parse import urlsplit


def discover_local_bridges(timeout=1.5):
    """Return advertised private IPv4 Hue bridges, without changing any config.

    Some networks filter multicast or bridges do not advertise SSDP; callers
    must retain the manual address path. No subnet scan is performed.
    """
    found = []
    packet = (b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n'
              b'MAN: "ssdp:discover"\r\nMX: 1\r\nST: ssdp:all\r\n\r\n')
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.sendto(packet, ('239.255.255.250', 1900))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                sock.settimeout(max(.01, deadline - time.monotonic()))
                try:
                    payload, peer = sock.recvfrom(8192)
                except socket.timeout:
                    break
                text = payload.decode('utf-8', errors='replace')
                headers = {}
                for line in text.split('\r\n')[1:]:
                    if ':' in line:
                        name, value = line.split(':', 1)
                        headers[name.strip().lower()] = value.strip()
                if not text.upper().startswith('HTTP/1.1 200'):
                    continue
                # A random UPnP device must never be offered as a Hue bridge.
                if not headers.get('hue-bridgeid') and 'ipbridge' not in headers.get('server', '').lower():
                    continue
                try:
                    location = urlsplit(headers.get('location', ''))
                    if location.scheme not in ('http', 'https'):
                        continue
                    ip = ipaddress.IPv4Address(location.hostname or '')
                except ValueError:
                    continue
                private = any(ip in ipaddress.IPv4Network(net) for net in
                              ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
                if private and str(ip) == peer[0] and str(ip) not in found:
                    found.append(str(ip))
    except (OSError, ValueError):
        # LAN discovery is best-effort on restricted hosts and Raspberry networks.
        pass
    return found
