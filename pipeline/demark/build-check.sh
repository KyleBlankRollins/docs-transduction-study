#!/usr/bin/env bash
# Build check for P3 exit gate
# Per ADR-0003: two full builds of pinned docs tree (explicit + implicit)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$REPO_ROOT/build"

# Clean up build artifacts on any exit path (fixpoint 4)
cleanup() {
  rm -rf "$BUILD_DIR/explicit" "$BUILD_DIR/implicit"
}
trap cleanup EXIT
VENDOR_DIR="$REPO_ROOT/vendor/astro-docs"
BUILD_DIR="$REPO_ROOT/build"
EXPLICIT_DIR="$REPO_ROOT/corpus/explicit"
IMPLICIT_DIR="$REPO_ROOT/corpus/implicit"
SPECIMENS_CSV="$REPO_ROOT/corpus/specimens.csv"

echo "=== P3 Build Check ==="

echo "--- Step 1: Installing dependencies ---"
cd "$VENDOR_DIR"
pnpm install --frozen-lockfile 2>&1 | tail -3
echo "Dependencies installed."

echo "--- Step 2: Materializing trees ---"

echo "Copying pinned tree to $BUILD_DIR/explicit..."
rm -rf "$BUILD_DIR/explicit"
mkdir -p "$BUILD_DIR/explicit"
rsync -a --exclude=.git --exclude=node_modules "$VENDOR_DIR/" "$BUILD_DIR/explicit/"
cd "$BUILD_DIR/explicit"
pnpm install --prefer-offline 2>&1 | tail -3

while IFS=',' read -r id rest || [ -n "$id" ]; do
    case "$id" in specimen_id|"") continue ;; esac
    source_path="$(echo "$rest" | cut -d',' -f1)"
    cp "$EXPLICIT_DIR/$source_path" "$BUILD_DIR/explicit/src/content/docs/en/$source_path"
    echo "  explicit: $id -> $source_path"
done < "$SPECIMENS_CSV"
echo "Explicit tree materialized."

echo "Copying pinned tree to $BUILD_DIR/implicit..."
rm -rf "$BUILD_DIR/implicit"
mkdir -p "$BUILD_DIR/implicit"
rsync -a --exclude=.git --exclude=node_modules "$VENDOR_DIR/" "$BUILD_DIR/implicit/"
cd "$BUILD_DIR/implicit"
pnpm install --prefer-offline 2>&1 | tail -3

while IFS=',' read -r id rest || [ -n "$id" ]; do
    case "$id" in specimen_id|"") continue ;; esac
    source_path="$(echo "$rest" | cut -d',' -f1)"
    cp "$IMPLICIT_DIR/$source_path" "$BUILD_DIR/implicit/src/content/docs/en/$source_path"
    echo "  implicit: $id -> $source_path"
done < "$SPECIMENS_CSV"
echo "Implicit tree materialized."

echo "--- Step 3: Building explicit arm ---"
cd "$BUILD_DIR/explicit"
EXIT_A=0
pnpm build > /tmp/build-explicit.log 2>&1 || EXIT_A=$?
tail -5 /tmp/build-explicit.log

echo "--- Step 4: Building implicit arm ---"
cd "$BUILD_DIR/implicit"
EXIT_B=0
pnpm build > /tmp/build-implicit.log 2>&1 || EXIT_B=$?
tail -5 /tmp/build-implicit.log

echo "--- Results ---"
echo "Explicit build exit code: $EXIT_A"
echo "Implicit build exit code: $EXIT_B"

rm -rf "$BUILD_DIR/explicit" "$BUILD_DIR/implicit"
echo "Build output deleted."

if [ "$EXIT_A" -ne 0 ] || [ "$EXIT_B" -ne 0 ]; then
    echo "BUILD CHECK FAILED"
    exit 1
fi

echo "BUILD CHECK PASSED"
