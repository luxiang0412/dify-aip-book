#!/usr/bin/env bash
# Build the VitePress site and publish it to the gh-pages branch.
# GitHub Pages serves https://luxiang0412.github.io/dify-aip-book/ from that branch.
set -euo pipefail
cd "$(dirname "$0")/.."
npm run build
cd .vitepress/dist
touch .nojekyll                      # don't let Jekyll drop files/folders starting with "_"
git init -q -b gh-pages
git add -A
git -c user.name="$(git config --global user.name)" -c user.email="$(git config --global user.email)" \
    commit -qm "deploy: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git push -f git@github.com:luxiang0412/dify-aip-book.git gh-pages
rm -rf .git
