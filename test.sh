#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work_root="$project_root/build/test"
local_mode=false
keep_data=false
reset_data=false
reset_env=false
host="127.0.0.1"
port="8000"
passthrough=()

usage() {
  awk 'BEGIN {show=0} /^# 账本测试/ {show=1} show {if ($0 !~ /^#/) exit; sub(/^# ?/, ""); print}' "$0"
}

# 账本测试与本地运行
#
# 用法：
#   ./test.sh [--keep-data] [--reset-data] [--reset-env] [-- pytest参数]
#   ./test.sh --local [--host HOST] [--port PORT] [--reset-data] [-- Flask参数]
#
# 参数：
#   -h, --help       显示命令速查
#   --local          启动隔离的本地服务，不运行 pytest
#   --host HOST      本地服务监听地址，默认 127.0.0.1
#   --port PORT      本地服务端口，默认 8000
#   --keep-data      pytest 模式保留上次测试数据
#   --reset-data     清空当前模式的数据
#   --reset-env      重建 build/test/.venv
#   --               后续参数传给 pytest 或本地服务

while (($#)); do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --local) local_mode=true; shift ;;
    --host) host="${2:?--host 需要参数}"; shift 2 ;;
    --port) port="${2:?--port 需要参数}"; shift 2 ;;
    --keep-data) keep_data=true; shift ;;
    --reset-data) reset_data=true; shift ;;
    --reset-env) reset_env=true; shift ;;
    --) shift; passthrough=("$@"); break ;;
    *) echo "未知参数: $1" >&2; usage; exit 2 ;;
  esac
done

if ! $local_mode && { [[ "$host" != "127.0.0.1" ]] || [[ "$port" != "8000" ]]; }; then
  echo "--host 和 --port 只能与 --local 一起使用" >&2
  exit 2
fi
if $local_mode && $keep_data; then
  echo "--keep-data 只用于 pytest 模式" >&2
  exit 2
fi
if ! [[ "$port" =~ ^[0-9]+$ ]] || ((port < 1 || port > 65535)); then
  echo "端口必须在 1 到 65535 之间" >&2
  exit 2
fi

if [[ -n "${PYTHON_BIN:-}" ]]; then
  python_bin="$PYTHON_BIN"
  if ! command -v "$python_bin" >/dev/null 2>&1; then
    echo "PYTHON_BIN 指定的 Python 不存在: $python_bin" >&2
    exit 1
  fi
elif command -v python3.13 >/dev/null 2>&1; then
  python_bin="python3.13"
else
  python_bin="python3"
  if ! command -v "$python_bin" >/dev/null 2>&1; then
    echo "未找到可用的 Python；请安装 Python 3.13 或通过 PYTHON_BIN 指定" >&2
    exit 1
  fi
  echo "WARNING: 未找到 Python 3.13，回退使用系统 Python: $(command -v "$python_bin")" >&2
fi
version="$($python_bin -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$version" != "3.13" ]]; then
  echo "WARNING: 推荐使用 Python 3.13，当前使用 Python $version" >&2
fi

mkdir -p "$work_root"
rsync -a --delete \
  --exclude '/.git/' --exclude '/.env' --exclude '/.venv/' \
  --exclude '/data/' --exclude '/build/' --exclude '/__pycache__/' \
  --exclude '*.pyc' --exclude '/.pytest_cache/' \
  "$project_root/" "$work_root/"

venv="$work_root/.venv"
if $reset_env; then
  rm -rf "$venv"
fi
if [[ -x "$venv/bin/python" ]]; then
  venv_version="$("$venv/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$venv_version" != "$version" ]]; then
    echo "WARNING: Python 版本已从 $venv_version 变为 $version，正在重建隔离环境" >&2
    rm -rf "$venv"
  fi
fi
if [[ ! -x "$venv/bin/python" ]]; then
  "$python_bin" -m venv "$venv"
fi
requirements_hash="$(shasum "$work_root/requirements.txt" "$work_root/requirements-dev.txt" | shasum | awk '{print $1}')"
if [[ ! -f "$venv/.requirements-hash" ]] || [[ "$(cat "$venv/.requirements-hash")" != "$requirements_hash" ]]; then
  "$venv/bin/python" -m pip install --disable-pip-version-check -r "$work_root/requirements-dev.txt"
  printf '%s\n' "$requirements_hash" > "$venv/.requirements-hash"
fi

if $local_mode; then
  data_root="$work_root/data/local"
else
  data_root="$work_root/data/test"
fi
if $reset_data || { ! $local_mode && ! $keep_data; }; then
  rm -rf "$data_root"
fi
mkdir -p "$data_root/logs"

cd "$work_root"
export CASHBOOK_DATABASE_PATH="$data_root/cashbook.db"
export CASHBOOK_LOG_FILE="$data_root/logs/cashbook.log"
export PYTHONDONTWRITEBYTECODE=1
export SECRET_KEY="${SECRET_KEY:-test-only-secret-key}"

if $local_mode; then
  if ((${#passthrough[@]})); then
    exec "$venv/bin/python" -m flask --app wsgi:app run --no-debugger --no-reload --host "$host" --port "$port" "${passthrough[@]}"
  fi
  exec "$venv/bin/python" -m flask --app wsgi:app run --no-debugger --no-reload --host "$host" --port "$port"
fi
if ((${#passthrough[@]})); then
  exec "$venv/bin/python" -m pytest "${passthrough[@]}"
fi
exec "$venv/bin/python" -m pytest
