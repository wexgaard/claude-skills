# memory-bridge tests

Stdlib `unittest` only — no third-party deps. Run from the repo root:

```
python -m unittest discover -s plugins/memory-bridge/skills/sync/tests -v
```

Coverage:

- `resolve_python_interpreter()` — candidate order, Python-2 rejection, py launcher.
- `post()` — sends a `memory-bridge/<version>` User-Agent.
- `explain_http_failure()` — disambiguates Cloudflare 403s (cf-ray header, `error code: 10xx`, or "cloudflare" in body) from auth 403s.
- `cmd_normal()` — gap-scans `.memory-compiler/daily/`, honours `installed_at`, falls back to a 7-day cap, advances state after each success, stops on first failure.

The tests rebind module-level constants (`DAILY_DIR`, `CONFIG_PATH`, etc.) and the `_today()` / `forward_day()` functions on the imported `sync` module. Each test restores the originals in `tearDown`.
