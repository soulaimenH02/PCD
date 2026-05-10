package com.farmwatch.controller;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;
import org.springframework.http.ResponseEntity;

import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Proxies the ESP-CAM MJPEG stream so Angular can display it
 * without CORS issues. The stream URL is configured in application.yml.
 *
 * Usage: GET /api/camera/live-stream
 * Angular uses this as: <img src="/api/camera/live-stream">
 */
@RestController
@RequestMapping("/api/camera")
@Slf4j
public class CameraStreamController {

    @Value("${farmwatch.camera.espcam-url:http://192.168.100.37:81/stream}")
    private String espCamUrl;

    @Value("${farmwatch.camera.pi-stream-url:http://localhost:4000/stream}")
    private String piStreamUrl;

    /**
     * Proxy the ESP-CAM MJPEG stream.
     * Configure the ESP-CAM IP in application.yml under:
     * farmwatch.camera.espcam-url
     */
    @GetMapping(value = "/live-stream", produces = "multipart/x-mixed-replace; boundary=frame")
    public ResponseEntity<StreamingResponseBody> liveStream(
            @RequestParam(defaultValue = "espcam") String source) {

        String streamUrl = "pi".equals(source) ? piStreamUrl : espCamUrl;

        StreamingResponseBody body = outputStream -> {
            try {
                HttpURLConnection conn = (HttpURLConnection) new URL(streamUrl).openConnection();
                conn.setConnectTimeout(5000);
                conn.setReadTimeout(30000);
                conn.connect();

                try (InputStream inputStream = conn.getInputStream()) {
                    byte[] buffer = new byte[4096];
                    int bytesRead;
                    while ((bytesRead = inputStream.read(buffer)) != -1) {
                        outputStream.write(buffer, 0, bytesRead);
                        outputStream.flush();
                    }
                }
            } catch (Exception e) {
                log.error("Camera stream error: {}", e.getMessage());
            }
        };

        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("multipart/x-mixed-replace; boundary=frame"))
                .body(body);
    }

    /**
     * Returns a single JPEG snapshot from the ESP-CAM.
     * ESP-CAM snapshot endpoint is typically /capture
     */
    @GetMapping(value = "/snapshot", produces = MediaType.IMAGE_JPEG_VALUE)
    public ResponseEntity<byte[]> snapshot(
            @RequestParam(defaultValue = "espcam") String source) {
        String snapshotUrl = espCamUrl.replace("/stream", "/capture");
        if ("pi".equals(source)) {
            snapshotUrl = piStreamUrl.replace("/stream", "/snapshot");
        }

        try {
            HttpURLConnection conn = (HttpURLConnection) new URL(snapshotUrl).openConnection();
            conn.setConnectTimeout(3000);
            conn.setReadTimeout(5000);
            byte[] imageBytes = conn.getInputStream().readAllBytes();
            return ResponseEntity.ok()
                    .contentType(MediaType.IMAGE_JPEG)
                    .body(imageBytes);
        } catch (Exception e) {
            log.error("Snapshot error: {}", e.getMessage());
            return ResponseEntity.status(503).build();
        }
    }
}
