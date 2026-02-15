# TLS消息捕获工具

本工具用于捕获TLS握手过程中的所有消息并保存到文件，方便分析TLS协议的认证过程。

## 目录结构

```
tools/tls_capture/
├── tls_proxy.py          # Python代理工具（主要工具）
├── run_test.sh           # 自动化测试脚本
├── capture_client.c      # C语言客户端工具（可选）
├── Makefile              # C语言工具编译配置
├── docs/                 # 文档目录
│   ├── 使用说明.md      # 中文详细说明
│   ├── 捕获结果说明.md  # 结果格式说明
│   └── ...              # 其他文档
├── results/              # 捕获结果目录
│   └── tls_capture_*    # 时间戳命名的捕获结果
└── README.md            # 本文件
```

## 快速开始

### 方法1：使用自动化脚本（推荐）

```bash
cd tools/tls_capture
./run_test.sh
```

这将：
1. 自动创建测试证书
2. 启动TLS服务器
3. 运行客户端测试
4. 捕获所有消息到 `results/` 目录

### 方法2：手动运行

1. **启动代理**（终端1）：
```bash
cd tools/tls_capture
python3 tls_proxy.py 8443 localhost 4433
```

2. **启动TLS服务器**（终端2）：
```bash
# 使用openssl
openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 365 -nodes -subj "/CN=localhost"
openssl s_server -accept 4433 -cert server.crt -key server.key -www
```

3. **运行客户端**（终端3）：
```bash
openssl s_client -connect localhost:8443
```

## 输出位置

- 使用 `run_test.sh`：消息保存在 `results/tls_capture_YYYYMMDD_HHMMSS/` 目录
- 使用 `tls_proxy.py`：消息保存在当前目录的 `tls_all_messages.txt`

## 查看结果

```bash
# 查看最新的捕获结果
ls -lt results/ | head -2

# 查看消息
cat results/tls_capture_*/tls_all_messages.txt

# 查看特定消息类型
grep -A 50 "ClientHello" results/tls_capture_*/tls_all_messages.txt
```

## 文档

详细文档请查看 `docs/` 目录：
- `docs/使用说明.md` - 中文详细使用说明
- `docs/捕获结果说明.md` - 结果格式说明
- `docs/README.md` - 文档索引

## 消息格式

每条消息包含：
- 消息编号和方向（Client->Server 或 Server->Client）
- 时间戳
- 记录层信息（ContentType, Version, Length）
- 握手层信息（HandshakeType, Length）
- 完整的十六进制转储
- ASCII字符显示

## 注意事项

1. 端口冲突：确保端口8443和4433没有被占用
2. 权限：不需要root权限（与tcpdump不同）
3. 消息格式：所有消息都是原始网络传输格式
4. 加密状态：握手阶段是明文，ApplicationData是加密的

## 编译C语言工具（可选）

如果需要使用C语言工具：

```bash
cd tools/tls_capture
make -f Makefile capture_client
```

需要先编译mbedtls库。
