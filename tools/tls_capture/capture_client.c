/*
 * Simple TLS Message Capture Tool
 * 
 * This tool uses the existing mbedtls programs and captures messages
 * by hooking into the network layer.
 */

#include "mbedtls/net_sockets.h"
#include "mbedtls/ssl.h"
#include "mbedtls/entropy.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/error.h"
#include "mbedtls/debug.h"
#include "test/certs.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MAX_MSG_SIZE 16384

static FILE *capture_file = NULL;
static int message_count = 0;

// 保存消息到文件
static void save_message(const char *direction,
                        const unsigned char *data, 
                        size_t len)
{
    if (capture_file == NULL || len == 0) {
        return;
    }
    
    message_count++;
    time_t now = time(NULL);
    
    fprintf(capture_file, "\n");
    fprintf(capture_file, "========================================\n");
    fprintf(capture_file, "Message #%d: %s\n", message_count, direction);
    fprintf(capture_file, "Time: %s", ctime(&now));
    fprintf(capture_file, "Length: %zu bytes\n", len);
    fprintf(capture_file, "----------------------------------------\n");
    
    // 解析记录层
    if (len >= 5) {
        unsigned char content_type = data[0];
        unsigned char version_major = data[1];
        unsigned char version_minor = data[2];
        unsigned short length = (data[3] << 8) | data[4];
        
        fprintf(capture_file, "Record Layer:\n");
        fprintf(capture_file, "  ContentType: 0x%02x ", content_type);
        switch (content_type) {
            case 20: fprintf(capture_file, "(ChangeCipherSpec)\n"); break;
            case 21: fprintf(capture_file, "(Alert)\n"); break;
            case 22: fprintf(capture_file, "(Handshake)\n"); break;
            case 23: fprintf(capture_file, "(ApplicationData)\n"); break;
            default: fprintf(capture_file, "(Unknown)\n"); break;
        }
        fprintf(capture_file, "  Version: 0x%02x%02x ", version_major, version_minor);
        if (version_major == 0x03) {
            if (version_minor == 0x03) fprintf(capture_file, "(TLS 1.2)\n");
            else if (version_minor == 0x04) fprintf(capture_file, "(TLS 1.3)\n");
        }
        fprintf(capture_file, "  Length: %u bytes\n", length);
        
        // 解析握手层
        if (content_type == 22 && len >= 9) {
            unsigned char handshake_type = data[5];
            unsigned long handshake_len = ((unsigned long)data[6] << 16) |
                                         ((unsigned long)data[7] << 8) |
                                         (unsigned long)data[8];
            
            fprintf(capture_file, "Handshake Layer:\n");
            fprintf(capture_file, "  HandshakeType: 0x%02x ", handshake_type);
            const char *hs_name = "Unknown";
            switch (handshake_type) {
                case 1: hs_name = "ClientHello"; break;
                case 2: hs_name = "ServerHello"; break;
                case 11: hs_name = "Certificate"; break;
                case 13: hs_name = "CertificateRequest"; break;
                case 15: hs_name = "CertificateVerify"; break;
                case 20: hs_name = "Finished"; break;
            }
            fprintf(capture_file, "(%s)\n", hs_name);
            fprintf(capture_file, "  Length: %lu bytes\n", handshake_len);
        }
    }
    
    fprintf(capture_file, "----------------------------------------\n");
    fprintf(capture_file, "Hex Dump:\n");
    
    // 十六进制输出
    for (size_t i = 0; i < len; i++) {
        if (i % 16 == 0) {
            fprintf(capture_file, "%04zx: ", i);
        }
        fprintf(capture_file, "%02x ", data[i]);
        if (i % 16 == 15 || i == len - 1) {
            // 打印ASCII
            size_t start = (i / 16) * 16;
            size_t end = (i < start + 16) ? i : start + 15;
            for (size_t j = end + 1; j < start + 16; j++) {
                fprintf(capture_file, "   ");
            }
            fprintf(capture_file, " |");
            for (size_t j = start; j <= end; j++) {
                char c = (data[j] >= 32 && data[j] < 127) ? data[j] : '.';
                fprintf(capture_file, "%c", c);
            }
            fprintf(capture_file, "|\n");
        }
    }
    
    fprintf(capture_file, "========================================\n");
    fflush(capture_file);
}

// 自定义发送函数
static int my_send(void *ctx, const unsigned char *buf, size_t len)
{
    mbedtls_net_context *net_ctx = (mbedtls_net_context *)ctx;
    save_message("Client->Server", buf, len);
    return mbedtls_net_send(net_ctx, buf, len);
}

// 自定义接收函数
static int my_recv(void *ctx, unsigned char *buf, size_t len)
{
    mbedtls_net_context *net_ctx = (mbedtls_net_context *)ctx;
    int ret = mbedtls_net_recv(net_ctx, buf, len);
    if (ret > 0) {
        save_message("Server->Client", buf, ret);
    }
    return ret;
}

// 调试回调
static void my_debug(void *ctx, int level,
                     const char *file, int line,
                     const char *str)
{
    FILE *f = (FILE *)ctx;
    if (f != NULL && level <= 3) {
        fprintf(f, "[%d] %s:%04d: %s", level, file, line, str);
        fflush(f);
    }
}

int main(int argc, char *argv[])
{
    int ret = 1;
    mbedtls_net_context server_fd;
    mbedtls_entropy_context entropy;
    mbedtls_ctr_drbg_context ctr_drbg;
    mbedtls_ssl_config conf;
    mbedtls_ssl_context ssl;
    mbedtls_x509_crt cacert;
    const char *pers = "tls_capture";
    FILE *debug_file = NULL;
    const char *capture_filename = "tls_all_messages.txt";
    
    if (argc > 1) {
        capture_filename = argv[1];
    }
    
    // 初始化
    mbedtls_net_init(&server_fd);
    mbedtls_ssl_init(&ssl);
    mbedtls_ssl_config_init(&conf);
    mbedtls_x509_crt_init(&cacert);
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&ctr_drbg);
    
    // 打开捕获文件
    capture_file = fopen(capture_filename, "w");
    debug_file = fopen("tls_debug.log", "w");
    
    if (capture_file == NULL) {
        printf("Failed to open capture file: %s\n", capture_filename);
        goto cleanup;
    }
    
    fprintf(capture_file, "TLS Message Capture - All Messages\n");
    fprintf(capture_file, "===================================\n");
    fprintf(capture_file, "Started: %s\n", ctime(&(time_t){time(NULL)}));
    
    // 初始化PSA Crypto
    psa_status_t status = psa_crypto_init();
    if (status != PSA_SUCCESS) {
        printf("Failed to initialize PSA Crypto: %d\n", (int)status);
        goto cleanup;
    }
    
    // 加载CA证书
    printf("Loading CA certificate...\n");
    ret = mbedtls_x509_crt_parse(&cacert, 
                                 (const unsigned char *)mbedtls_test_cas_pem,
                                 mbedtls_test_cas_pem_len);
    if (ret < 0) {
        printf("Failed to parse CA certificate: %d\n", ret);
        goto cleanup;
    }
    
    // 配置SSL
    printf("Configuring SSL...\n");
    ret = mbedtls_ssl_config_defaults(&conf,
                                       MBEDTLS_SSL_IS_CLIENT,
                                       MBEDTLS_SSL_TRANSPORT_STREAM,
                                       MBEDTLS_SSL_PRESET_DEFAULT);
    if (ret != 0) {
        printf("ssl_config_defaults failed: %d\n", ret);
        goto cleanup;
    }
    
    mbedtls_ssl_conf_authmode(&conf, MBEDTLS_SSL_VERIFY_OPTIONAL);
    mbedtls_ssl_conf_ca_chain(&conf, &cacert, NULL);
    mbedtls_ssl_conf_dbg(&conf, my_debug, debug_file);
    mbedtls_ssl_conf_dbg_level(&conf, 3);
    
    // 连接服务器
    printf("Connecting to localhost:4433...\n");
    ret = mbedtls_net_connect(&server_fd, "localhost", "4433",
                              MBEDTLS_NET_PROTO_TCP);
    if (ret != 0) {
        printf("Connection failed: %d\n", ret);
        printf("Please start the server first!\n");
        goto cleanup;
    }
    
    // 设置SSL上下文
    ret = mbedtls_ssl_setup(&ssl, &conf);
    if (ret != 0) {
        printf("ssl_setup failed: %d\n", ret);
        goto cleanup;
    }
    
    ret = mbedtls_ssl_set_hostname(&ssl, "localhost");
    if (ret != 0) {
        printf("ssl_set_hostname failed: %d\n", ret);
        goto cleanup;
    }
    
    // 使用自定义的发送/接收函数
    mbedtls_ssl_set_bio(&ssl, &server_fd, my_send, my_recv, NULL);
    
    // 执行握手
    printf("Performing TLS handshake...\n");
    while ((ret = mbedtls_ssl_handshake(&ssl)) != 0) {
        if (ret != MBEDTLS_ERR_SSL_WANT_READ && 
            ret != MBEDTLS_ERR_SSL_WANT_WRITE) {
            printf("Handshake failed: %d\n", ret);
            goto cleanup;
        }
    }
    
    printf("Handshake completed successfully!\n");
    printf("Captured %d messages\n", message_count);
    printf("Messages saved to: %s\n", capture_filename);
    
    // 关闭连接
    mbedtls_ssl_close_notify(&ssl);
    
    ret = 0;
    
cleanup:
    if (capture_file) {
        fprintf(capture_file, "\nCapture ended: %s\n", ctime(&(time_t){time(NULL)}));
        fprintf(capture_file, "Total messages: %d\n", message_count);
        fclose(capture_file);
    }
    if (debug_file) fclose(debug_file);
    
    mbedtls_net_free(&server_fd);
    mbedtls_ssl_free(&ssl);
    mbedtls_ssl_config_free(&conf);
    mbedtls_x509_crt_free(&cacert);
    mbedtls_ctr_drbg_free(&ctr_drbg);
    mbedtls_entropy_free(&entropy);
    
    return ret;
}
