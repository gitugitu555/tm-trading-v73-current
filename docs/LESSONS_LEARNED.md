# Lessons Learned

This file records the practical conclusions from the work so far.

## Storage

- Seagate HDD is fine as cold storage for archived raw data.
- Keeping compressed archives on HDD is reasonable when the dataset is rarely touched.
- Unzipped hot data on NVMe is the better choice for repeated backtests.
- A symlinked hot path only helps if the target is actually local NVMe; a symlink back to cold storage keeps the I/O penalty.
- For repeated backtests, the hot raw copy and the Parquet catalog both need to live on the fast tier.

## Backtesting

- For this workload, the bottleneck is not just disk access. CPU and parse cost still matter.
- A single sample shard is enough to compare layouts before committing to a full run.
- Benchmarks should be done on the exact dataset shape you plan to use in production research.
- Shard jobs need monitoring because they can die on reboot or leave placeholder outputs behind.

## Dataset Management

- A canonical path layout prevents ad hoc folder drift when adding new pairs or feed types.
- A dataset manager script is more maintainable than hand-built path strings in multiple scripts.
- Cold storage and hot cache should be treated as separate tiers, not competing source-of-truth locations.
- If a Parquet catalog throws a corrupt-footer error, check whether the rebuild was interrupted before assuming the data is bad.

## Downloads

- The downloader defaults should point to cold storage, not the local working tree.
- Existing scripts should still accept overrides for ad hoc experiments.
- Manifest-based downloads are easier to verify and resume than one-off manual fetches.

## GitHub Collaboration

- Never paste API tokens into chat.
- Use SSH or local auth tooling when possible.
- If a token is used, keep it outside the repo and rotate it if it was exposed.

## Repo Hygiene

- Put roadmap, log, and lesson summaries under `docs/` so the repository stays navigable.
- Keep raw data out of git.
- Keep generated result files only when they are useful to reproduce or explain research conclusions.
