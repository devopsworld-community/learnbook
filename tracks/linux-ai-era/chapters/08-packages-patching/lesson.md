# Packages and patching without breaking the GPU stack

Unpatched hosts get owned; carelessly patched GPU hosts stop serving. The craft is separating what may update
itself from what needs a person and a window.

## The mental model

- **Security updates unattended**, everything else on a schedule. On Debian/Ubuntu that is
  `unattended-upgrades` with only the `-security` origin; on RHEL-likes, `dnf-automatic` with
  `upgrade_type = security`.
- **Hold what needs a window.** The NVIDIA driver is an out-of-tree kernel module built per kernel. A driver or
  kernel update without a rebuild leaves the GPUs dark after reboot. Hold it (`apt-mark hold`,
  `dnf versionlock`) or blacklist it from unattended upgrades.
- **A patched library protects nothing until the process restarts.** `needrestart` (or
  `dnf needs-restarting`) lists services still mapped to the old files.
- **Packages come from a registry you trust, under names that exist.** An agent's suggested `pip install`
  is a supply-chain decision.

## Do it

```
sudo unattended-upgrade --dry-run --debug | tail -20
apt-mark showhold
sudo apt-mark hold nvidia-driver-570      # until the planned window
sudo needrestart -r l                     # list, do not restart
dkms status                               # is the NVIDIA module built for every installed kernel?
```

## What goes wrong in real teams

Nightly upgrades that pull a new kernel and driver, a reboot at 14:00 in the middle of a training run, and
"we patched openssl" while every daemon still runs the old copy.

## The AI angle

Assistants invent plausible package names, and attackers register those names. Lab 8's `check_package.py`
checks existence, age and release history before anything installs.

## Whose method this is

Debian's `unattended-upgrades` (its default config documents origins and the blacklist) and `needrestart`
are the reference implementations; RHEL's equivalents are `dnf-automatic` and `dnf needs-restarting`.
