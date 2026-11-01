# Inference servers, now: Ollama, vLLM and llama.cpp as hardened services

The current generation of AI on Linux is a long-running server that holds a model in GPU memory and answers
HTTP. Everything from Part 1 applies, with bigger numbers.

## The mental model

- **Bind localhost.** Ollama listens where `OLLAMA_HOST` says; vLLM and llama.cpp take `--host`. Other
  users reach it through an authenticated gateway, not a firewall hole.
- **A ceiling that throttles before it kills.** `MemoryHigh` below `MemoryMax` in a drop-in, so the model is
  what slows down when kind and the agent need memory, not kubelet.
- **A sandbox with one door to the GPU.** `ProtectSystem=strict` plus `ReadWritePaths` for the model store,
  `DevicePolicy=closed` plus `DeviceAllow` for the NVIDIA device nodes.
- **Containers need the toolkit.** `docker run --gpus all` works only once the NVIDIA Container Toolkit is
  installed and configured for the runtime.
- **Pre-allocation is normal.** vLLM reserves about 90% of GPU memory up front for its KV cache
  (`--gpu-memory-utilization`, default 0.9).

## Do it

```
sudo systemctl edit ollama                 # the drop-in from this chapter's exercise
systemctl show ollama -p MemoryHigh -p MemoryMax
ss -ltnp | grep 11434                      # must show 127.0.0.1
systemd-analyze security ollama.service    # the setup script aims for < 5.0
nvtop                                      # GPU utilization and memory per process
nvidia-smi -q -d PERFORMANCE               # why clocks are throttled, if they are
sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
```

## What goes wrong in real teams

`OLLAMA_HOST=0.0.0.0` copied from a blog post, a model server killed by the OOM killer because nothing
throttled it first, and `--privileged` used to make a GPU container work.

## The AI angle

This chapter is where Part 1 pays off: the drop-in, the bind address, the cgroup ceiling and the sandbox are
exactly what `setup/01-ollama-systemd.sh` writes before the labs in Part 3 run an agent against the model.

## Whose method this is

The projects' own docs (Ollama's environment variables, vLLM's engine arguments, llama.cpp's server options,
NVIDIA's Container Toolkit guide) plus systemd's sandboxing options from chapter 4.
