#!/bin/bash
# 快速生成模拟TLS消息的便捷脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "TLS消息模拟生成器 - 快速使用"
echo "=========================================="
echo ""
echo "请选择操作："
echo "  1) 生成单个测试文件（8条消息）"
echo "  2) 生成单个文件（自定义消息数）"
echo "  3) 批量生成（1000个文件）"
echo "  4) 批量生成（自定义数量）"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "生成测试文件..."
        python3 generate_tls_simulated.py -n 8 --output-dir results_simulated
        echo ""
        echo "✓ 完成！文件保存在 results_simulated/ 目录"
        ;;
    2)
        read -p "请输入消息数量: " num_msg
        echo ""
        echo "生成文件..."
        python3 generate_tls_simulated.py -n "$num_msg" --output-dir results_simulated
        echo ""
        echo "✓ 完成！文件保存在 results_simulated/ 目录"
        ;;
    3)
        echo ""
        echo "批量生成1000个文件（每个文件8条消息）..."
        echo "这可能需要一些时间..."
        ./generate_batch_simulated.sh 1000 8
        ;;
    4)
        read -p "请输入文件数量: " num_files
        read -p "请输入每个文件的消息数: " num_msg
        echo ""
        echo "批量生成 $num_files 个文件（每个文件 $num_msg 条消息）..."
        echo "这可能需要一些时间..."
        ./generate_batch_simulated.sh "$num_files" "$num_msg"
        ;;
    *)
        echo "无效选项"
        exit 1
        ;;
esac

echo ""
echo "查看生成的文件："
echo "  ls -lh results_simulated/"
echo ""
echo "查看文件内容："
echo "  cat results_simulated/tls_simulated_*.txt | head -50"
