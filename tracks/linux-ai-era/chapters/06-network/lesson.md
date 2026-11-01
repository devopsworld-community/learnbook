# Networking from the box

Most network tickets are answered from the box itself in four questions: what is listening, can the other
side reach it, what does name resolution return, and what actually crosses the wire.

## The mental model

- **Listening** is a socket bound to an address. `127.0.0.1` is this host only; `0.0.0.0` is every
  interface. A model server on `0.0.0.0` with no firewall is a public API.
- **Reachability** is routing plus the firewall. nftables evaluates the `input` chain; with `policy drop`,
  anything not accepted explicitly is dropped.
- **Resolution** goes through the system resolver (glibc, NSS, systemd-resolved). `dig @server` bypasses it,
  so "dig works, curl does not" means the resolver configuration differs, not the record.
- **The wire** does not lie. `tcpdump -ni any port 11434` settles arguments.

## Do it

```
ip -br a; ip r                      # addresses and routes, briefly
sudo ss -ltnp                       # listening TCP sockets with the owning process
resolvectl status                   # which DNS servers this host really asks
dig +short api.internal; dig @10.0.0.2 api.internal
curl -sv https://api.internal/ -o /dev/null   # DNS, TCP, TLS and HTTP in one trace
sudo tcpdump -ni any port 11434     # what crosses the wire, no name lookups
sudo nft list ruleset               # the live firewall
sudo nft -c -f /etc/sysconfig/nftables.conf   # validate a ruleset file without applying it
```

## Changing a firewall remotely

Edit the persisted file, validate it with `nft -c -f`, schedule a rollback (for example
`sudo systemd-run --on-active=5min nft -f /root/nftables.good`), apply with `nft -f` (one atomic
transaction), prove a fresh SSH login from a second terminal, then cancel the rollback timer.

## What goes wrong in real teams

`nft flush ruleset` over SSH, a typo that turns port 22 into port 2 and only bites after the next reboot,
and an inference port opened "temporarily" for a demo.

## The AI angle

Ollama, vLLM and llama.cpp servers all accept requests from anyone who can reach them. Bind them to
localhost, keep their port out of the firewall, and put an authenticated gateway in front when others need them.

## Whose method this is

W. Richard Stevens' *TCP/IP Illustrated* is still the model of what is on the wire; Julia Evans' networking
zines are the quickest refresher for `dig`, `tcpdump` and friends.
