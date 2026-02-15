"""
训练脚本：数据加载、模型训练、验证评估、模型保存
"""

import os
import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm
import numpy as np
from pathlib import Path

from config import (
    REAL_DATA_DIR, SIMULATED_DATA_DIR, BEST_MODEL_PATH,
    BATCH_SIZE, LEARNING_RATE, NUM_EPOCHS, EARLY_STOPPING_PATIENCE,
    TRAIN_RATIO, VAL_RATIO, TEST_RATIO, DEVICE, RANDOM_SEED
)
from data_loader import create_data_loaders
from model import create_model
from utils import save_training_history, plot_training_curves


def set_seed(seed: int):
    """设置随机种子"""
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    import random
    random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def train_epoch(model: nn.Module, train_loader: DataLoader, 
                criterion: nn.Module, optimizer: optim.Optimizer,
                device: torch.device):
    """
    训练一个epoch
    
    Returns:
        (平均损失, 准确率)
    """
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0
    
    pbar = tqdm(train_loader, desc="Training")
    for messages, masks, labels in pbar:
        messages = messages.to(device)
        masks = masks.to(device)
        labels = labels.to(device)
        
        # 前向传播
        optimizer.zero_grad()
        logits = model(messages, masks)
        loss = criterion(logits, labels)
        
        # 反向传播
        loss.backward()
        optimizer.step()
        
        # 统计
        total_loss += loss.item()
        predictions = torch.argmax(logits, dim=1)
        correct += (predictions == labels).sum().item()
        total += labels.size(0)
        
        # 更新进度条
        pbar.set_postfix({
            'loss': f'{loss.item():.4f}',
            'acc': f'{100 * correct / total:.2f}%'
        })
    
    avg_loss = total_loss / len(train_loader)
    accuracy = 100 * correct / total
    
    return avg_loss, accuracy


def validate(model: nn.Module, val_loader: DataLoader,
             criterion: nn.Module, device: torch.device):
    """
    验证模型
    
    Returns:
        (平均损失, 准确率)
    """
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        for messages, masks, labels in tqdm(val_loader, desc="Validating"):
            messages = messages.to(device)
            masks = masks.to(device)
            labels = labels.to(device)
            
            logits = model(messages, masks)
            loss = criterion(logits, labels)
            
            total_loss += loss.item()
            predictions = torch.argmax(logits, dim=1)
            correct += (predictions == labels).sum().item()
            total += labels.size(0)
    
    avg_loss = total_loss / len(val_loader)
    accuracy = 100 * correct / total
    
    return avg_loss, accuracy


def train(model: nn.Module, train_loader: DataLoader, val_loader: DataLoader,
          num_epochs: int = NUM_EPOCHS, learning_rate: float = LEARNING_RATE,
          early_stopping_patience: int = EARLY_STOPPING_PATIENCE,
          device: torch.device = None, model_save_path: Path = BEST_MODEL_PATH):
    """
    训练模型
    
    Args:
        model: 模型实例
        train_loader: 训练数据加载器
        val_loader: 验证数据加载器
        num_epochs: 训练轮数
        learning_rate: 学习率
        early_stopping_patience: 早停耐心值
        device: 设备
        model_save_path: 模型保存路径
    """
    if device is None:
        device = torch.device(DEVICE)
    
    # 损失函数和优化器
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # 训练历史
    history = {
        'train_loss': [],
        'train_acc': [],
        'val_loss': [],
        'val_acc': []
    }
    
    # 早停
    best_val_loss = float('inf')
    patience_counter = 0
    
    print(f"\n开始训练，共 {num_epochs} 个epoch")
    print(f"设备: {device}")
    print(f"模型参数量: {model.count_parameters():,}")
    print("-" * 60)
    
    for epoch in range(1, num_epochs + 1):
        print(f"\nEpoch {epoch}/{num_epochs}")
        
        # 训练
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        
        # 验证
        val_loss, val_acc = validate(model, val_loader, criterion, device)
        
        # 记录历史
        history['train_loss'].append(train_loss)
        history['train_acc'].append(train_acc)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)
        
        # 打印结果
        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
        
        # 保存最佳模型
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'val_acc': val_acc,
                'history': history
            }, model_save_path)
            print(f"✓ 保存最佳模型 (Val Loss: {val_loss:.4f})")
        else:
            patience_counter += 1
            print(f"  早停计数: {patience_counter}/{early_stopping_patience}")
        
        # 早停
        if patience_counter >= early_stopping_patience:
            print(f"\n早停触发！最佳验证损失: {best_val_loss:.4f}")
            break
    
    # 保存训练历史
    history_path = model_save_path.parent / "training_history.json"
    save_training_history(history, history_path)
    
    # 绘制训练曲线
    plot_path = model_save_path.parent / "training_curves.png"
    plot_training_curves(history, plot_path)
    
    print(f"\n训练完成！")
    print(f"最佳模型保存在: {model_save_path}")
    print(f"训练历史保存在: {history_path}")
    print(f"训练曲线保存在: {plot_path}")


def main():
    parser = argparse.ArgumentParser(description='训练TLS消息分类模型')
    parser.add_argument('--real-data-pattern', type=str, 
                       default=str(REAL_DATA_DIR),
                       help='真实数据文件模式（glob模式）')
    parser.add_argument('--simulated-data-dir', type=str,
                       default=str(SIMULATED_DATA_DIR),
                       help='模拟数据目录')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE,
                       help='批次大小')
    parser.add_argument('--learning-rate', type=float, default=LEARNING_RATE,
                       help='学习率')
    parser.add_argument('--num-epochs', type=int, default=NUM_EPOCHS,
                       help='训练轮数')
    parser.add_argument('--early-stopping-patience', type=int,
                       default=EARLY_STOPPING_PATIENCE,
                       help='早停耐心值')
    parser.add_argument('--model-save-path', type=str,
                       default=str(BEST_MODEL_PATH),
                       help='模型保存路径')
    parser.add_argument('--seed', type=int, default=RANDOM_SEED,
                       help='随机种子')
    
    args = parser.parse_args()
    
    # 设置随机种子
    set_seed(args.seed)
    
    # 设备
    device = torch.device(DEVICE)
    print(f"使用设备: {device}")
    
    # 创建数据加载器
    print("\n加载数据...")
    train_loader, val_loader, test_loader = create_data_loaders(
        real_data_pattern=args.real_data_pattern,
        simulated_data_dir=Path(args.simulated_data_dir),
        train_ratio=TRAIN_RATIO,
        val_ratio=VAL_RATIO,
        test_ratio=TEST_RATIO,
        batch_size=args.batch_size,
        random_seed=args.seed
    )
    
    # 创建模型
    print("\n创建模型...")
    model = create_model()
    model = model.to(device)
    
    # 训练
    train(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=args.num_epochs,
        learning_rate=args.learning_rate,
        early_stopping_patience=args.early_stopping_patience,
        device=device,
        model_save_path=Path(args.model_save_path)
    )


if __name__ == '__main__':
    main()
