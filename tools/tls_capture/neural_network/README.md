# TLS消息分类神经网络

使用深度学习模型区分真实捕获的TLS消息和模拟生成的TLS消息。

## 项目结构

```
neural_network/
├── data_loader.py          # 数据加载和预处理
├── model.py                # 神经网络模型定义
├── train.py               # 训练脚本
├── predict.py              # 预测脚本
├── utils.py                # 工具函数
├── config.py               # 配置文件
├── requirements.txt        # Python依赖
├── models/                 # 模型保存目录
└── README.md               # 使用说明
```

## 环境要求

- Python 3.8+
- PyTorch 2.0+
- 其他依赖见 `requirements.txt`

## 安装

```bash
cd tools/tls_capture/neural_network
pip install -r requirements.txt
```

## 模型架构

本模型采用混合架构（CNN + LSTM + 注意力机制）：

1. **Byte Embedding**: 将字节值（0-255）映射到嵌入向量
2. **CNN层**: 使用多个不同大小的卷积核捕获局部字节模式
3. **LSTM层**: 双向LSTM捕获序列的长期依赖关系
4. **注意力池化**: 聚合文件中的多个消息特征
5. **分类头**: 全连接层进行二分类（真实/模拟）

### 模型参数

- 字节嵌入维度: 128
- CNN输出通道数: 128
- CNN卷积核大小: [3, 5, 7]
- LSTM隐藏单元: 256（双向）
- LSTM层数: 2
- 全连接层: [512, 256, 128]
- Dropout: 0.5

## 使用方法

### 1. 训练模型

```bash
python train.py
```

可选参数：
- `--real-data-pattern`: 真实数据文件模式（glob模式），默认从config.py读取
- `--simulated-data-dir`: 模拟数据目录，默认从config.py读取
- `--batch-size`: 批次大小，默认16
- `--learning-rate`: 学习率，默认0.001
- `--num-epochs`: 训练轮数，默认100
- `--early-stopping-patience`: 早停耐心值，默认10
- `--model-save-path`: 模型保存路径
- `--seed`: 随机种子，默认42

示例：
```bash
python train.py --batch-size 32 --learning-rate 0.0005 --num-epochs 50
```

### 2. 预测单个文件

```bash
python predict.py <文件路径>
```

可选参数：
- `--model-path`: 模型文件路径，默认 `models/best_model.pth`
- `--device`: 设备（cpu/cuda），默认从config.py读取

示例：
```bash
# 预测真实数据文件
python predict.py ../results/tls_capture_20260131_135313/tls_all_messages.txt

# 预测模拟数据文件
python predict.py ../results_simulated/tls_simulated_0001.txt

# 使用指定模型
python predict.py <文件路径> --model-path models/best_model.pth
```

### 3. 查看训练历史

训练完成后，会在 `models/` 目录下生成：
- `best_model.pth`: 最佳模型权重
- `training_history.json`: 训练历史数据
- `training_curves.png`: 训练曲线图

## 数据格式

### 输入数据格式

模型期望的输入是TLS消息捕获文件，格式如下：

```
Message #1: Client->Server
Time: 2026-01-31 13:53:19
Length: 297 bytes
Record Layer:
  ContentType: 0x16 (Handshake)
  Version: 0x0301
  Length: 292 bytes
Handshake Layer:
  HandshakeType: 0x01 (ClientHello)
  Length: 288 bytes
--------------------------------------------------
Hex Dump:
0000: 16 03 01 01 24 01 00 01 20 03 03 24 f0 4a 2e 33  |....$... ..$.J.3|
...
```

### 数据预处理

- 从Hex Dump中提取字节序列
- 每个消息填充或截断到固定长度（默认2048字节）
- 每个文件最多处理10个消息
- 短消息用0填充，长消息截断

## 配置说明

主要配置在 `config.py` 中：

- **数据路径**: `REAL_DATA_DIR`, `SIMULATED_DATA_DIR`
- **模型参数**: 嵌入维度、CNN/LSTM参数等
- **训练参数**: 批次大小、学习率、训练轮数等
- **数据划分**: 训练集/验证集/测试集比例（默认80%/10%/10%）

## 性能指标

模型训练完成后会输出：
- 训练准确率
- 验证准确率
- 损失值
- 其他分类指标（精确率、召回率、F1分数）

## 预期性能

- 训练准确率: >90%
- 验证准确率: >85%
- 测试准确率: >80%

## 注意事项

1. **数据量**: 确保有足够的数据（建议每个类别至少1000个文件）
2. **GPU**: 如果有GPU，会自动使用CUDA加速训练
3. **内存**: 批次大小根据可用内存调整
4. **早停**: 如果验证损失连续10个epoch不下降，训练会自动停止

## 故障排除

### 问题：找不到数据文件

确保数据路径配置正确：
- 检查 `config.py` 中的 `REAL_DATA_DIR` 和 `SIMULATED_DATA_DIR`
- 使用glob模式匹配真实数据文件

### 问题：内存不足

- 减小批次大小（`--batch-size`）
- 减小最大消息长度（在 `config.py` 中修改 `MAX_MESSAGE_LENGTH`）

### 问题：训练不收敛

- 调整学习率（尝试更小的值，如0.0001）
- 增加训练轮数
- 检查数据质量和标签是否正确

## 扩展功能

### 评估测试集

可以修改 `train.py` 添加测试集评估：

```python
from utils import evaluate_model, print_evaluation_results

# 在训练后添加
test_results = evaluate_model(model, test_loader, device)
print_evaluation_results(test_results, "测试集")
```

### 批量预测

可以编写脚本批量预测多个文件：

```python
from predict import load_model, predict_file
from pathlib import Path

model = load_model(Path("models/best_model.pth"), device)
for file_path in file_list:
    result = predict_file(model, file_path, device)
    print(f"{file_path}: {result['class_name']} ({result['confidence']:.2%})")
```

## 许可证

本项目为mbedTLS项目的一部分。
