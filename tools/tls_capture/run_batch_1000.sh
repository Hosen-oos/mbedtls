#!/bin/bash
# 批量执行TLS捕获脚本
# 执行997次TLS捕获（已有3次，共1000次）
# 每次只保留 tls_all_messages.txt 文件

# 不使用 set -e，允许在循环中继续执行

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="$SCRIPT_DIR/results"
TOTAL_RUNS=997
CURRENT_RUN=0

echo "=========================================="
echo "批量TLS捕获执行脚本"
echo "=========================================="
echo "目标：执行 $TOTAL_RUNS 次TLS捕获"
echo "结果目录：$RESULTS_DIR"
echo "开始时间：$(date)"
echo ""

# 确保结果目录存在
mkdir -p "$RESULTS_DIR"

# 统计变量
SUCCESS_COUNT=0
FAIL_COUNT=0

# 执行循环
for i in $(seq 1 $TOTAL_RUNS); do
    CURRENT_RUN=$i
    TIMESTAMP=$(date +%Y%m%d_%H%M%S_%N | cut -c1-21)
    OUTPUT_DIR="$RESULTS_DIR/tls_capture_${TIMESTAMP}"
    
    echo "[$CURRENT_RUN/$TOTAL_RUNS] 开始执行 TLS 捕获..."
    
    # 执行单次捕获（静默执行，错误信息保存到临时文件）
    TEMP_LOG="/tmp/tls_capture_run_${TIMESTAMP}.log"
    if "$SCRIPT_DIR/run_test.sh" "$OUTPUT_DIR" > "$TEMP_LOG" 2>&1; then
        # 检查是否成功生成 tls_all_messages.txt
        if [ -f "$OUTPUT_DIR/tls_all_messages.txt" ]; then
            # 删除不需要的文件
            rm -f "$OUTPUT_DIR/client.log" \
                  "$OUTPUT_DIR/proxy.log" \
                  "$OUTPUT_DIR/server.log" \
                  "$OUTPUT_DIR/server.crt" \
                  "$OUTPUT_DIR/server.key" 2>/dev/null || true
            
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            
            # 每10次显示一次进度
            if [ $((CURRENT_RUN % 10)) -eq 0 ]; then
                echo "  ✓ 成功 [$CURRENT_RUN/$TOTAL_RUNS] (成功: $SUCCESS_COUNT, 失败: $FAIL_COUNT)"
            fi
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
            echo "  ✗ 失败 [$CURRENT_RUN/$TOTAL_RUNS] - 未生成 tls_all_messages.txt"
            # 删除失败的目录
            rm -rf "$OUTPUT_DIR" 2>/dev/null || true
        fi
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "  ✗ 失败 [$CURRENT_RUN/$TOTAL_RUNS] - 执行错误"
        # 删除失败的目录
        rm -rf "$OUTPUT_DIR" 2>/dev/null || true
    fi
    
    # 清理临时日志
    rm -f "$TEMP_LOG" 2>/dev/null || true
    
    # 短暂延迟，避免端口冲突和资源竞争
    sleep 0.3
done

echo ""
echo "=========================================="
echo "批量执行完成！"
echo "=========================================="
echo "总执行次数: $TOTAL_RUNS"
echo "成功次数: $SUCCESS_COUNT"
echo "失败次数: $FAIL_COUNT"
echo "结束时间: $(date)"
echo ""
echo "结果目录: $RESULTS_DIR"
echo "所有 tls_all_messages.txt 文件已保存在结果目录中"
echo ""

# 统计最终的文件数量
FINAL_COUNT=$(find "$RESULTS_DIR" -name "tls_all_messages.txt" -type f | wc -l)
echo "当前结果目录中共有 $FINAL_COUNT 个 tls_all_messages.txt 文件"
