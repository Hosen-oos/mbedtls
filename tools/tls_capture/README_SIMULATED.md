# TLS消息模拟生成器使用说明

## 概述

`generate_tls_simulated.py` 是一个用于模拟生成TLS协议通信消息的Python脚本。它可以生成各种类型的TLS消息，包括ClientHello、ServerHello、Certificate、ChangeCipherSpec、ApplicationData等。

## 字段分类

### 可随机生成的字段

1. **随机数（Random）**
   - ClientHello和ServerHello中的32字节随机数
   - 完全随机生成

2. **会话ID（Session ID）**
   - 长度：0-32字节（随机）
   - 内容：随机字节

3. **加密套件列表（Cipher Suites）**
   - 数量：5-30个（随机）
   - 从预定义的常用套件中随机选择，不足时随机生成

4. **扩展（Extensions）**
   - Server Name Indication (SNI)
   - Supported Groups (椭圆曲线)
   - Signature Algorithms
   - 随机选择是否包含这些扩展

5. **证书数据（Certificate Data）**
   - 证书数量：1-3个（随机）
   - 每个证书长度：500-2000字节（随机）
   - 内容：随机字节（实际应为DER编码的X.509证书）

6. **应用数据（Application Data）**
   - 长度：20-1500字节（随机）
   - 内容：完全随机（模拟加密后的数据）

### 有固定值或范围的字段

1. **ContentType（内容类型）**
   - 0x14: ChangeCipherSpec
   - 0x16: Handshake
   - 0x17: ApplicationData
   - 根据消息类型自动选择

2. **Version（TLS版本）**
   - 0x0301: TLS 1.0
   - 0x0302: TLS 1.1
   - 0x0303: TLS 1.2
   - 0x0304: TLS 1.3
   - 从这些版本中随机选择

3. **HandshakeType（握手消息类型）**
   - 0x01: ClientHello
   - 0x02: ServerHello
   - 0x0b: Certificate
   - 0x0c: ServerKeyExchange
   - 0x0d: CertificateRequest
   - 0x0e: ServerHelloDone
   - 0x0f: CertificateVerify
   - 0x10: ClientKeyExchange
   - 0x14: Finished
   - 根据消息类型自动选择

4. **Length字段**
   - Record Layer Length: 2字节，根据实际消息内容计算
   - Handshake Length: 3字节，根据实际握手消息内容计算

5. **压缩方法**
   - 通常为0x00（NULL压缩）
   - 偶尔包含0x01（DEFLATE）

## 使用方法

### 基本用法

```bash
# 生成一个包含8条消息的模拟文件（默认）
python3 generate_tls_simulated.py

# 生成指定数量的消息
python3 generate_tls_simulated.py -n 10

# 指定输出文件
python3 generate_tls_simulated.py -o my_simulated.txt

# 指定输出目录
python3 generate_tls_simulated.py --output-dir results_simulated
```

### 批量生成

```bash
# 生成1000个文件，每个文件包含8条消息
./generate_batch_simulated.sh 1000 8

# 生成100个文件，每个文件包含10条消息
./generate_batch_simulated.sh 100 10
```

### 参数说明

- `-n, --num-messages`: 每个文件包含的消息数量（默认：8）
- `-o, --output`: 输出文件路径（默认：自动生成带时间戳的文件名）
- `--output-dir`: 输出目录（默认：results_simulated）

## 生成的消息类型

脚本会按照典型的TLS握手序列生成消息：

1. ClientHello（客户端 → 服务器）
2. ServerHello（服务器 → 客户端）
3. Certificate（服务器 → 客户端）
4. ChangeCipherSpec（客户端 → 服务器）
5. Finished（客户端 → 服务器，加密后）
6. Finished（服务器 → 客户端，加密后）
7. ApplicationData（服务器 → 客户端）
8. ApplicationData（客户端 → 服务器）

如果指定的消息数量超过8条，会随机生成额外的消息。

## 输出格式

生成的文件格式与真实捕获的文件格式一致，包括：

- 消息编号和方向
- 时间戳
- Record Layer信息（ContentType、Version、Length）
- Handshake Layer信息（如果适用）
- 完整的十六进制转储

## 注意事项

1. **证书数据**：生成的证书数据是随机字节，不是真实的X.509证书。如果需要真实的证书格式，需要额外处理。

2. **加密数据**：ApplicationData和Finished消息的内容是完全随机的，不包含真实的加密数据。

3. **消息完整性**：生成的消息在结构上符合TLS协议规范，但内容（除固定字段外）是随机的，不能用于实际的TLS通信。

4. **用途**：此工具主要用于：
   - 测试TLS消息解析器
   - 生成训练数据
   - 协议分析和学习
   - 性能测试

## 文件位置

- 脚本：`tools/tls_capture/generate_tls_simulated.py`
- 批量生成脚本：`tools/tls_capture/generate_batch_simulated.sh`
- 输出目录：`tools/tls_capture/results_simulated/`

## 示例

```bash
# 生成一个测试文件
cd /home/hosen/mbedtls/tools/tls_capture
python3 generate_tls_simulated.py -n 5

# 查看生成的文件
ls -lh results_simulated/

# 查看文件内容
cat results_simulated/tls_simulated_*.txt | head -50
```
