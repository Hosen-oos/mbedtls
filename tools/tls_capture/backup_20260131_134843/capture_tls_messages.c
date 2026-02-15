/*
 * TLS Message Capture Tool
 * 
 * This tool captures all TLS messages exchanged between client and server
 * and saves them to files for analysis.
 */

#define MBEDTLS_ALLOW_PRIVATE_ACCESS

#include "mbedtls/net_sockets.h"
#include "mbedtls/ssl.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/error.h"
#include "mbedtls/certs.h"
#include "mbedtls/x509.h"
#include "mbedtls/pk.h"
#include "mbedtls/debug.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

#define SERVER_PORT "4433"
#define CLIENT_PORT "4434"
#define MAX_MESSAGE_SIZE 16384

// 消息捕获结构
typedef struct {
    FILE *file;
    int message_count;
    char direction;  // 'C' for client, 'S' for server
} message_capture_t;

static message_capture_t client_capture = {NULL, 0, 'C'};
static message_capture_t server_capture = {NULL, 0, 'S'};

// 保存消息到文件
static void save_message(message_capture_t *capture, 
                        const unsigned char *data, 
                        size_t len,
                        const char *msg_type)
{
    if (capture->file == NULL) {
        return;
    }
    
    capture->message_count++;
    
    fprintf(capture->file, "\n");
    fprintf(capture->file, "========================================\n");
    fprintf(capture->file, "Message #%d: %s (%c->%c)\n", 
            capture->message_count, msg_type,
            capture->direction, 
            capture->direction == 'C' ? 'S' : 'C');
    fprintf(capture->file, "Length: %zu bytes\n", len);
    fprintf(capture->file, "Time: %ld\n", (long)time(NULL));
    fprintf(capture->file, "----------------------------------------\n");
    fprintf(capture->file, "Hex Dump:\n");
    
    // 十六进制输出
    for (size_t i = 0; i < len; i++) {
        if (i % 16 == 0) {
            fprintf(capture->file, "%04zx: ", i);
        }
        fprintf(capture->file, "%02x ", data[i]);
        if (i % 16 == 15 || i == len - 1) {
            // 打印ASCII
            size_t start = (i / 16) * 16;
            size_t end = (i < start + 16) ? i : start + 15;
            for (size_t j = end + 1; j < start + 16; j++) {
                fprintf(capture->file, "   ");
            }
            fprintf(capture->file, " |");
            for (size_t j = start; j <= end; j++) {
                char c = (data[j] >= 32 && data[j] < 127) ? data[j] : '.';
                fprintf(capture->file, "%c", c);
            }
            fprintf(capture->file, "|\n");
        }
    }
    
    fprintf(capture->file, "----------------------------------------\n");
    
    // 解析记录层头部
    if (len >= 5) {
        unsigned char content_type = data[0];
        unsigned char version_major = data[1];
        unsigned char version_minor = data[2];
        unsigned short length = (data[3] << 8) | data[4];
        
        fprintf(capture->file, "Record Layer:\n");
        fprintf(capture->file, "  ContentType: 0x%02x ", content_type);
        switch (content_type) {
            case 20: fprintf(capture->file, "(ChangeCipherSpec)\n"); break;
            case 21: fprintf(capture->file, "(Alert)\n"); break;
            case 22: fprintf(capture->file, "(Handshake)\n"); break;
            case 23: fprintf(capture->file, "(ApplicationData)\n"); break;
            default: fprintf(capture->file, "(Unknown)\n"); break;
        }
        fprintf(capture->file, "  Version: 0x%02x%02x ", version_major, version_minor);
        if (version_major == 0x03) {
            if (version_minor == 0x03) fprintf(capture->file, "(TLS 1.2)\n");
            else if (version_minor == 0x04) fprintf(capture->file, "(TLS 1.3)\n");
            else fprintf(capture->file, "\n");
        } else {
            fprintf(capture->file, "\n");
        }
        fprintf(capture->file, "  Length: %u bytes\n", length);
        
        // 解析握手层
        if (content_type == 22 && len >= 9) {
            unsigned char handshake_type = data[5];
            unsigned long handshake_len = ((unsigned long)data[6] << 16) |
                                         ((unsigned long)data[7] << 8) |
                                         (unsigned long)data[8];
            
            fprintf(capture->file, "Handshake Layer:\n");
            fprintf(capture->file, "  HandshakeType: 0x%02x ", handshake_type);
            switch (handshake_type) {
                case 1: fprintf(capture->file, "(ClientHello)\n"); break;
                case 2: fprintf(capture->file, "(ServerHello)\n"); break;
                case 11: fprintf(capture->file, "(Certificate)\n"); break;
                case 13: fprintf(capture->file, "(CertificateRequest)\n"); break;
                case 15: fprintf(capture->file, "(CertificateVerify)\n"); break;
                case 20: fprintf(capture->file, "(Finished)\n"); break;
                default: fprintf(capture->file, "(Unknown)\n"); break;
            }
            fprintf(capture->file, "  Length: %lu bytes\n", handshake_len);
        }
    }
    
    fprintf(capture->file, "========================================\n");
    fflush(capture->file);
}

// 自定义发送函数 - 捕获客户端发送的消息
static int client_send(void *ctx, const unsigned char *buf, size_t len)
{
    mbedtls_net_context *net_ctx = (mbedtls_net_context *)ctx;
    save_message(&client_capture, buf, len, "Client->Server");
    return mbedtls_net_send(net_ctx, buf, len);
}

// 自定义接收函数 - 捕获服务器接收的消息
static int client_recv(void *ctx, unsigned char *buf, size_t len)
{
    mbedtls_net_context *net_ctx = (mbedtls_net_context *)ctx;
    int ret = mbedtls_net_recv(net_ctx, buf, len);
    if (ret > 0) {
        save_message(&client_capture, buf, ret, "Server->Client");
    }
    return ret;
}

// 自定义发送函数 - 捕获服务器发送的消息
static int server_send(void *ctx, const unsigned char *buf, size_t len)
{
    mbedtls_net_context *net_ctx = (mbedtls_net_context *)ctx;
    save_message(&server_capture, buf, len, "Server->Client");
    return mbedtls_net_send(net_ctx, buf, len);
}

// 自定义接收函数 - 捕获服务器接收的消息
static int server_recv(void *ctx, unsigned char *buf, size_t len)
{
    mbedtls_net_context *net_ctx = (mbedtls_net_context *)ctx;
    int ret = mbedtls_net_recv(net_ctx, buf, len);
    if (ret > 0) {
        save_message(&server_capture, buf, ret, "Client->Server");
    }
    return ret;
}

// 调试回调
static void my_debug(void *ctx, int level,
                     const char *file, int line,
                     const char *str)
{
    FILE *f = (FILE *)ctx;
    if (f != NULL) {
        fprintf(f, "%s:%04d: %s", file, line, str);
        fflush(f);
    }
}

int main(int argc, char *argv[])
{
    int ret = 1;
    mbedtls_net_context server_fd, client_fd;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context ctr_drbg;
    mbedtls_ssl_config conf;
    mbedtls_ssl_context ssl;
    mbedtls_x509_crt srvcert;
    mbedtls_pk_context pkey;
    const char *pers = "tls_message_capture";
    FILE *debug_file = NULL;
    
    // 初始化
    mbedtls_net_init(&server_fd);
    mbedtls_net_init(&client_fd);
    mbedtls_ssl_init(&ssl);
    mbedtls_ssl_config_init(&conf);
    mbedtls_x509_crt_init(&srvcert);
    mbedtls_pk_init(&pkey);
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&ctr_drbg);
    
    // 打开消息捕获文件
    client_capture.file = fopen("tls_client_messages.txt", "w");
    server_capture.file = fopen("tls_server_messages.txt", "w");
    debug_file = fopen("tls_debug.log", "w");
    
    if (client_capture.file == NULL || server_capture.file == NULL) {
        printf("Failed to open output files\n");
        goto cleanup;
    }
    
    fprintf(client_capture.file, "TLS Client Messages Capture\n");
    fprintf(client_capture.file, "============================\n");
    fprintf(server_capture.file, "TLS Server Messages Capture\n");
    fprintf(server_capture.file, "============================\n");
    
    // 生成随机数
    if ((ret = mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy,
                                     (const unsigned char *) pers,
                                     strlen(pers))) != 0) {
        printf("mbedtls_ctr_drbg_seed returned %d\n", ret);
        goto cleanup;
    }
    
    // 加载证书和密钥（使用内置测试证书）
    ret = mbedtls_x509_crt_parse(&srvcert, 
                                 (const unsigned char *) mbedtls_test_srv_crt,
                                 mbedtls_test_srv_crt_len);
    if (ret != 0) {
        printf("mbedtls_x509_crt_parse returned %d\n", ret);
        goto cleanup;
    }
    
    ret = mbedtls_pk_parse_key(&pkey,
                               (const unsigned char *) mbedtls_test_srv_key,
                               mbedtls_test_srv_key_len,
                               NULL, 0);
    if (ret != 0) {
        printf("mbedtls_pk_parse_key returned %d\n", ret);
        goto cleanup;
    }
    
    // 配置SSL
    if ((ret = mbedtls_ssl_config_defaults(&conf,
                                           MBEDTLS_SSL_IS_SERVER,
                                           MBEDTLS_SSL_TRANSPORT_STREAM,
                                           MBEDTLS_SSL_PRESET_DEFAULT)) != 0) {
        printf("mbedtls_ssl_config_defaults returned %d\n", ret);
        goto cleanup;
    }
    
    mbedtls_ssl_conf_rng(&conf, mbedtls_ctr_drbg_random, &ctr_drbg);
    mbedtls_ssl_conf_dbg(&conf, my_debug, debug_file);
    mbedtls_ssl_conf_dbg_level(&conf, 4);
    
    if ((ret = mbedtls_ssl_conf_own_cert(&conf, &srvcert, &pkey)) != 0) {
        printf("mbedtls_ssl_conf_own_cert returned %d\n", ret);
        goto cleanup;
    }
    
    // 绑定服务器
    if ((ret = mbedtls_net_bind(&server_fd, NULL, SERVER_PORT,
                                MBEDTLS_NET_PROTO_TCP)) != 0) {
        printf("mbedtls_net_bind returned %d\n", ret);
        goto cleanup;
    }
    
    printf("Server listening on port %s\n", SERVER_PORT);
    
    // 接受连接
    if ((ret = mbedtls_net_accept(&server_fd, &client_fd,
                                   NULL, 0, NULL)) != 0) {
        printf("mbedtls_net_accept returned %d\n", ret);
        goto cleanup;
    }
    
    printf("Client connected\n");
    
    // 设置SSL上下文
    if ((ret = mbedtls_ssl_setup(&ssl, &conf)) != 0) {
        printf("mbedtls_ssl_setup returned %d\n", ret);
        goto cleanup;
    }
    
    // 使用自定义的发送/接收函数来捕获消息
    mbedtls_ssl_set_bio(&ssl, &client_fd, server_send, server_recv, NULL);
    
    // 执行握手
    printf("Performing TLS handshake...\n");
    while ((ret = mbedtls_ssl_handshake(&ssl)) != 0) {
        if (ret != MBEDTLS_ERR_SSL_WANT_READ && 
            ret != MBEDTLS_ERR_SSL_WANT_WRITE) {
            printf("mbedtls_ssl_handshake returned %d\n", ret);
            goto cleanup;
        }
    }
    
    printf("Handshake completed successfully!\n");
    printf("Messages saved to:\n");
    printf("  - tls_client_messages.txt\n");
    printf("  - tls_server_messages.txt\n");
    printf("  - tls_debug.log\n");
    
    // 关闭连接
    mbedtls_ssl_close_notify(&ssl);
    
    ret = 0;
    
cleanup:
    if (client_capture.file) fclose(client_capture.file);
    if (server_capture.file) fclose(server_capture.file);
    if (debug_file) fclose(debug_file);
    
    mbedtls_net_free(&client_fd);
    mbedtls_net_free(&server_fd);
    mbedtls_ssl_free(&ssl);
    mbedtls_ssl_config_free(&conf);
    mbedtls_x509_crt_free(&srvcert);
    mbedtls_pk_free(&pkey);
    mbedtls_ctr_drbg_free(&ctr_drbg);
    mbedtls_entropy_free(&entropy);
    
    return ret;
}
