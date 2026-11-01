# Disks, logs and the 3 am disk-full drill

"No space left on device" stops databases, package managers and the journal at once. The drill is always the
same: which filesystem, which kind of full, which directory, which process.

## The mental model

- **Blocks or inodes.** `df -h` for space, `df -i` for inodes. Millions of tiny files run out of inodes first.
- **Deleted but open.** Removing a file only removes its name. The space comes back when the last process
  holding it closes it. `df` sees it, `du` does not.
- **Logs grow until something rotates them.** journald has size caps; plain files need logrotate, and
  logrotate has to be able to create a file the app can still write.
- **Separate volumes for things that grow.** Model stores, container images and databases do not belong on
  the same filesystem as `/var/log`. LVM lets you grow a volume online: `lvextend -r` grows the filesystem too.

## Do it

```
df -h; df -i                              # which filesystem, which kind of full
sudo du -xh --max-depth=2 /var | sort -h | tail   # where, without crossing mounts
sudo ncdu -x /var                         # the same, interactively
sudo lsof +L1                             # deleted files still held open
journalctl --disk-usage; sudo journalctl --vacuum-size=1G
sudo logrotate -d /etc/logrotate.d/chatty # dry run: what would happen, and why not
sudo lvextend -r -L +50G vg0/var          # grow the LV and its filesystem, online
```

## What goes wrong in real teams

`rm` on a 40 GB log that a process still holds (nothing is freed), a logrotate rule that creates the new
file as root so the app silently stops logging, and a model pull that fills `/var` and takes the journal and
the package manager down with it.

## The AI angle

A single open-weight model is 10 to 50 GB, and every tool keeps its own cache (`OLLAMA_MODELS`, `HF_HOME`).
Give them their own volume and remove models with the tool's own command, never by deleting blobs.

## Whose method this is

Limoncelli, Hogan and Chalup's *Practice of System and Network Administration* argues for monitoring capacity
before it pages you; this chapter is the page you get when nobody did.
