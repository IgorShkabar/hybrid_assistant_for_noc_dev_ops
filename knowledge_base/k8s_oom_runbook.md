# Runbook: Kubernetes OOMKilled (Out Of Memory)
## Symptoms
Pod crashes with `Exit Code 137` or `OOMKilled` in container status.
## Root Cause
Container exceeded its memory limit defined in Kubernetes deployment manifest.
## Diagnostics (Read-Only)
1. Check pod events and memory limits: `kubectl describe pod <pod-name> -n prod`
2. Check current node memory pressure: `kubectl top pods -n prod`
