#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
if [[ ! -d "$repo_root/.git" ]]; then
  echo "could not find the tm-trading-v555 git repo from $script_dir" >&2
  exit 2
fi

cd "$repo_root"

git config --local core.sharedRepository group
git config --local push.default simple
git config --local user.name "${GIT_USER_NAME:-${USER:-tokio}}"
git config --local user.email "${GIT_USER_EMAIL:-${USER:-tokio}@sam-x99}"

echo "configured local git identity"
echo "  user.name=$(git config --local --get user.name)"
echo "  user.email=$(git config --local --get user.email)"
echo "  remote=$(git remote get-url origin)"

if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    echo "gh auth: available for the current user"
  else
    echo "gh auth: not configured for the current user"
    echo "        run 'gh auth login' or use an SSH key for pushes"
  fi
fi
