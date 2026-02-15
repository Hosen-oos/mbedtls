#!/bin/bash
# 从根目录运行的快捷脚本
# 自动切换到tools/tls_capture并运行测试

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/tools/tls_capture"
exec ./run_test.sh "$@"
