// ============================================================
//  FarmWatch — ESP32-CAM (camera + siren control)
//
//  - MJPEG stream  : http://IP:81/stream
//  - Snapshot      : http://IP:81/capture
//  - Siren ON      : http://IP:82/siren/on
//  - Siren OFF     : http://IP:82/siren/off
//  - Status        : http://IP:82/status
//
//  Architecture:
//  - The ESP32 only exposes the camera stream and the siren control endpoints.
//  - Bird detection AND backend reporting are entirely handled by bridge.py
//    on the Raspberry Pi (which polls /capture or pulls from /stream).
//  - The siren is driven exclusively via /siren/on or /siren/off, called by
//    bridge.py when Spring Boot says the siren should be active.
// ============================================================

#include <WiFi.h>
#include "esp_camera.h"
#include "esp_http_server.h"

// ─────────────────────────────────────────────────────────────
// WIFI
// ─────────────────────────────────────────────────────────────
const char* WIFI_SSID     = "HUAWEI-2.4G-Kt6f";
const char* WIFI_PASSWORD = "Manoubadom062009";

// ─────────────────────────────────────────────────────────────
// GPIO
// ─────────────────────────────────────────────────────────────
#define PIN_SIREN     4    // built-in flash LED + buzzer (via NPN transistor)

// ─────────────────────────────────────────────────────────────
// CAMERA PINS — AI Thinker ESP32-CAM
// ─────────────────────────────────────────────────────────────
#define PWDN_GPIO_NUM    32
#define RESET_GPIO_NUM   -1
#define XCLK_GPIO_NUM     0
#define SIOD_GPIO_NUM    26
#define SIOC_GPIO_NUM    27
#define Y9_GPIO_NUM      35
#define Y8_GPIO_NUM      34
#define Y7_GPIO_NUM      39
#define Y6_GPIO_NUM      36
#define Y5_GPIO_NUM      21
#define Y4_GPIO_NUM      19
#define Y3_GPIO_NUM      18
#define Y2_GPIO_NUM       5
#define VSYNC_GPIO_NUM   25
#define HREF_GPIO_NUM    23
#define PCLK_GPIO_NUM    22

// ─────────────────────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────────────────────
bool sirenActive = false;

// ─────────────────────────────────────────────────────────────
// CAMERA INIT
// ─────────────────────────────────────────────────────────────
void init_camera() {
    camera_config_t config;
    config.ledc_channel  = LEDC_CHANNEL_0;
    config.ledc_timer    = LEDC_TIMER_0;
    config.pin_d0        = Y2_GPIO_NUM;
    config.pin_d1        = Y3_GPIO_NUM;
    config.pin_d2        = Y4_GPIO_NUM;
    config.pin_d3        = Y5_GPIO_NUM;
    config.pin_d4        = Y6_GPIO_NUM;
    config.pin_d5        = Y7_GPIO_NUM;
    config.pin_d6        = Y8_GPIO_NUM;
    config.pin_d7        = Y9_GPIO_NUM;
    config.pin_xclk      = XCLK_GPIO_NUM;
    config.pin_pclk      = PCLK_GPIO_NUM;
    config.pin_vsync     = VSYNC_GPIO_NUM;
    config.pin_href      = HREF_GPIO_NUM;
    config.pin_sccb_sda  = SIOD_GPIO_NUM;
    config.pin_sccb_scl  = SIOC_GPIO_NUM;
    config.pin_pwdn      = PWDN_GPIO_NUM;
    config.pin_reset     = RESET_GPIO_NUM;
    config.xclk_freq_hz  = 20000000;
    config.pixel_format  = PIXFORMAT_JPEG;
    config.frame_size    = FRAMESIZE_VGA;     // 640x480
    config.jpeg_quality  = 12;
    config.fb_count      = 2;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed: 0x%x\n", err);
        delay(1000);
        ESP.restart();
    }
    Serial.println("Camera ready");
}

// ─────────────────────────────────────────────────────────────
// HTTP STREAM HANDLER (port 81)
// ─────────────────────────────────────────────────────────────
#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE =
    "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART =
    "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t stream_httpd = NULL;

esp_err_t stream_handler(httpd_req_t* req) {
    camera_fb_t* fb  = NULL;
    esp_err_t    res = ESP_OK;
    char part_buf[64];

    res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
    if (res != ESP_OK) return res;
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) { res = ESP_FAIL; break; }

        res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
        if (res == ESP_OK) {
            size_t hlen = snprintf(part_buf, 64, STREAM_PART, fb->len);
            res = httpd_resp_send_chunk(req, part_buf, hlen);
        }
        if (res == ESP_OK)
            res = httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);
        esp_camera_fb_return(fb);
        if (res != ESP_OK) break;
    }
    return res;
}

esp_err_t snapshot_handler(httpd_req_t* req) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_send(req, (const char*)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    return ESP_OK;
}

// ─────────────────────────────────────────────────────────────
// HTTP SIREN HANDLERS (port 82)
// ─────────────────────────────────────────────────────────────
esp_err_t siren_on_handler(httpd_req_t* req) {
    sirenActive = true;
    digitalWrite(PIN_SIREN, HIGH);
    Serial.println("SIREN ON");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_sendstr(req, "{\"status\":\"siren_on\"}");
    return ESP_OK;
}

esp_err_t siren_off_handler(httpd_req_t* req) {
    sirenActive = false;
    digitalWrite(PIN_SIREN, LOW);
    Serial.println("SIREN OFF");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_sendstr(req, "{\"status\":\"siren_off\"}");
    return ESP_OK;
}

esp_err_t status_handler(httpd_req_t* req) {
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    String json = "{\"status\":\"ok\"";
    json += ",\"siren\":" + String(sirenActive ? "true" : "false");
    json += "}";
    httpd_resp_sendstr(req, json.c_str());
    return ESP_OK;
}

// ─────────────────────────────────────────────────────────────
// START HTTP SERVERS
// ─────────────────────────────────────────────────────────────
void startServers() {
    // Stream server — port 81
    httpd_config_t stream_cfg = HTTPD_DEFAULT_CONFIG();
    stream_cfg.server_port    = 81;
    stream_cfg.ctrl_port      = 32768;        // unique to avoid collision

    httpd_uri_t stream_uri   = { "/stream",  HTTP_GET, stream_handler,   NULL };
    httpd_uri_t snapshot_uri = { "/capture", HTTP_GET, snapshot_handler, NULL };

    if (httpd_start(&stream_httpd, &stream_cfg) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &stream_uri);
        httpd_register_uri_handler(stream_httpd, &snapshot_uri);
        Serial.printf("Stream   : http://%s:81/stream\n",  WiFi.localIP().toString().c_str());
        Serial.printf("Snapshot : http://%s:81/capture\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("Failed to start stream server");
    }

    // Control server — port 82
    httpd_handle_t ctrl_httpd = NULL;
    httpd_config_t ctrl_cfg   = HTTPD_DEFAULT_CONFIG();
    ctrl_cfg.server_port      = 82;
    ctrl_cfg.ctrl_port        = 32769;        // unique to avoid collision

    httpd_uri_t siren_on  = { "/siren/on",  HTTP_GET, siren_on_handler,  NULL };
    httpd_uri_t siren_off = { "/siren/off", HTTP_GET, siren_off_handler, NULL };
    httpd_uri_t status    = { "/status",    HTTP_GET, status_handler,    NULL };

    if (httpd_start(&ctrl_httpd, &ctrl_cfg) == ESP_OK) {
        httpd_register_uri_handler(ctrl_httpd, &siren_on);
        httpd_register_uri_handler(ctrl_httpd, &siren_off);
        httpd_register_uri_handler(ctrl_httpd, &status);
        Serial.printf("Siren    : http://%s:82/siren/on|off\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("Failed to start control server (port 82)");
    }
}

// ─────────────────────────────────────────────────────────────
// SETUP
// ─────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    Serial.println("\n============================================================");
    Serial.println("  FarmWatch ESP32-CAM");
    Serial.println("============================================================");

    pinMode(PIN_SIREN, OUTPUT);
    digitalWrite(PIN_SIREN, LOW);

    // Connect WiFi
    Serial.printf("WiFi: connecting to %s ...", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 30) {
        delay(500); Serial.print("."); tries++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\nWiFi connected. IP: %s\n",
            WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\nWiFi failed. Restarting...");
        ESP.restart();
    }

    init_camera();
    startServers();

    Serial.println("\nAll systems ready.\n");
}

// ─────────────────────────────────────────────────────────────
// LOOP
// ─────────────────────────────────────────────────────────────
void loop() {
    // Nothing to do here — everything runs in the HTTP server tasks.
    delay(1000);
}
