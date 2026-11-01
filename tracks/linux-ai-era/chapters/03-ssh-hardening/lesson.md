# Users, groups and SSH hardening

SSH is the front door of every Linux box you will run. Hardening it is a short list, and the dangerous part
is not the list but applying it to a server you can only reach through that door.

## The mental model

- Authentication: keys (`ssh-keygen -t ed25519`), not passwords. Turn off both `PasswordAuthentication`
  and `KbdInteractiveAuthentication`, or PAM can still ask for a password.
- Authorization: no direct root (`PermitRootLogin no`), and an explicit `AllowGroups` so a new local user
  is not an SSH user by accident.
- Precedence: for most keywords sshd keeps the **first** value it reads. Debian and Ubuntu include
  `/etc/ssh/sshd_config.d/*.conf` at the top of `sshd_config`, so a drop-in beats a line at the bottom.

## Do it

```
sudo sshd -t                                   # syntax check, prints nothing when fine
sudo sshd -T | grep -Ei 'permitroot|passwordauth|kbdinteractive|allowgroups'   # what is in effect
sudo systemctl reload ssh                      # Debian/Ubuntu unit name; sshd on RHEL-likes
ssh -o PreferredAuthentications=password you@host   # from a second terminal: must be refused
ssh-audit host                                 # algorithms and key exchange, scored
```

Keep your current session open until a fresh login works from a second terminal.

## What goes wrong in real teams

A cloud image ships `50-cloud-init.conf` with `PasswordAuthentication yes` and silently wins over your edit;
a restart instead of a reload after a typo; a shared deploy key nobody can rotate.

## The AI angle

Never hand an agent your SSH key. Lab 5 gives it a one-hour lab key behind a tool that only runs read-only
commands and logs every call, and the sandbox denies `~/.ssh` outright.

## Whose method this is

Mozilla's OpenSSH guidelines make the same calls as this chapter's exercise; `sshd_config(5)` documents the
first-value-wins rule; `ssh-audit` checks the cryptography side.
