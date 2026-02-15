"""
工具函数：可视化、评估指标、辅助函数
"""

import json
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, List
import numpy as np
import torch
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix


def save_training_history(history: Dict[str, List[float]], file_path: Path):
    """
    保存训练历史到JSON文件
    
    Args:
        history: 训练历史字典
        file_path: 保存路径
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    print(f"训练历史已保存到: {file_path}")


def load_training_history(file_path: Path) -> Dict[str, List[float]]:
    """
    从JSON文件加载训练历史
    
    Args:
        file_path: 文件路径
    
    Returns:
        训练历史字典
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        history = json.load(f)
    return history


def plot_training_curves(history: Dict[str, List[float]], save_path: Path = None):
    """
    绘制训练曲线
    
    Args:
        history: 训练历史字典
        save_path: 保存路径（可选）
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    epochs = range(1, len(history['train_loss']) + 1)
    
    # 损失曲线
    axes[0].plot(epochs, history['train_loss'], 'b-', label='训练损失', linewidth=2)
    axes[0].plot(epochs, history['val_loss'], 'r-', label='验证损失', linewidth=2)
    axes[0].set_xlabel('Epoch', fontsize=12)
    axes[0].set_ylabel('Loss', fontsize=12)
    axes[0].set_title('训练和验证损失', fontsize=14, fontweight='bold')
    axes[0].legend(fontsize=10)
    axes[0].grid(True, alpha=0.3)
    
    # 准确率曲线
    axes[1].plot(epochs, history['train_acc'], 'b-', label='训练准确率', linewidth=2)
    axes[1].plot(epochs, history['val_acc'], 'r-', label='验证准确率', linewidth=2)
    axes[1].set_xlabel('Epoch', fontsize=12)
    axes[1].set_ylabel('Accuracy (%)', fontsize=12)
    axes[1].set_title('训练和验证准确率', fontsize=14, fontweight='bold')
    axes[1].legend(fontsize=10)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"训练曲线已保存到: {save_path}")
    else:
        plt.show()
    
    plt.close()


def calculate_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    """
    计算分类指标
    
    Args:
        y_true: 真实标签
        y_pred: 预测标签
    
    Returns:
        指标字典
    """
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
    
    metrics = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1
    }
    
    return metrics


def plot_confusion_matrix(y_true: List[int], y_pred: List[int], 
                         class_names: List[str] = None, save_path: Path = None):
    """
    绘制混淆矩阵
    
    Args:
        y_true: 真实标签
        y_pred: 预测标签
        class_names: 类别名称
        save_path: 保存路径（可选）
    """
    if class_names is None:
        class_names = ['真实数据', '模拟数据']
    
    cm = confusion_matrix(y_true, y_pred)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    
    # 设置标签
    ax.set(xticks=np.arange(cm.shape[1]),
           yticks=np.arange(cm.shape[0]),
           xticklabels=class_names,
           yticklabels=class_names,
           title='混淆矩阵',
           ylabel='真实标签',
           xlabel='预测标签')
    
    # 添加数值
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], 'd'),
                   ha="center", va="center",
                   color="white" if cm[i, j] > thresh else "black")
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"混淆矩阵已保存到: {save_path}")
    else:
        plt.show()
    
    plt.close()


def evaluate_model(model: torch.nn.Module, data_loader, device: torch.device) -> Dict:
    """
    评估模型
    
    Args:
        model: 模型
        data_loader: 数据加载器
        device: 设备
    
    Returns:
        评估结果字典
    """
    model.eval()
    all_predictions = []
    all_labels = []
    
    with torch.no_grad():
        for messages, masks, labels in data_loader:
            messages = messages.to(device)
            masks = masks.to(device)
            labels = labels.to(device)
            
            logits = model(messages, masks)
            predictions = torch.argmax(logits, dim=1)
            
            all_predictions.extend(predictions.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    # 计算指标
    metrics = calculate_metrics(all_labels, all_predictions)
    
    return {
        'metrics': metrics,
        'predictions': all_predictions,
        'labels': all_labels
    }


def print_evaluation_results(eval_results: Dict, dataset_name: str = "数据集"):
    """
    打印评估结果
    
    Args:
        eval_results: 评估结果字典
        dataset_name: 数据集名称
    """
    metrics = eval_results['metrics']
    
    print(f"\n{dataset_name}评估结果:")
    print("=" * 60)
    print(f"准确率 (Accuracy):  {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
    print(f"精确率 (Precision): {metrics['precision']:.4f} ({metrics['precision']*100:.2f}%)")
    print(f"召回率 (Recall):    {metrics['recall']:.4f} ({metrics['recall']*100:.2f}%)")
    print(f"F1分数 (F1-Score):  {metrics['f1_score']:.4f} ({metrics['f1_score']*100:.2f}%)")
    print("=" * 60)
