#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tag=""

while (($#)); do
  case "$1" in
    --tag) tag="${2:?--tag 需要版本号}"; shift 2 ;;
    -h|--help) echo "用法: ./pack.sh --tag 1.0.0"; exit 0 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

if ! [[ "$tag" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "必须使用明确版本号，例如 --tag 1.0.0" >&2
  exit 2
fi

mkdir -p "$project_root/build"
docker build --tag "cashbook:$tag" "$project_root"
docker save --output "$project_root/build/cashbook-$tag.tar" "cashbook:$tag"
echo "已生成 build/cashbook-$tag.tar"

