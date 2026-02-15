#!/bin/bash
# 批量生成模拟TLS消息的便捷启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "批量生成模拟TLS消息"
echo "=========================================="
echo "此操作将生成 1000 个模拟TLS消息文件。"
echo "所有结果将保存在 $SCRIPT_DIR/results_simulated/ 目录下。"
echo ""
read -p "是否继续？ (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "开始执行批量生成..."
    "$SCRIPT_DIR/generate_batch_1000.sh"
else
    echo "操作已取消。"
fi
