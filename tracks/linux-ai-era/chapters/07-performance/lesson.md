# Performance triage: 60 seconds and the USE method

"The box is slow" is not a diagnosis. Brendan Gregg's answer is a fixed first minute and a fixed question
for every resource, so you collect evidence before you form a theory.

## The first 60 seconds

```
uptime                 # load averages: rising, falling, or flat?
dmesg -T | tail        # OOM kills, I/O errors, driver complaints
vmstat 1               # r (run queue), free memory, si/so (swap), us/sy/id/wa
mpstat -P ALL 1        # one hot CPU while the others idle?
pidstat 1              # which processes use the CPU
iostat -xz 1           # per-disk r/s, w/s, await, aqu-sz, %util
free -m                # 'available' is the number that matters
sar -n DEV 1           # network throughput per interface
sar -n TCP,ETCP 1      # connections per second, retransmits
top                    # a last look at everything together
```

The exercise turns this list into `triage.sh`, which is the cheat sheet you keep.

## The USE method

For every resource (CPUs, memory, disks, network interfaces, and now GPUs), ask for **U**tilization,
**S**aturation and **E**rrors. Saturation is the one people skip: a run queue longer than the CPU count,
swapping, a disk queue, or a stall in `/proc/pressure/*` (PSI).

## Traps

- Linux load averages count tasks waiting on disk (D state) as well as runnable ones.
- `%util` near 100 on NVMe or RAID only means "busy at some point each interval"; look at await and queue size.
- Short-lived processes never show in `top`; `execsnoop` (bcc or bpftrace) catches them.

## The AI angle

Paste triage output into a model and it will give you a confident story. Check each claim against the metric
that actually measures it; the classic misreadings above are exactly what it will repeat.

## Whose method this is

Brendan Gregg: *Linux Performance Analysis in 60,000 Milliseconds* (Netflix Tech Blog, 2015), the USE
Method, *Systems Performance* (2nd ed., 2020) and *BPF Performance Tools* (2019).
