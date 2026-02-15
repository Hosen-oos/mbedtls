#!/bin/bash
# 便捷启动脚本 - 批量执行997次TLS捕获

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "批量TLS捕获 - 启动脚本"
echo "=========================================="
echo ""
echo "此脚本将执行 997 次 TLS 捕获"
echo "（已有 3 次结果，共需要 1000 次）"
echo ""
echo "注意："
echo "  - 每次捕获大约需要 5-10 秒"
echo "  - 预计总耗时：约 1.5-3 小时"
echo "  - 结果将保存在: $SCRIPT_DIR/results/"
echo "  - 每个结果目录只保留 tls_all_messages.txt 文件"
echo ""
echo "是否继续？(y/n)"
read -r answer

if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "开始执行..."
echo "提示：可以按 Ctrl+C 中断执行（已完成的捕获会保留）"
echo ""

# 执行批量脚本
"$SCRIPT_DIR/run_batch_1000.sh"
