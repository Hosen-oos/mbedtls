# TLS消息捕获工具使用说明

本工具用于捕获TLS握手过程中的所有消息并保存到文件。

## 方法1：使用tcpdump（推荐）

这是最准确的方法，可以捕获网络层传输的所有原始数据。

### 步骤：

1. **编译mbedtls程序**（如果还没有编译）：
```bash
cd /home/hosen/mbedtls
make -j4
```

2. **在一个终端启动服务器**：
```bash
cd programs/ssl
./ssl_server
```

3. **在另一个终端启动tcpdump捕获**：
```bash
sudo tcpdump -i lo -w tls_capture.pcap port 4433
```

4. **在第三个终端运行客户端**：
```bash
cd programs/ssl
./ssl_client1
```

5. **停止tcpdump**（按Ctrl+C）

6. **查看捕获的数据**：
```bash
# 使用tshark查看（如果安装了）
tshark -r tls_capture.pcap -V > tls_messages.txt

# 或者使用wireshark
wireshark tls_capture.pcap
```

## 方法2：使用自定义捕获程序

### 编译捕获工具：

```bash
cd /home/hosen/mbedtls

# 编译简单客户端捕获工具
gcc -o capture_client capture_tls_simple.c \
    -I./include -I./library \
    -L./library -lmbedtls -lmbedx509 -lmbedcrypto \
    -lpthread -ldl

# 或者使用CMake（如果项目使用CMake）
```

### 运行：

1. **启动服务器**（使用现有的ssl_server）：
```bash
cd programs/ssl
./ssl_server > server.log 2>&1 &
SERVER_PID=$!
```

2. **运行捕获客户端**：
```bash
./capture_client tls_all_messages.txt
```

3. **停止服务器**：
```bash
kill $SERVER_PID
```

## 方法3：使用自动化脚本

运行提供的脚本：

```bash
./run_tls_capture.sh
```

这个脚本会：
- 自动启动服务器和客户端
- 使用tcpdump捕获网络流量（如果可用）
- 保存所有消息到时间戳目录中

## 输出文件说明

捕获的文件包含：

1. **tls_all_messages.txt** 或 **tls_client_messages.txt** / **tls_server_messages.txt**
   - 所有TLS消息的十六进制转储
   - 包含记录层和握手层的解析信息
   - 每条消息都有时间戳和方向标识

2. **tls_debug.log**
   - mbedtls的调试日志
   - 包含握手过程的详细信息

3. **tls_traffic.pcap**（如果使用tcpdump）
   - 原始网络数据包
   - 可以用Wireshark或tshark打开分析

## 消息格式说明

每条消息包含：
- 消息编号和方向（Client->Server 或 Server->Client）
- 时间戳
- 记录层信息（ContentType, Version, Length）
- 握手层信息（HandshakeType, Length）
- 完整的十六进制转储
- ASCII字符显示（如果可打印）

## 注意事项

1. 如果使用tcpdump，需要root权限
2. 确保端口4433没有被其他程序占用
3. 如果编译失败，检查是否已正确编译mbedtls库
4. 某些消息（如Finished）是加密的，会显示为加密数据
