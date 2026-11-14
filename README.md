# status

Uptime checks for useland.dev, shown at https://useland.dev/status.

Every 5 minutes a GitHub Actions job (outside land's own machines) checks each monitor in `monitors.json` once and
appends the result to `data/history/<id>.csv` on the `data` branch; `data/summary.json` is rebuilt from the whole
history. A failed check is retried once after 20 s before it counts as down. Nothing is backfilled: history starts
with the first check. GitHub's scheduler can delay or skip runs, so gaps in the data are gaps in checking, not outages.
