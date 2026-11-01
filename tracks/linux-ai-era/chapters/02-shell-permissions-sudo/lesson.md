# The shell, permissions and sudo

The shell is your control plane: everything else in this track is typed into it. The two things that
decide whether a typed command works are file permissions and sudo, and both fail in quiet, specific ways.

## The mental model

- Mode bits are read as owner, group, other. The kernel picks the **first** class that matches you and
  applies only that one: an owner with `0466` cannot write, even though the group can.
- Opening `/a/b/c` needs execute (search) permission on `/`, `/a` and `/a/b`, plus the right bit on `c`.
  That is why a file with perfect permissions can still be unreadable.
- sudo is a policy, not a password prompt. Good policy names the user, the target user, and the exact
  command by full path. `NOPASSWD: ALL` is root with extra steps.

## Do it

```
namei -l /srv/app/logs/app.log     # owner and mode of every path component, top to bottom
stat -c '%A %U:%G %n' /srv/app      # one line per file
find / -xdev -type f -perm -0002    # world-writable files on this filesystem
getfacl /srv/app                    # ACLs, which ls only hints at with a +
sudo -l                             # what sudo will let *you* run
sudo visudo -c -f /etc/sudoers.d/deploy   # check a sudoers file before it can lock you out
```

## What goes wrong in real teams

`chmod -R 777` to make an error go away, a sudoers file edited without visudo that breaks sudo for
everyone, and a deploy user with full root because "it needs to restart one service".

## The AI angle

An agent will happily propose `chmod -R 777` or `sudo` for everything; the error goes away and the hole
stays. The skill you keep is finding the one missing bit, which is exactly what you check in its output.

## Whose method this is

The *UNIX and Linux System Administration Handbook* (Nemeth, Snyder, Hein, Whaley, Mackin) treats sudo as
least-privilege policy with logging. Julia Evans' zines are the fastest way to rebuild the model in your head.
