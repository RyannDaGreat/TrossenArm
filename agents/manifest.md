# Goal

Connect this Mac to four Trossen robot arms through its USB-C Ethernet adapter and a network device. First verify that all four addresses respond, then report to the user. This stage does not permit motor activation or movement. Keep experimental work in `agents/.scratchpad/` until the user requests a top-level implementation.

# Glossary

- Dump: a portable Git project that must not depend on its absolute location.
- Leader: the arm intended to supply operator input.
- Follower: the arm intended to follow that input.
- Connectivity: network reachability; it does not prove motion control is ready.
- Subnet: the group of local IP addresses that can communicate directly.
- Glossary: definitions of project-specific terms.

# User requirements and transcript

Full received text is in `agents/transcript.md`, including the repeated initial request. The user uses voice dictation. Interpret clear typos in context; do not treat dictation noise as extra requirements.

- Initialize this dump and establish connectivity first.
- USB-C connects through an Ethernet adapter and an unspecified network device to the arms.
- Address mapping from box labels:

| Arm | Address |
| --- | --- |
| Leader right | 192.168.1.2 |
| Follower right | 192.168.1.4 |
| Leader left | 192.168.1.3 |
| Follower left | 192.168.1.5 |

- Keep transcripts and this manifest current.
- Report once this stage is complete. Do not speak aloud during setup.

# Approach and constraints

Use native macOS network tools first. Inspect the adapter and routes, add a host address on the robot subnet if needed, then test each labeled address. Preserve Wi-Fi and VPN settings. Do not issue robot control commands, enable torque, or run vendor motion examples. A successful ping proves IP reachability, not identity or safe control readiness. Record exact results and any limitations.

# Verified network setup

On 2026-10-28, all four labeled addresses responded to three pings each, with 0% packet loss. Routes and ARP entries confirm access through USB Ethernet `en9`, not the VPN. The link is 1000baseT full-duplex. Evidence: `agents/.scratchpad/logs/connectivity.log`.

| Arm | Address | MAC address | Mean ping latency |
| --- | --- | --- | --- |
| Leader right | 192.168.1.2 | 04:e9:e5:1a:5f:78 | 1.858 ms |
| Follower right | 192.168.1.4 | 04:e9:e5:1a:5e:5f | 0.862 ms |
| Leader left | 192.168.1.3 | 04:e9:e5:18:11:da | 1.023 ms |
| Follower left | 192.168.1.5 | 04:e9:e5:1a:5e:8b | 1.187 ms |

The Mac's `USB 10/100/1000 LAN` service now has a persistent manual address `192.168.1.100/24`, with no router. Wi-Fi and VPN settings were not changed. Names and addresses in this paragraph describe this machine; rediscover the correct adapter on another machine.

Reproduce on this Mac:

```sh
networksetup -setmanual 'USB 10/100/1000 LAN' 192.168.1.100 255.255.255.0
```

Restore its original DHCP configuration when no longer using the robot network:

```sh
networksetup -setdhcp 'USB 10/100/1000 LAN'
```

Only network reachability is verified. Arm names follow the user's box labels; no vendor protocol, model identity, motor activation, or movement was tested.

# Files

- `AGENTS.md`: project instructions and safety boundary.
- `agents/todo.md`: current work checklist.
- `agents/transcript.md`: user messages.
- `agents/manifest.md`: current goal, requirements, design, and results.
- `agents/concerns.md`: append-only progress, mistakes, and risks.
- `agents/.scratchpad/`: experiments and results; logs go in its `logs/` folder.

# Code and verification

Use small, clear functions and explicit errors. Document function classification, inputs, outputs, and examples if code is needed. Avoid dependencies unless they simplify the task. All paths in project files must be relative to the Git root.

Success for this stage: all four labeled addresses respond over USB Ethernet. Record ping results and route/interface evidence. Protocol identification and robot control remain separate work.

# Semantic Bindings

None.
