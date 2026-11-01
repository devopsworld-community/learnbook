# GPU boxes, then: drivers, DKMS, CUDA and shared notebooks

Before LLM servers there were training boxes: a few GPUs, a driver, CUDA, a shared Jupyter server and maybe
Slurm. They are still running, and most AI incidents on Linux still start in this stack.

## The mental model

- **Kernel module.** The NVIDIA driver is an out-of-tree module. DKMS rebuilds it for each installed kernel;
  Secure Boot refuses it unless it is signed with an enrolled key. The open-source `nouveau` driver must not
  claim the GPU first.
- **Driver versus toolkit.** `nvidia-smi` prints the highest CUDA version the *driver* supports. `nvcc
  --version` prints the *toolkit* you installed. A toolkit at or below the driver's version is fine.
- **Persistence.** On a headless server the driver tears GPU state down when no process holds the device;
  `nvidia-persistenced` keeps it initialized so the first call is not slow.
- **Shared notebooks are remote shells.** A Jupyter kernel runs whatever is typed and can open a terminal.
- **Schedulers use cgroups.** Slurm confines a job to the memory it requested; ask for too little and the
  kernel kills it, however much the node has free.

## Do it

```
nvidia-smi                                 # driver, CUDA (driver-supported), GPUs, processes
cat /proc/driver/nvidia/version            # the loaded module's version
dkms status                                # built for which kernels?
mokutil --sb-state                         # Secure Boot on? then the module must be signed
sudo update-initramfs -u                   # after blacklisting nouveau (dracut --force on RHEL-likes)
ssh -L 8888:localhost:8888 gpu-box         # reach a notebook bound to localhost
sacct -j 1234 --format=JobID,ReqMem,MaxRSS,State   # what a Slurm job asked for and used
```

## What goes wrong in real teams

A kernel update with no module rebuild, a notebook on `0.0.0.0` with the token disabled, and a training job
sized by guess that the scheduler kills at hour six.

## The AI angle

Today's inference servers inherit all of this: same driver, same module, same Secure Boot story. Chapter 10
adds the serving layer on top.

## Whose method this is

NVIDIA's driver installation guide (blacklisting nouveau, DKMS, persistence daemon), SchedMD's Slurm cgroup
documentation, and Project Jupyter's security guidance.
