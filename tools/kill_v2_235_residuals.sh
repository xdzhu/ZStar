#!/usr/bin/env bash
set -u
for pid in $(ps -u "${USER}" -o pid=); do
    cwd=$(readlink "/proc/$pid/cwd" 2>/dev/null || true)
    case "$cwd" in
        /home/zhuxd/abacus/agent-runs/20260913-v2-piezo-candidates/zno/strain-002-*) kill -KILL "$pid" 2>/dev/null || true ;;
        /home/zhuxd/abacus/agent-runs/20260914-v2-refrelax-zno*) kill -KILL "$pid" 2>/dev/null || true ;;
    esac
done
