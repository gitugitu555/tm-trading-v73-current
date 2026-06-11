# Pressure-Confirmed Profile Exits

Profile exits remain shadow-only. The cached runner now supports `--profile-exit-require-cvd-confirm` and `--profile-exit-require-pressure-confirm`; the latter uses the available MLOFI weighted aggregate as pressure confirmation.

Raw, CVD-confirmed, and pressure-confirmed shadow fields can be compared with `scripts/v86_shadow_pressure_exit_report.py`.
