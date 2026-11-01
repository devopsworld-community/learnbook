# systemd, cgroup v2 and resource control

Every long-running thing on a modern Linux box is a systemd unit, and every unit runs in its own cgroup.
That is the lever you pull when a model server, kind and an agent share one machine.

## The mental model

- A unit file is declarative: what to run, as whom, when to restart, what it may touch. `systemctl cat`
  shows the merged result of the vendor file plus every drop-in.
- Vendor units live in `/usr/lib/systemd/system` and are replaced on upgrade. Your changes go in
  `/etc/systemd/system/<unit>.d/*.conf` (`systemctl edit <unit>` writes one for you).
- cgroup v2 resource control: `MemoryHigh` throttles and reclaims, `MemoryMax` is the hard cap where the
  OOM killer acts, `CPUWeight` decides who gets the CPU under contention.
- Sandboxing options (`NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`, `DynamicUser`) cost a few
  lines and remove whole classes of damage. `systemd-analyze security` scores what is left.

## Do it

```
stat -fc %T /sys/fs/cgroup          # cgroup2fs on a correct host
systemctl status metrics-collector  # state, last log lines, the cgroup it runs in
systemctl cat metrics-collector     # vendor unit plus drop-ins, as systemd sees it
sudo systemctl edit metrics-collector   # opens a drop-in; daemon-reload happens on save
journalctl -b -u metrics-collector  # this boot's logs for one unit
systemd-cgtop                       # live memory and CPU per cgroup
systemd-analyze security model-api.service   # exposure score, lower is better
```

## What goes wrong in real teams

Editing the vendor unit and losing it on the next upgrade, "fixing" an OOM loop by removing the memory limit,
and running a network-facing service as root because that is what the README did.

## The AI angle

Model servers are memory-hungry network services. The pattern you learn here (a drop-in with MemoryHigh
below MemoryMax, localhost bind, a dynamic user) is exactly how Part 2 runs Ollama next to everything else.

## Whose method this is

Lennart Poettering's systemd design: declarative units, cgroups per service, sandboxing as configuration.
The man pages `systemd.exec(5)` and `systemd.resource-control(5)` are the reference for every key here.
