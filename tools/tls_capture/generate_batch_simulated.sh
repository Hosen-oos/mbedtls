#!/bin/bash
# 批量生成模拟TLS消息脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/results_simulated"
PYTHON_SCRIPT="$SCRIPT_DIR/generate_tls_simulated.py"

# 默认参数
NUM_FILES=${1:-1000}
MESSAGES_PER_FILE=${2:-8}

echo "=========================================="
echo "批量生成模拟TLS消息"
echo "=========================================="
echo "生成文件数量: $NUM_FILES"
echo "每个文件消息数: $MESSAGES_PER_FILE"
echo "输出目录: $OUTPUT_DIR"
echo "开始时间: $(date)"
echo ""

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 检查Python脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "错误: 找不到Python脚本: $PYTHON_SCRIPT"
    exit 1
fi

# 检查Python是否可用
if ! command -v python3 &> /dev/null; then
    echo "错误: 找不到 python3"
    exit 1
fi

# 统计变量
SUCCESS_COUNT=0
FAIL_COUNT=0

# 生成文件
for i in $(seq 1 $NUM_FILES); do
    if python3 "$PYTHON_SCRIPT" -n "$MESSAGES_PER_FILE" --output-dir "$OUTPUT_DIR" > /dev/null 2>&1; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        
        # 每100个文件显示一次进度
        if [ $((i % 100)) -eq 0 ]; then
            echo "  ✓ 进度: [$i/$NUM_FILES] (成功: $SUCCESS_COUNT, 失败: $FAIL_COUNT)"
        fi
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "  ✗ 失败: 文件 #$i"
    fi
done

echo ""
echo "=========================================="
echo "批量生成完成！"
echo "=========================================="
echo "总文件数: $NUM_FILES"
echo "成功: $SUCCESS_COUNT"
echo "失败: $FAIL_COUNT"
echo "结束时间: $(date)"
echo ""

# 统计最终的文件数量
FINAL_COUNT=$(find "$OUTPUT_DIR" -name "tls_simulated_*.txt" -type f | wc -l)
echo "结果目录中共有 $FINAL_COUNT 个模拟文件"
echo "结果目录: $OUTPUT_DIR"
