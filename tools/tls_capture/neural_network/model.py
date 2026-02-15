"""
神经网络模型定义：混合架构（CNN + LSTM）
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from config import (
    BYTE_EMBEDDING_DIM, CNN_OUT_CHANNELS, CNN_KERNEL_SIZES,
    LSTM_HIDDEN_SIZE, LSTM_NUM_LAYERS, ATTENTION_DIM,
    FC_HIDDEN_SIZES, DROPOUT_RATE, NUM_CLASSES, MAX_MESSAGE_LENGTH
)


class ByteEmbedding(nn.Module):
    """
    字节嵌入层：将字节值（0-255）映射到嵌入向量
    """
    
    def __init__(self, embedding_dim: int = BYTE_EMBEDDING_DIM):
        super(ByteEmbedding, self).__init__()
        # 256个字节值 + 1个填充值
        self.embedding = nn.Embedding(257, embedding_dim, padding_idx=256)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: shape (batch_size, num_messages, seq_length) - 字节值
        
        Returns:
            shape (batch_size, num_messages, seq_length, embedding_dim)
        """
        # 将填充值0转换为256（padding_idx）
        x_padded = x.clone()
        x_padded[x == 0] = 256
        
        # 嵌入
        embedded = self.embedding(x_padded)  # (batch_size, num_messages, seq_length, embedding_dim)
        return embedded


class MessageEncoder(nn.Module):
    """
    消息编码器：使用CNN和LSTM编码单个消息
    """
    
    def __init__(self, embedding_dim: int = BYTE_EMBEDDING_DIM,
                 cnn_out_channels: int = CNN_OUT_CHANNELS,
                 cnn_kernel_sizes: list = CNN_KERNEL_SIZES,
                 lstm_hidden_size: int = LSTM_HIDDEN_SIZE,
                 lstm_num_layers: int = LSTM_NUM_LAYERS):
        super(MessageEncoder, self).__init__()
        
        self.embedding_dim = embedding_dim
        self.cnn_out_channels = cnn_out_channels
        self.lstm_hidden_size = lstm_hidden_size
        
        # CNN层：多个不同大小的卷积核
        self.conv_layers = nn.ModuleList()
        for kernel_size in cnn_kernel_sizes:
            conv = nn.Sequential(
                nn.Conv1d(embedding_dim, cnn_out_channels, kernel_size, padding=kernel_size//2),
                nn.ReLU(),
                nn.MaxPool1d(2)
            )
            self.conv_layers.append(conv)
        
        # 合并CNN输出
        cnn_output_dim = cnn_out_channels * len(cnn_kernel_sizes)
        
        # LSTM层
        self.lstm = nn.LSTM(
            input_size=cnn_output_dim,
            hidden_size=lstm_hidden_size,
            num_layers=lstm_num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=DROPOUT_RATE if lstm_num_layers > 1 else 0
        )
        
        # LSTM输出维度（双向）
        self.lstm_output_dim = lstm_hidden_size * 2
    
    def forward(self, embedded: torch.Tensor) -> torch.Tensor:
        """
        Args:
            embedded: shape (batch_size, num_messages, seq_length, embedding_dim)
        
        Returns:
            shape (batch_size, num_messages, lstm_output_dim)
        """
        batch_size, num_messages, seq_length, embedding_dim = embedded.shape
        
        # 重塑为 (batch_size * num_messages, seq_length, embedding_dim)
        embedded_reshaped = embedded.view(batch_size * num_messages, seq_length, embedding_dim)
        
        # 转换为 (batch_size * num_messages, embedding_dim, seq_length) 用于CNN
        embedded_conv = embedded_reshaped.transpose(1, 2)
        
        # CNN处理
        cnn_outputs = []
        for conv_layer in self.conv_layers:
            conv_out = conv_layer(embedded_conv)  # (batch_size * num_messages, cnn_out_channels, new_seq_length)
            # 全局平均池化
            pooled = F.adaptive_avg_pool1d(conv_out, 1).squeeze(-1)  # (batch_size * num_messages, cnn_out_channels)
            cnn_outputs.append(pooled)
        
        # 拼接CNN输出
        cnn_combined = torch.cat(cnn_outputs, dim=1)  # (batch_size * num_messages, cnn_output_dim)
        
        # 重塑为序列用于LSTM
        # 将CNN输出重复以形成序列（简化处理）
        seq_len = min(seq_length, 512)  # 限制序列长度
        cnn_seq = cnn_combined.unsqueeze(1).repeat(1, seq_len, 1)  # (batch_size * num_messages, seq_len, cnn_output_dim)
        
        # LSTM处理
        lstm_out, (h_n, c_n) = self.lstm(cnn_seq)
        
        # 使用最后一个时间步的输出
        message_features = lstm_out[:, -1, :]  # (batch_size * num_messages, lstm_output_dim)
        
        # 重塑回 (batch_size, num_messages, lstm_output_dim)
        message_features = message_features.view(batch_size, num_messages, self.lstm_output_dim)
        
        return message_features


class AttentionPooling(nn.Module):
    """
    注意力池化：聚合多个消息的特征
    """
    
    def __init__(self, input_dim: int, attention_dim: int = ATTENTION_DIM):
        super(AttentionPooling, self).__init__()
        self.attention_dim = attention_dim
        
        self.query = nn.Linear(input_dim, attention_dim)
        self.key = nn.Linear(input_dim, attention_dim)
        self.value = nn.Linear(input_dim, input_dim)
        self.scale = attention_dim ** -0.5
    
    def forward(self, message_features: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """
        Args:
            message_features: shape (batch_size, num_messages, feature_dim)
            mask: shape (batch_size, num_messages) - 1表示有效消息，0表示填充
        
        Returns:
            shape (batch_size, feature_dim) - 聚合后的文件特征
        """
        batch_size, num_messages, feature_dim = message_features.shape
        
        # 计算注意力权重
        Q = self.query(message_features)  # (batch_size, num_messages, attention_dim)
        K = self.key(message_features)    # (batch_size, num_messages, attention_dim)
        V = self.value(message_features)  # (batch_size, num_messages, feature_dim)
        
        # 注意力分数
        scores = torch.bmm(Q, K.transpose(1, 2)) * self.scale  # (batch_size, num_messages, num_messages)
        
        # 应用mask：将填充消息的注意力设为负无穷
        mask_expanded = mask.unsqueeze(1).expand(-1, num_messages, -1)  # (batch_size, num_messages, num_messages)
        scores = scores.masked_fill(~mask_expanded, float('-inf'))
        
        # Softmax
        attention_weights = F.softmax(scores, dim=-1)  # (batch_size, num_messages, num_messages)
        
        # 加权求和
        attended = torch.bmm(attention_weights, V)  # (batch_size, num_messages, feature_dim)
        
        # 对有效消息求平均
        mask_expanded = mask.unsqueeze(-1).expand(-1, -1, feature_dim)  # (batch_size, num_messages, feature_dim)
        attended = attended * mask_expanded.float()
        
        # 聚合：对消息维度求平均
        num_valid = mask.sum(dim=1, keepdim=True).float()  # (batch_size, 1)
        file_features = attended.sum(dim=1) / (num_valid + 1e-8)  # (batch_size, feature_dim)
        
        return file_features


class TLSClassifier(nn.Module):
    """
    完整的TLS分类模型
    """
    
    def __init__(self, embedding_dim: int = BYTE_EMBEDDING_DIM,
                 cnn_out_channels: int = CNN_OUT_CHANNELS,
                 cnn_kernel_sizes: list = CNN_KERNEL_SIZES,
                 lstm_hidden_size: int = LSTM_HIDDEN_SIZE,
                 lstm_num_layers: int = LSTM_NUM_LAYERS,
                 attention_dim: int = ATTENTION_DIM,
                 fc_hidden_sizes: list = FC_HIDDEN_SIZES,
                 dropout_rate: float = DROPOUT_RATE,
                 num_classes: int = NUM_CLASSES):
        super(TLSClassifier, self).__init__()
        
        # 字节嵌入
        self.byte_embedding = ByteEmbedding(embedding_dim)
        
        # 消息编码器
        self.message_encoder = MessageEncoder(
            embedding_dim, cnn_out_channels, cnn_kernel_sizes,
            lstm_hidden_size, lstm_num_layers
        )
        
        # 注意力池化
        lstm_output_dim = lstm_hidden_size * 2  # 双向LSTM
        self.attention_pooling = AttentionPooling(lstm_output_dim, attention_dim)
        
        # 分类头
        input_dim = lstm_output_dim
        self.fc_layers = nn.ModuleList()
        for hidden_size in fc_hidden_sizes:
            self.fc_layers.append(nn.Linear(input_dim, hidden_size))
            input_dim = hidden_size
        
        self.dropout = nn.Dropout(dropout_rate)
        self.classifier = nn.Linear(input_dim, num_classes)
    
    def forward(self, messages: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """
        Args:
            messages: shape (batch_size, num_messages, seq_length) - 字节序列
            mask: shape (batch_size, num_messages) - 有效消息mask
        
        Returns:
            shape (batch_size, num_classes) - 分类logits
        """
        # 字节嵌入
        embedded = self.byte_embedding(messages)  # (batch_size, num_messages, seq_length, embedding_dim)
        
        # 消息编码
        message_features = self.message_encoder(embedded)  # (batch_size, num_messages, lstm_output_dim)
        
        # 注意力池化
        file_features = self.attention_pooling(message_features, mask)  # (batch_size, lstm_output_dim)
        
        # 分类头
        x = file_features
        for fc_layer in self.fc_layers:
            x = fc_layer(x)
            x = F.relu(x)
            x = self.dropout(x)
        
        logits = self.classifier(x)  # (batch_size, num_classes)
        
        return logits
    
    def count_parameters(self) -> int:
        """计算模型参数量"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def create_model(**kwargs) -> TLSClassifier:
    """
    创建模型实例
    
    Args:
        **kwargs: 模型参数（可选）
    
    Returns:
        TLSClassifier实例
    """
    model = TLSClassifier(**kwargs)
    return model
