package com.farmwatch.controller;

import com.farmwatch.dto.CameraDto;
import com.farmwatch.dto.SirenCommandDto;
import com.farmwatch.dto.SirenStatusDto;
import com.farmwatch.entity.Camera;
import com.farmwatch.repository.CameraRepository;
import com.farmwatch.service.SirenService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

// ── Siren Controller ──────────────────────────────────────────────────────────

@RestController
@RequestMapping("/api/siren")
@RequiredArgsConstructor
class SirenController {

    private final SirenService sirenService;

    /** GET /api/siren/status */
    @GetMapping("/status")
    public ResponseEntity<SirenStatusDto> status() {
        return ResponseEntity.ok(sirenService.getStatus());
    }

    /** POST /api/siren/activate — manual activation */
    @PostMapping("/activate")
    public ResponseEntity<Map<String, Object>> activate(@RequestBody(required = false) SirenCommandDto cmd) {
        String user = cmd != null ? cmd.getTriggeredBy() : "admin";
        sirenService.activateManual(user);
        return ResponseEntity.ok(Map.of("success", true, "message", "Siren activated"));
    }

    /** POST /api/siren/stop — manual stop */
    @PostMapping("/stop")
    public ResponseEntity<Map<String, Object>> stop() {
        sirenService.deactivateManual();
        return ResponseEntity.ok(Map.of("success", true, "message", "Siren stopped"));
    }

    /** POST /api/siren/mode — change mode: AUTO | MANUAL | DISABLED */
    @PostMapping("/mode")
    public ResponseEntity<Map<String, Object>> mode(@RequestBody Map<String, String> body) {
        String mode = body.get("mode");
        if (mode == null || !List.of("AUTO", "MANUAL", "DISABLED").contains(mode.toUpperCase())) {
            return ResponseEntity.badRequest().body(Map.of("error", "Invalid mode"));
        }
        sirenService.setMode(mode);
        return ResponseEntity.ok(Map.of("success", true, "mode", mode.toUpperCase()));
    }
}

// ── Camera Controller ─────────────────────────────────────────────────────────

@RestController
@RequestMapping("/api/camera")
@RequiredArgsConstructor
class CameraController {

    private final CameraRepository cameraRepo;

    /** GET /api/camera — list all active cameras */
    @GetMapping
    public ResponseEntity<List<CameraDto>> list() {
        List<Camera> cameras = cameraRepo.findByActiveTrue();
        List<CameraDto> dtos = cameras.stream().map(c -> CameraDto.builder()
                .id(c.getId())
                .name(c.getName())
                .sectorCode(c.getSector() != null ? c.getSector().getCode() : null)
                .streamUrl("/api/camera/" + c.getId() + "/stream")
                .active(c.isActive())
                .build()).collect(Collectors.toList());
        return ResponseEntity.ok(dtos);
    }

    /**
     * GET /api/camera/{id}/stream
     *
     * In a real deployment you would:
     *  1. Proxy the RTSP stream through a library like OpenCV (via Python script) 
     *     and re-stream as MJPEG, OR
     *  2. Use a dedicated media server (e.g. MediaMTX / Frigate) and return
     *     a redirect to its MJPEG URL.
     *
     * For now this returns the stream URL for the frontend to use directly.
     */
    @GetMapping("/{id}/stream-url")
    public ResponseEntity<Map<String, String>> streamUrl(@PathVariable Integer id) {
        return cameraRepo.findById(id)
                .map(c -> ResponseEntity.ok(Map.of(
                        "cameraId", String.valueOf(c.getId()),
                        "name", c.getName(),
                        "streamUrl", c.getStreamUrl() != null ? c.getStreamUrl() : ""
                )))
                .orElse(ResponseEntity.notFound().build());
    }

    /** POST /api/camera/switch — tell system to show a different sector */
    @PostMapping("/switch")
    public ResponseEntity<Map<String, Object>> switchCamera(@RequestBody Map<String, String> body) {
        String sector = body.get("sector");
        // In production: send command to camera switcher or update active camera config
        return ResponseEntity.ok(Map.of("success", true, "sector", sector));
    }
}
