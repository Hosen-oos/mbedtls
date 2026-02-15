"""
配置文件：定义超参数、路径和模型参数
"""

import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_ROOT = PROJECT_ROOT

# 数据路径
REAL_DATA_DIR = DATA_ROOT / "results" / "tls_capture_*" / "tls_all_messages.txt"
SIMULATED_DATA_DIR = DATA_ROOT / "results_simulated"

# 模型保存路径
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)
BEST_MODEL_PATH = MODEL_DIR / "best_model.pth"

# 数据预处理参数
MAX_MESSAGE_LENGTH = 2048  # 最大消息长度（字节）
PAD_VALUE = 0  # 填充值
MAX_MESSAGES_PER_FILE = 10  # 每个文件最大消息数

# 模型参数
BYTE_EMBEDDING_DIM = 128  # 字节嵌入维度
CNN_OUT_CHANNELS = 128  # CNN输出通道数
CNN_KERNEL_SIZES = [3, 5, 7]  # CNN卷积核大小
LSTM_HIDDEN_SIZE = 256  # LSTM隐藏单元数
LSTM_NUM_LAYERS = 2  # LSTM层数
ATTENTION_DIM = 256  # 注意力机制维度
FC_HIDDEN_SIZES = [512, 256, 128]  # 全连接层隐藏单元数
DROPOUT_RATE = 0.5  # Dropout比率
NUM_CLASSES = 2  # 分类类别数（真实/模拟）

# 训练参数
BATCH_SIZE = 16  # 批次大小
LEARNING_RATE = 0.001  # 学习率
NUM_EPOCHS = 100  # 训练轮数
EARLY_STOPPING_PATIENCE = 10  # 早停耐心值
TRAIN_RATIO = 0.8  # 训练集比例
VAL_RATIO = 0.1  # 验证集比例
TEST_RATIO = 0.1  # 测试集比例

# 设备配置
DEVICE = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu"

# 随机种子
RANDOM_SEED = 42
