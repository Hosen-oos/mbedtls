"""
数据加载器：解析TLS文件、提取Hex Dump字节序列、创建PyTorch Dataset
"""

import re
import glob
import random
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from config import (
    MAX_MESSAGE_LENGTH, PAD_VALUE, MAX_MESSAGES_PER_FILE,
    BATCH_SIZE, RANDOM_SEED
)


def extract_hex_dump_bytes(hex_lines: List[str]) -> np.ndarray:
    """
    从Hex Dump行中提取字节序列
    
    Args:
        hex_lines: Hex Dump行列表，例如：
            ['0000: 16 03 01 01 24 01 00 01 20 03 03 24 f0 4a 2e 33  |....$... ..$.J.3|', ...]
    
    Returns:
        numpy数组，包含提取的字节值（0-255）
    """
    bytes_list = []
    for line in hex_lines:
        # 提取十六进制字节部分（在冒号和|之间）
        match = re.search(r':\s+([0-9a-fA-F\s]+)\s+\|', line)
        if match:
            hex_str = match.group(1)
            # 分割十六进制字符串并转换为整数
            hex_bytes = hex_str.strip().split()
            for hex_byte in hex_bytes:
                try:
                    bytes_list.append(int(hex_byte, 16))
                except ValueError:
                    continue
    return np.array(bytes_list, dtype=np.uint8)


def parse_tls_file(file_path: Path) -> List[Tuple[np.ndarray, dict]]:
    """
    解析TLS文件，提取所有消息及其元数据
    
    Args:
        file_path: TLS文件路径
    
    Returns:
        消息列表，每个元素为(字节序列, 元数据字典)
    """
    messages = []
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 使用正则表达式匹配每个消息块
    message_pattern = r'Message #(\d+): (.+?)\nTime: (.+?)\nLength: (\d+) bytes\nRecord Layer:\n  ContentType: (.+?)\n  Version: (.+?)\n  Length: (\d+) bytes(?:.*?Handshake Layer:\n  HandshakeType: (.+?)\n  Length: (\d+) bytes)?.*?Hex Dump:\n((?:.*?\n)*?)(?====|$)'
    
    matches = re.finditer(message_pattern, content, re.DOTALL)
    
    for match in matches:
        msg_num = int(match.group(1))
        direction = match.group(2).strip()
        length = int(match.group(4))
        content_type = match.group(5).strip()
        version = match.group(6).strip()
        hex_dump = match.group(9) if match.group(9) else ""
        
        # 提取Hex Dump字节
        hex_lines = [line for line in hex_dump.split('\n') if ':' in line and '|' in line]
        if not hex_lines:
            continue
        
        bytes_array = extract_hex_dump_bytes(hex_lines)
        
        if len(bytes_array) == 0:
            continue
        
        # 元数据
        metadata = {
            'message_num': msg_num,
            'direction': direction,
            'length': length,
            'content_type': content_type,
            'version': version
        }
        
        messages.append((bytes_array, metadata))
    
    return messages


def pad_or_truncate(bytes_array: np.ndarray, target_length: int, pad_value: int = 0) -> np.ndarray:
    """
    填充或截断字节数组到目标长度
    
    Args:
        bytes_array: 输入字节数组
        target_length: 目标长度
        pad_value: 填充值
    
    Returns:
        处理后的字节数组
    """
    if len(bytes_array) > target_length:
        return bytes_array[:target_length]
    elif len(bytes_array) < target_length:
        padded = np.full(target_length, pad_value, dtype=np.uint8)
        padded[:len(bytes_array)] = bytes_array
        return padded
    else:
        return bytes_array


class TLSDataset(Dataset):
    """
    TLS消息数据集
    每个样本是一个文件，包含多个消息
    """
    
    def __init__(self, file_paths: List[Path], labels: List[int], max_message_length: int = MAX_MESSAGE_LENGTH):
        """
        Args:
            file_paths: 文件路径列表
            labels: 标签列表（0=真实，1=模拟）
            max_message_length: 最大消息长度
        """
        self.file_paths = file_paths
        self.labels = labels
        self.max_message_length = max_message_length
        
        assert len(file_paths) == len(labels), "文件路径和标签数量必须一致"
    
    def __len__(self) -> int:
        return len(self.file_paths)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, int]:
        """
        返回一个样本
        
        Returns:
            (messages_tensor, mask_tensor, label)
            - messages_tensor: shape (num_messages, max_message_length)
            - mask_tensor: shape (num_messages,) - 1表示有效消息，0表示填充
            - label: 标签（0或1）
        """
        file_path = self.file_paths[idx]
        label = self.labels[idx]
        
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
            processed = pad_or_truncate(bytes_array, self.max_message_length, PAD_VALUE)
            processed_messages.append(processed)
        
        # 转换为tensor
        num_messages = len(processed_messages)
        messages_tensor = torch.zeros((MAX_MESSAGES_PER_FILE, self.max_message_length), dtype=torch.long)
        mask_tensor = torch.zeros(MAX_MESSAGES_PER_FILE, dtype=torch.bool)
        
        for i, msg in enumerate(processed_messages):
            messages_tensor[i] = torch.from_numpy(msg.astype(np.int64))
            mask_tensor[i] = True
        
        return messages_tensor, mask_tensor, label


def collate_fn(batch: List[Tuple[torch.Tensor, torch.Tensor, int]]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    自定义批次整理函数
    
    Args:
        batch: 批次数据列表
    
    Returns:
        (messages_batch, masks_batch, labels_batch)
    """
    messages_list, masks_list, labels_list = zip(*batch)
    
    messages_batch = torch.stack(messages_list)  # (batch_size, num_messages, max_length)
    masks_batch = torch.stack(masks_list)  # (batch_size, num_messages)
    labels_batch = torch.tensor(labels_list, dtype=torch.long)  # (batch_size,)
    
    return messages_batch, masks_batch, labels_batch


def load_data_paths(real_data_pattern: str, simulated_data_dir: Path) -> Tuple[List[Path], List[int]]:
    """
    加载所有数据文件路径和标签
    
    Args:
        real_data_pattern: 真实数据文件模式（glob模式）
        simulated_data_dir: 模拟数据目录
    
    Returns:
        (文件路径列表, 标签列表)
    """
    file_paths = []
    labels = []
    
    # 加载真实数据
    real_files = glob.glob(real_data_pattern)
    for file_path in real_files:
        file_paths.append(Path(file_path))
        labels.append(0)  # 0 = 真实数据
    
    # 加载模拟数据
    simulated_files = list(simulated_data_dir.glob("tls_simulated_*.txt"))
    for file_path in simulated_files:
        file_paths.append(file_path)
        labels.append(1)  # 1 = 模拟数据
    
    return file_paths, labels


def split_dataset(file_paths: List[Path], labels: List[int], 
                  train_ratio: float, val_ratio: float, test_ratio: float,
                  random_seed: int = RANDOM_SEED) -> Tuple[List[Path], List[Path], List[Path], 
                                                           List[int], List[int], List[int]]:
    """
    划分数据集
    
    Args:
        file_paths: 文件路径列表
        labels: 标签列表
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        random_seed: 随机种子
    
    Returns:
        (train_paths, val_paths, test_paths, train_labels, val_labels, test_labels)
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, "比例之和必须为1"
    
    # 设置随机种子
    random.seed(random_seed)
    np.random.seed(random_seed)
    
    # 打乱数据
    indices = list(range(len(file_paths)))
    random.shuffle(indices)
    
    file_paths = [file_paths[i] for i in indices]
    labels = [labels[i] for i in indices]
    
    # 计算划分点
    n_total = len(file_paths)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)
    
    # 划分
    train_paths = file_paths[:n_train]
    val_paths = file_paths[n_train:n_train + n_val]
    test_paths = file_paths[n_train + n_val:]
    
    train_labels = labels[:n_train]
    val_labels = labels[n_train:n_train + n_val]
    test_labels = labels[n_train + n_val:]
    
    return train_paths, val_paths, test_paths, train_labels, val_labels, test_labels


def create_data_loaders(real_data_pattern: str, simulated_data_dir: Path,
                       train_ratio: float = 0.8, val_ratio: float = 0.1, test_ratio: float = 0.1,
                       batch_size: int = BATCH_SIZE, random_seed: int = RANDOM_SEED) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    创建数据加载器
    
    Args:
        real_data_pattern: 真实数据文件模式
        simulated_data_dir: 模拟数据目录
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        batch_size: 批次大小
        random_seed: 随机种子
    
    Returns:
        (train_loader, val_loader, test_loader)
    """
    # 加载数据路径
    file_paths, labels = load_data_paths(real_data_pattern, simulated_data_dir)
    
    print(f"总共加载 {len(file_paths)} 个文件")
    print(f"真实数据: {sum(1 for l in labels if l == 0)} 个")
    print(f"模拟数据: {sum(1 for l in labels if l == 1)} 个")
    
    # 划分数据集
    train_paths, val_paths, test_paths, train_labels, val_labels, test_labels = split_dataset(
        file_paths, labels, train_ratio, val_ratio, test_ratio, random_seed
    )
    
    print(f"\n数据集划分:")
    print(f"  训练集: {len(train_paths)} 个文件")
    print(f"  验证集: {len(val_paths)} 个文件")
    print(f"  测试集: {len(test_paths)} 个文件")
    
    # 创建数据集
    train_dataset = TLSDataset(train_paths, train_labels)
    val_dataset = TLSDataset(val_paths, val_labels)
    test_dataset = TLSDataset(test_paths, test_labels)
    
    # 创建数据加载器
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, 
                             collate_fn=collate_fn, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False,
                           collate_fn=collate_fn, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False,
                            collate_fn=collate_fn, num_workers=0)
    
    return train_loader, val_loader, test_loader
