# Progress and concerns

## 2026-10-28 19:52 - Initial setup

- The directory was empty and not a Git repository. Initialized Git and created project instructions, a checklist, a transcript, and a manifest.
- The USB Ethernet device `en9` has an active 1 Gbit/s link but only a self-assigned IPv4 address (`169.254.31.103`). No robot-subnet route exists. This explains why direct local access is not yet configured.
- Attempted a temporary `192.168.1.100/24` alias with `sudo -n /sbin/ifconfig en9 alias 192.168.1.100 netmask 255.255.255.0`. It failed: `sudo: a password is required`. No alias was added.
- Next check: whether macOS permits the current administrator to configure the network service using `networksetup`. Preserve the original DHCP configuration so it can be restored.
- Robot identity and protocol are not verified. Do not infer motion readiness from network reachability.

## 2026-10-28 19:53 - Connectivity verified

- `networksetup -setmanual 'USB 10/100/1000 LAN' 192.168.1.100 255.255.255.0` succeeded without sudo. This persistently changes only the USB Ethernet service from DHCP to a static address with no router. Restore with `networksetup -setdhcp 'USB 10/100/1000 LAN'`.
- An immediate route query still showed the VPN default while the network change applied. The later verification confirmed all four routes use `en9`. Lesson: verify applied interface state and routes, not only saved service settings.
- All four IPs returned 3/3 pings, 0% loss, and distinct ARP MAC addresses. Mean latencies: `.2` 1.858 ms, `.4` 0.862 ms, `.3` 1.023 ms, `.5` 1.187 ms.
- Full interface, route, ping, and ARP output is in `agents/.scratchpad/logs/connectivity.log`.
- No robot commands were sent. No motor or motion checks were performed. Wi-Fi and VPN settings were left unchanged.
