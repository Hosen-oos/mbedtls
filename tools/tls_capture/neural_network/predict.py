"""
预测脚本：加载模型、单文件预测、输出结果
"""

import argparse
import torch
import torch.nn.functional as F
from pathlib import Path
import numpy as np

from config import DEVICE, BEST_MODEL_PATH, MAX_MESSAGE_LENGTH, MAX_MESSAGES_PER_FILE
from data_loader import parse_tls_file, pad_or_truncate
from model import create_model


def load_model(model_path: Path, device: torch.device) -> torch.nn.Module:
    """
    加载训练好的模型
    
    Args:
        model_path: 模型文件路径
        device: 设备
    
    Returns:
        加载的模型
    """
    # 创建模型
    model = create_model()
    
    # 加载权重
    checkpoint = torch.load(model_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model = model.to(device)
    model.eval()
    
    print(f"模型加载成功: {model_path}")
    if 'epoch' in checkpoint:
        print(f"训练轮数: {checkpoint['epoch']}")
    if 'val_acc' in checkpoint:
        print(f"验证准确率: {checkpoint['val_acc']:.2f}%")
    
    return model


def preprocess_file(file_path: Path) -> Tuple[torch.Tensor, torch.Tensor]:
    """
    预处理单个文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        (messages_tensor, mask_tensor)
    """
    # 解析文件
    messages = parse_tls_file(file_path)
    
    if len(messages) == 0:
        # 如果文件为空，返回一个空消息
        messages = [(np.array([], dtype=np.uint8), {})]
    
    # 限制消息数量
    messages = messages[:MAX_MESSAGES_PER_FILE]
    
    # 处理每个消息
    processed_messages = []
    for bytes_array, metadata in messages:
        processed = pad_or_truncate(bytes_array, MAX_MESSAGE_LENGTH, 0)
        processed_messages.append(processed)
    
    # 转换为tensor
    messages_tensor = torch.zeros((MAX_MESSAGES_PER_FILE, MAX_MESSAGE_LENGTH), dtype=torch.long)
    mask_tensor = torch.zeros(MAX_MESSAGES_PER_FILE, dtype=torch.bool)
    
    for i, msg in enumerate(processed_messages):
        messages_tensor[i] = torch.from_numpy(msg.astype(np.int64))
        mask_tensor[i] = True
    
    # 添加batch维度
    messages_tensor = messages_tensor.unsqueeze(0)  # (1, num_messages, seq_length)
    mask_tensor = mask_tensor.unsqueeze(0)  # (1, num_messages)
    
    return messages_tensor, mask_tensor


def predict_file(model: torch.nn.Module, file_path: Path, device: torch.device) -> dict:
    """
    对单个文件进行预测
    
    Args:
        model: 模型
        file_path: 文件路径
        device: 设备
    
    Returns:
        预测结果字典
    """
    # 预处理
    messages_tensor, mask_tensor = preprocess_file(file_path)
    
    # 移动到设备
    messages_tensor = messages_tensor.to(device)
    mask_tensor = mask_tensor.to(device)
    
    # 预测
    with torch.no_grad():
        logits = model(messages_tensor, mask_tensor)
        probabilities = F.softmax(logits, dim=1)
        predicted_class = torch.argmax(logits, dim=1).item()
        confidence = probabilities[0, predicted_class].item()
    
    # 结果
    class_names = ['真实数据', '模拟数据']
    result = {
        'file_path': str(file_path),
        'predicted_class': predicted_class,
        'class_name': class_names[predicted_class],
        'confidence': confidence,
        'probabilities': {
            '真实数据': probabilities[0, 0].item(),
            '模拟数据': probabilities[0, 1].item()
        }
    }
    
    return result


def main():
    parser = argparse.ArgumentParser(description='预测TLS消息文件')
    parser.add_argument('file_path', type=str, help='要预测的文件路径')
    parser.add_argument('--model-path', type=str, default=str(BEST_MODEL_PATH),
                       help='模型文件路径')
    parser.add_argument('--device', type=str, default=DEVICE,
                       help='设备 (cpu/cuda)')
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    file_path = Path(args.file_path)
    if not file_path.exists():
        print(f"错误: 文件不存在: {file_path}")
        return
    
    # 检查模型是否存在
    model_path = Path(args.model_path)
    if not model_path.exists():
        print(f"错误: 模型文件不存在: {model_path}")
        print("请先训练模型或指定正确的模型路径")
        return
    
    # 设备
    device = torch.device(args.device)
    print(f"使用设备: {device}")
    
    # 加载模型
    print("\n加载模型...")
    model = load_model(model_path, device)
    
    # 预测
    print(f"\n预测文件: {file_path}")
    result = predict_file(model, file_path, device)
    
    # 输出结果
    print("\n" + "=" * 60)
    print("预测结果")
    print("=" * 60)
    print(f"文件路径: {result['file_path']}")
    print(f"预测类别: {result['class_name']} (类别ID: {result['predicted_class']})")
    print(f"置信度: {result['confidence']:.4f} ({result['confidence']*100:.2f}%)")
    print(f"\n各类别概率:")
    for class_name, prob in result['probabilities'].items():
        print(f"  {class_name}: {prob:.4f} ({prob*100:.2f}%)")
    print("=" * 60)


if __name__ == '__main__':
    main()
