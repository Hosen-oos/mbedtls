#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TLS协议消息模拟生成器

此脚本可以模拟生成各种TLS协议消息，包括：
- ClientHello
- ServerHello
- Certificate
- ChangeCipherSpec
- ApplicationData
- Finished

字段分类：
- 可随机生成：随机数、会话ID、加密套件、扩展、证书数据、加密数据
- 固定值/范围：ContentType、Version、HandshakeType（从预定义列表选择）
"""

import os
import random
import struct
from datetime import datetime
from typing import List, Tuple, Optional

# TLS常量定义
# ContentType
CONTENT_TYPE_CHANGE_CIPHER_SPEC = 0x14
CONTENT_TYPE_ALERT = 0x21
CONTENT_TYPE_HANDSHAKE = 0x16
CONTENT_TYPE_APPLICATION_DATA = 0x17

# TLS版本
TLS_VERSION_1_0 = 0x0301
TLS_VERSION_1_1 = 0x0302
TLS_VERSION_1_2 = 0x0303
TLS_VERSION_1_3 = 0x0304

# HandshakeType
HANDSHAKE_TYPE_CLIENT_HELLO = 0x01
HANDSHAKE_TYPE_SERVER_HELLO = 0x02
HANDSHAKE_TYPE_CERTIFICATE = 0x0b
HANDSHAKE_TYPE_SERVER_KEY_EXCHANGE = 0x0c
HANDSHAKE_TYPE_CERTIFICATE_REQUEST = 0x0d
HANDSHAKE_TYPE_SERVER_HELLO_DONE = 0x0e
HANDSHAKE_TYPE_CERTIFICATE_VERIFY = 0x0f
HANDSHAKE_TYPE_CLIENT_KEY_EXCHANGE = 0x10
HANDSHAKE_TYPE_FINISHED = 0x14

# 常用加密套件（部分）
CIPHER_SUITES = [
    0x003e,  # TLS_RSA_WITH_AES_128_CBC_SHA
    0x003f,  # TLS_RSA_WITH_AES_256_CBC_SHA
    0x002f,  # TLS_RSA_WITH_AES_128_CBC_SHA256
    0x0035,  # TLS_RSA_WITH_AES_256_CBC_SHA256
    0xc02c,  # TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
    0xc02b,  # TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
    0x1301,  # TLS_AES_256_GCM_SHA384 (TLS 1.3)
    0x1302,  # TLS_AES_128_GCM_SHA256 (TLS 1.3)
    0x1303,  # TLS_CHACHA20_POLY1305_SHA256 (TLS 1.3)
]


class TLSSimulator:
    """TLS消息模拟生成器"""
    
    def __init__(self):
        self.message_count = 0
    
    def random_bytes(self, length: int) -> bytes:
        """生成随机字节"""
        return bytes([random.randint(0, 255) for _ in range(length)])
    
    def random_uint16(self) -> int:
        """生成随机16位无符号整数"""
        return random.randint(0, 65535)
    
    def random_uint24(self) -> int:
        """生成随机24位无符号整数"""
        return random.randint(0, 16777215)
    
    def put_uint16(self, value: int) -> bytes:
        """将16位整数转换为大端字节序"""
        return struct.pack('>H', value)
    
    def put_uint24(self, value: int) -> bytes:
        """将24位整数转换为大端字节序"""
        return struct.pack('>I', value)[1:]  # 去掉最高字节
    
    def generate_random(self, length: int = 32) -> bytes:
        """生成随机数（用于ClientHello/ServerHello）"""
        return self.random_bytes(length)
    
    def generate_session_id(self, length: Optional[int] = None) -> bytes:
        """生成会话ID"""
        if length is None:
            length = random.randint(0, 32)  # 0-32字节
        if length == 0:
            return b'\x00'  # 空会话ID
        return bytes([length]) + self.random_bytes(length)
    
    def generate_cipher_suites(self, count: Optional[int] = None) -> bytes:
        """生成加密套件列表"""
        if count is None:
            count = random.randint(5, 30)  # 5-30个套件
        
        suites = random.sample(CIPHER_SUITES, min(count, len(CIPHER_SUITES)))
        # 如果需要的套件数量超过可用套件，随机生成一些
        while len(suites) < count:
            suites.append(self.random_uint16())
        
        suites_bytes = b''.join([self.put_uint16(s) for s in suites])
        return self.put_uint16(len(suites_bytes)) + suites_bytes
    
    def generate_compression_methods(self) -> bytes:
        """生成压缩方法列表"""
        methods = [0x00]  # NULL压缩
        if random.random() > 0.5:
            methods.append(0x01)  # DEFLATE
        
        methods_bytes = bytes(methods)
        return bytes([len(methods_bytes)]) + methods_bytes
    
    def generate_extensions(self) -> bytes:
        """生成扩展列表（简化版）"""
        extensions = []
        
        # 随机选择一些扩展
        if random.random() > 0.3:
            # Server Name Indication (0x0000)
            server_name = b'localhost'
            ext_data = self.put_uint16(len(server_name) + 3)  # 扩展长度
            ext_data += self.put_uint16(len(server_name) + 1)  # 服务器名称列表长度
            ext_data += bytes([0x00])  # 名称类型 (DNS)
            ext_data += self.put_uint16(len(server_name))  # 名称长度
            ext_data += server_name
            extensions.append(self.put_uint16(0x0000) + ext_data)
        
        if random.random() > 0.3:
            # Supported Groups (0x000a)
            groups = [0x001d, 0x0017, 0x001e, 0x0019, 0x0018]  # 常用椭圆曲线
            selected = random.sample(groups, random.randint(1, len(groups)))
            ext_data = self.put_uint16(len(selected) * 2)
            ext_data += b''.join([self.put_uint16(g) for g in selected])
            extensions.append(self.put_uint16(0x000a) + ext_data)
        
        if random.random() > 0.3:
            # Signature Algorithms (0x000d)
            algorithms = [
                (0x04, 0x01), (0x05, 0x01), (0x06, 0x01),  # RSA
                (0x04, 0x03), (0x05, 0x03), (0x06, 0x03),  # ECDSA
            ]
            selected = random.sample(algorithms, random.randint(2, len(algorithms)))
            ext_data = self.put_uint16(len(selected) * 2)
            ext_data += b''.join([bytes([h, s]) for h, s in selected])
            extensions.append(self.put_uint16(0x000d) + ext_data)
        
        if len(extensions) == 0:
            return b'\x00\x00'  # 无扩展
        
        extensions_data = b''.join(extensions)
        return self.put_uint16(len(extensions_data)) + extensions_data
    
    def generate_client_hello(self, version: int = TLS_VERSION_1_2, 
                              target_length: Optional[int] = None) -> bytes:
        """生成ClientHello消息"""
        # 客户端版本（最高支持的版本）
        client_version = version
        
        # 随机数（32字节）
        random_data = self.generate_random(32)
        
        # 会话ID（通常为空或较短）
        session_id = self.generate_session_id(random.randint(0, 10))
        
        # 加密套件列表（生成更多套件以增加长度，真实情况通常有20-30个）
        if target_length is None:
            cipher_suites = self.generate_cipher_suites(random.randint(20, 30))
        else:
            # 根据目标长度计算需要的套件数量
            # 基础开销：版本(2) + 随机数(32) + 会话ID(1-33) + 压缩(2) + 扩展长度(2) = 约40-70字节
            # Handshake头部(4) + Record头部(5) = 9字节
            # 扩展通常约100-150字节
            available = target_length - 9 - 2 - 32 - len(session_id) - 2 - 150  # 预留扩展空间
            num_suites = max(15, available // 2)  # 每个套件2字节
            cipher_suites = self.generate_cipher_suites(num_suites)
        
        # 压缩方法
        compression_methods = self.generate_compression_methods()
        
        # 扩展（生成更多扩展以增加长度）
        extensions = self.generate_extensions()
        # 如果目标长度较大，添加更多扩展数据
        if target_length is not None:
            current_len = 2 + 32 + len(session_id) + len(cipher_suites) + len(compression_methods) + len(extensions)
            needed = target_length - 9 - current_len  # 9 = Record(5) + Handshake(4)
            if needed > 50:
                # 添加额外的扩展数据
                additional_ext = self.random_bytes(min(needed - 10, 200))
                extensions = extensions[:-2] + self.put_uint16(len(extensions[2:] + additional_ext)) + extensions[2:] + additional_ext
        
        # 组装ClientHello消息体
        hello_body = (
            struct.pack('>H', client_version) +  # 客户端版本
            random_data +                        # 随机数
            session_id +                         # 会话ID
            cipher_suites +                     # 加密套件列表
            compression_methods +                 # 压缩方法
            extensions                           # 扩展
        )
        
        # Handshake层头部
        handshake_header = (
            bytes([HANDSHAKE_TYPE_CLIENT_HELLO]) +
            self.put_uint24(len(hello_body))
        )
        
        # Record层
        record_body = handshake_header + hello_body
        record_length = len(record_body)
        
        record_header = (
            bytes([CONTENT_TYPE_HANDSHAKE]) +
            struct.pack('>H', version) +  # Record层版本（通常是TLS 1.0）
            self.put_uint16(record_length)
        )
        
        return record_header + record_body
    
    def generate_server_hello(self, version: int = TLS_VERSION_1_2) -> bytes:
        """生成ServerHello消息（单独的Record）"""
        # 服务器版本
        server_version = version
        
        # 随机数（32字节）
        random_data = self.generate_random(32)
        
        # 会话ID（通常与ClientHello相同或为空）
        session_id = self.generate_session_id(random.randint(0, 32))
        
        # 选中的加密套件
        selected_cipher = random.choice(CIPHER_SUITES)
        cipher_suite = self.put_uint16(selected_cipher)
        
        # 压缩方法（通常为NULL）
        compression_method = bytes([0x00])
        
        # 扩展（可选）
        extensions = self.generate_extensions()
        
        # 组装ServerHello消息体
        hello_body = (
            struct.pack('>H', server_version) +  # 服务器版本
            random_data +                        # 随机数
            session_id +                        # 会话ID
            cipher_suite +                       # 选中的加密套件
            compression_method +                 # 压缩方法
            extensions                            # 扩展
        )
        
        # Handshake层头部
        handshake_header = (
            bytes([HANDSHAKE_TYPE_SERVER_HELLO]) +
            self.put_uint24(len(hello_body))
        )
        
        # Record层
        record_body = handshake_header + hello_body
        record_length = len(record_body)
        
        record_header = (
            bytes([CONTENT_TYPE_HANDSHAKE]) +
            struct.pack('>H', version) +
            self.put_uint16(record_length)
        )
        
        return record_header + record_body
    
    def generate_server_hello_with_certificate(self, version: int = TLS_VERSION_1_2, 
                                                target_total_length: Optional[int] = None) -> bytes:
        """生成ServerHello + Certificate + ServerKeyExchange等打包在一起的消息（模拟真实情况）"""
        # 生成ServerHello Record
        server_hello = self.generate_server_hello(version)
        server_hello_len = len(server_hello)
        
        # 计算Certificate Record的目标长度
        if target_total_length is None:
            target_total_length = random.randint(1000, 1500)
        
        # Certificate Record需要的大小 = 总长度 - ServerHello长度
        cert_record_target = target_total_length - server_hello_len
        
        # 生成Certificate Record
        # Record头部(5) + Handshake头部(4) + 证书链长度(3) = 12字节开销
        cert_data_size = max(100, cert_record_target - 12)
        
        # 生成1-2个证书
        num_certs = 1 if cert_data_size < 1500 else 2
        if num_certs == 1:
            cert_lengths = [cert_data_size]
        else:
            cert_lengths = [cert_data_size // 2, cert_data_size - cert_data_size // 2]
        
        certs_data = b''
        for cert_length in cert_lengths:
            cert_data = self.random_bytes(cert_length)
            certs_data += self.put_uint24(cert_length) + cert_data
        
        # Certificate消息体：证书链总长度(3字节) + 证书列表
        cert_chain_length = len(certs_data)
        cert_body = self.put_uint24(cert_chain_length) + certs_data
        
        # Handshake层头部
        cert_handshake_header = (
            bytes([HANDSHAKE_TYPE_CERTIFICATE]) +
            self.put_uint24(len(cert_body))
        )
        
        # Record层
        cert_record_body = cert_handshake_header + cert_body
        cert_record_length = len(cert_record_body)
        
        cert_record_header = (
            bytes([CONTENT_TYPE_HANDSHAKE]) +
            struct.pack('>H', version) +
            self.put_uint16(cert_record_length)
        )
        
        cert_record = cert_record_header + cert_record_body
        
        # 返回打包的多个Record
        return server_hello + cert_record
    
    def generate_certificate(self, version: int = TLS_VERSION_1_2, 
                             total_length: Optional[int] = None) -> bytes:
        """生成Certificate消息（简化版，包含模拟证书数据）"""
        # 如果指定了总长度，调整证书大小
        if total_length is None:
            # 生成1-2个证书，每个证书约600-1000字节
            num_certs = random.randint(1, 2)
            cert_lengths = [random.randint(600, 1000) for _ in range(num_certs)]
        else:
            # 根据总长度计算证书大小
            # Record头部(5) + Handshake头部(4) + 证书链长度(3) = 12字节
            # 剩余用于证书数据
            available = total_length - 12
            num_certs = 1 if available < 1500 else 2
            if num_certs == 1:
                cert_lengths = [available]
            else:
                cert_lengths = [available // 2, available - available // 2]
        
        certs_data = b''
        for cert_length in cert_lengths:
            cert_data = self.random_bytes(cert_length)
            certs_data += self.put_uint24(cert_length) + cert_data
        
        # Certificate消息体：证书链总长度(3字节) + 证书列表
        cert_chain_length = len(certs_data)
        cert_body = self.put_uint24(cert_chain_length) + certs_data
        
        # Handshake层头部
        handshake_header = (
            bytes([HANDSHAKE_TYPE_CERTIFICATE]) +
            self.put_uint24(len(cert_body))
        )
        
        # Record层
        record_body = handshake_header + cert_body
        record_length = len(record_body)
        
        record_header = (
            bytes([CONTENT_TYPE_HANDSHAKE]) +
            struct.pack('>H', version) +
            self.put_uint16(record_length)
        )
        
        return record_header + record_body
    
    def generate_change_cipher_spec(self, version: int = TLS_VERSION_1_2) -> bytes:
        """生成ChangeCipherSpec消息"""
        # ChangeCipherSpec消息体（固定为0x01）
        ccs_body = bytes([0x01])
        
        # Record层
        record_header = (
            bytes([CONTENT_TYPE_CHANGE_CIPHER_SPEC]) +
            struct.pack('>H', version) +
            self.put_uint16(len(ccs_body))
        )
        
        return record_header + ccs_body
    
    def generate_application_data(self, version: int = TLS_VERSION_1_2, 
                                  length: Optional[int] = None) -> bytes:
        """生成ApplicationData消息（加密后的应用数据）"""
        if length is None:
            length = random.randint(20, 1500)  # 20-1500字节
        
        # 应用数据（加密后，看起来是随机的）
        app_data = self.random_bytes(length)
        
        # Record层
        record_header = (
            bytes([CONTENT_TYPE_APPLICATION_DATA]) +
            struct.pack('>H', version) +
            self.put_uint16(length)
        )
        
        return record_header + app_data
    
    def generate_finished(self, version: int = TLS_VERSION_1_2) -> bytes:
        """生成Finished消息（加密后的）"""
        # Finished消息包含验证数据（通常是12字节的MAC，但加密后可能更长）
        # 这里生成加密后的Finished消息（作为ApplicationData发送）
        finished_length = random.randint(12, 64)
        finished_data = self.random_bytes(finished_length)
        
        # Finished消息在TLS 1.2中通常作为ApplicationData发送（因为已经加密）
        return self.generate_application_data(version, finished_length)
    
    def hex_dump(self, data: bytes, offset: int = 0) -> str:
        """生成十六进制转储"""
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join([f'{b:02x}' for b in chunk])
            ascii_str = ''.join([chr(b) if 32 <= b < 127 else '.' for b in chunk])
            lines.append(f'{offset+i:04x}: {hex_str:<48} |{ascii_str}|')
        return '\n'.join(lines)
    
    def parse_record_layer(self, data: bytes) -> dict:
        """解析Record层头部"""
        if len(data) < 5:
            return None
        
        content_type = data[0]
        version = struct.unpack('>H', data[1:3])[0]
        length = struct.unpack('>H', data[3:5])[0]
        
        ct_names = {
            CONTENT_TYPE_CHANGE_CIPHER_SPEC: 'ChangeCipherSpec',
            CONTENT_TYPE_ALERT: 'Alert',
            CONTENT_TYPE_HANDSHAKE: 'Handshake',
            CONTENT_TYPE_APPLICATION_DATA: 'ApplicationData'
        }
        
        info = {
            'content_type': content_type,
            'content_type_name': ct_names.get(content_type, 'Unknown'),
            'version': f'0x{version:04x}',
            'length': length
        }
        
        # 解析Handshake层（如果存在）
        if content_type == CONTENT_TYPE_HANDSHAKE and len(data) >= 9:
            handshake_type = data[5]
            handshake_len = struct.unpack('>I', b'\x00' + data[6:9])[0]
            
            hs_names = {
                HANDSHAKE_TYPE_CLIENT_HELLO: 'ClientHello',
                HANDSHAKE_TYPE_SERVER_HELLO: 'ServerHello',
                HANDSHAKE_TYPE_CERTIFICATE: 'Certificate',
                HANDSHAKE_TYPE_SERVER_KEY_EXCHANGE: 'ServerKeyExchange',
                HANDSHAKE_TYPE_CERTIFICATE_REQUEST: 'CertificateRequest',
                HANDSHAKE_TYPE_SERVER_HELLO_DONE: 'ServerHelloDone',
                HANDSHAKE_TYPE_CERTIFICATE_VERIFY: 'CertificateVerify',
                HANDSHAKE_TYPE_CLIENT_KEY_EXCHANGE: 'ClientKeyExchange',
                HANDSHAKE_TYPE_FINISHED: 'Finished'
            }
            
            info['handshake_type'] = handshake_type
            info['handshake_type_name'] = hs_names.get(handshake_type, 'Unknown')
            info['handshake_length'] = handshake_len
        
        return info
    
    def generate_message(self, msg_type: str, direction: str = 'Client->Server',
                        version: int = TLS_VERSION_1_2) -> Tuple[bytes, dict]:
        """生成指定类型的消息"""
        self.message_count += 1
        
        msg_generators = {
            'ClientHello': self.generate_client_hello,
            'ServerHello': self.generate_server_hello,
            'Certificate': self.generate_certificate,
            'ChangeCipherSpec': self.generate_change_cipher_spec,
            'ApplicationData': self.generate_application_data,
            'Finished': self.generate_finished,
        }
        
        if msg_type not in msg_generators:
            raise ValueError(f"Unknown message type: {msg_type}")
        
        # 生成消息
        if msg_type == 'ApplicationData':
            data = msg_generators[msg_type](version, random.randint(20, 1500))
        else:
            data = msg_generators[msg_type](version)
        
        # 解析消息信息
        info = self.parse_record_layer(data)
        info['direction'] = direction
        info['message_type'] = msg_type
        info['timestamp'] = datetime.now()
        
        return data, info
    
    def format_message(self, data: bytes, info: dict, msg_num: int) -> str:
        """格式化消息为文本格式（与捕获文件格式一致）"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"Message #{msg_num}: {info['direction']}")
        lines.append(f"Time: {info['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Length: {len(data)} bytes")
        lines.append("Record Layer:")
        lines.append(f"  ContentType: 0x{info['content_type']:02x} ({info['content_type_name']})")
        lines.append(f"  Version: {info['version']}")
        lines.append(f"  Length: {info['length']} bytes")
        
        if 'handshake_type' in info:
            lines.append("Handshake Layer:")
            lines.append(f"  HandshakeType: 0x{info['handshake_type']:02x} ({info['handshake_type_name']})")
            lines.append(f"  Length: {info['handshake_length']} bytes")
        
        lines.append("-" * 50)
        lines.append("Hex Dump:")
        lines.append(self.hex_dump(data))
        lines.append("=" * 50)
        lines.append("")
        
        return '\n'.join(lines)


def generate_simulated_capture(num_messages: int = 8, output_file: str = None):
    """生成模拟的TLS捕获文件"""
    simulator = TLSSimulator()
    
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"tls_simulated_{timestamp}.txt"
    
    # 生成典型的TLS握手序列（基于真实捕获格式）
    # Message #1: ClientHello (~297 bytes)
    # Message #2: ServerHello + Certificate打包 (~1000-1500 bytes)
    # Message #3: ChangeCipherSpec + Finished (~80 bytes)
    # Message #4: Finished (加密后，~38 bytes)
    # Message #5-7: ApplicationData (各种大小)
    
    # 根据真实捕获：ClientHello使用0x0301，后续消息使用协商后的版本（通常是0x0303）
    client_version = TLS_VERSION_1_0  # ClientHello总是使用0x0301
    negotiated_version = TLS_VERSION_1_2  # 协商后的版本通常是TLS 1.2 (0x0303)
    
    messages_data = []
    
    # Message #1: ClientHello (~297 bytes) - 使用0x0301
    client_hello = simulator.generate_client_hello(client_version, target_length=random.randint(290, 305))
    info = simulator.parse_record_layer(client_hello)
    info['direction'] = 'Client->Server'
    info['message_type'] = 'ClientHello'
    info['timestamp'] = datetime.now()
    messages_data.append((client_hello, info))
    
    # Message #2: ServerHello + Certificate打包（模拟真实情况，约1000-1500字节）
    # 从Message #2开始使用协商后的版本（0x0303）
    target_length = random.randint(1000, 1500)
    server_hello_cert = simulator.generate_server_hello_with_certificate(negotiated_version, target_length)
    
    info = simulator.parse_record_layer(server_hello_cert)
    info['direction'] = 'Server->Client'
    info['message_type'] = 'ServerHello+Certificate'
    info['timestamp'] = datetime.now()
    messages_data.append((server_hello_cert, info))
    
    # Message #3: ChangeCipherSpec + Finished（加密后，约80字节）
    # 使用协商后的版本
    ccs = simulator.generate_change_cipher_spec(negotiated_version)  # 5字节
    # Finished加密后约70-75字节，总共约80字节
    finished_size = random.randint(70, 75)
    finished_encrypted = simulator.generate_application_data(negotiated_version, finished_size)
    combined = ccs + finished_encrypted
    
    info = simulator.parse_record_layer(combined)
    info['direction'] = 'Client->Server'
    info['message_type'] = 'ChangeCipherSpec+Finished'
    info['timestamp'] = datetime.now()
    messages_data.append((combined, info))
    
    # Message #4: Finished（加密后，小，约38字节）
    # 使用协商后的版本
    finished_small = simulator.generate_application_data(negotiated_version, random.randint(30, 45))
    info = simulator.parse_record_layer(finished_small)
    info['direction'] = 'Client->Server'
    info['message_type'] = 'Finished'
    info['timestamp'] = datetime.now()
    messages_data.append((finished_small, info))
    
    # Message #5-7: ApplicationData（各种大小）
    # 根据原始文件：Message #5和#6都是255字节，Message #7是5199字节
    # 使用协商后的版本
    app_data_sizes = [255, 255, random.randint(2000, 5500)]  # 模拟真实大小
    directions_5_7 = ['Server->Client', 'Server->Client', 'Server->Client']  # 原始文件中都是Server->Client
    
    for i, size in enumerate(app_data_sizes[:min(3, num_messages-4)]):
        app_data = simulator.generate_application_data(negotiated_version, size)
        info = simulator.parse_record_layer(app_data)
        info['direction'] = directions_5_7[i] if i < len(directions_5_7) else ('Server->Client' if len(messages_data) % 2 == 0 else 'Client->Server')
        info['message_type'] = 'ApplicationData'
        info['timestamp'] = datetime.now()
        messages_data.append((app_data, info))
    
    # Message #8: 最后一个ApplicationData（小，约24字节，Client->Server）
    # 使用协商后的版本
    if num_messages >= 8:
        app_data_small = simulator.generate_application_data(negotiated_version, random.randint(20, 30))
        info = simulator.parse_record_layer(app_data_small)
        info['direction'] = 'Client->Server'
        info['message_type'] = 'ApplicationData'
        info['timestamp'] = datetime.now()
        messages_data.append((app_data_small, info))
    
    # 生成消息
    output_lines = []
    output_lines.append("TLS Message Capture - Simulated Messages")
    output_lines.append("=" * 50)
    output_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append("Note: This is a simulated capture for testing purposes")
    output_lines.append("=" * 50)
    output_lines.append("")
    
    for i, (data, info) in enumerate(messages_data, 1):
        formatted = simulator.format_message(data, info, i)
        output_lines.append(formatted)
    
    # 写入文件
    output_content = '\n'.join(output_lines)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output_content)
    
    print(f"✓ 已生成 {num_messages} 条模拟TLS消息")
    print(f"  文件: {output_file}")
    print(f"  大小: {len(output_content)} 字节")
    
    return output_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TLS协议消息模拟生成器')
    parser.add_argument('-n', '--num-messages', type=int, default=8,
                       help='生成的消息数量（默认：8）')
    parser.add_argument('-o', '--output', type=str, default=None,
                       help='输出文件路径（默认：自动生成）')
    parser.add_argument('--output-dir', type=str, default='results_simulated',
                       help='输出目录（默认：results_simulated）')
    parser.add_argument('--id', type=int, default=None,
                       help='文件编号（用于批量生成时避免文件名冲突）')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 生成输出文件路径
    if args.output is None:
        if args.id is not None:
            # 使用编号命名
            args.output = os.path.join(args.output_dir, f"tls_simulated_{args.id:04d}.txt")
        else:
            # 使用时间戳命名（兼容单次生成）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # 包含毫秒
            args.output = os.path.join(args.output_dir, f"tls_simulated_{timestamp}.txt")
    else:
        args.output = os.path.join(args.output_dir, args.output)
    
    # 生成模拟消息
    generate_simulated_capture(args.num_messages, args.output)


if __name__ == '__main__':
    main()
