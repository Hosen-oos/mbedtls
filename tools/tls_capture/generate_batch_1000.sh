#!/bin/bash
# 批量生成1000次模拟TLS消息

set +e  # 允许继续执行即使有错误

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/results_simulated"
TOTAL_RUNS=1000

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

cd "$SCRIPT_DIR"

echo "=========================================="
echo "开始批量生成模拟TLS消息"
echo "=========================================="
echo "目标: 生成 $TOTAL_RUNS 个模拟文件"
echo "输出目录: $OUTPUT_DIR"
echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 检查Python脚本是否存在
if [ ! -f "generate_tls_simulated.py" ]; then
    echo "错误: 找不到 generate_tls_simulated.py"
    exit 1
fi

SUCCESS_COUNT=0
FAIL_COUNT=0
START_TIME=$(date +%s)

# 批量生成
for i in $(seq 1 $TOTAL_RUNS); do
    # 使用编号确保文件名唯一
    if python3 generate_tls_simulated.py -n 8 --output-dir "$OUTPUT_DIR" --id "$i" > /dev/null 2>&1; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        
        # 每50次显示进度
        if [ $((i % 50)) -eq 0 ]; then
            ELAPSED=$(($(date +%s) - START_TIME))
            RATE=$((i * 100 / ELAPSED)) 2>/dev/null || RATE=0
            REMAINING=$(((TOTAL_RUNS - i) * ELAPSED / i)) 2>/dev/null || REMAINING=0
            echo "[$i/$TOTAL_RUNS] 已生成 $SUCCESS_COUNT 个文件 (失败: $FAIL_COUNT) | 已用时: ${ELAPSED}秒 | 预计剩余: ${REMAINING}秒"
        fi
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        if [ $((FAIL_COUNT % 10)) -eq 0 ]; then
            echo "  ⚠ 警告: 已有 $FAIL_COUNT 个失败"
        fi
    fi
done

END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))

echo ""
echo "=========================================="
echo "批量生成完成"
echo "=========================================="
echo "总文件数: $TOTAL_RUNS"
echo "成功: $SUCCESS_COUNT"
echo "失败: $FAIL_COUNT"
echo "总耗时: ${ELAPSED_TIME}秒"
echo "平均速度: $((TOTAL_RUNS * 100 / ELAPSED_TIME)) 文件/100秒" 2>/dev/null || echo "平均速度: 计算中..."
echo "结束时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "输出目录: $OUTPUT_DIR"
FINAL_COUNT=$(find "$OUTPUT_DIR" -name "tls_simulated_*.txt" -type f 2>/dev/null | wc -l)
echo "实际文件数量: $FINAL_COUNT"
