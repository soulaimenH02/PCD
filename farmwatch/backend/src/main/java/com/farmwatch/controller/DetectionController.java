package com.farmwatch.controller;

import com.farmwatch.dto.*;
import com.farmwatch.entity.Detection;
import com.farmwatch.entity.Sector;
import com.farmwatch.repository.SectorRepository;
import com.farmwatch.service.DetectionService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.List;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class DetectionController {

    private final DetectionService detectionService;
    private final SectorRepository sectorRepo;

    /** GET /api/stats/summary — dashboard metric cards */
    @GetMapping("/stats/summary")
    public ResponseEntity<DashboardSummaryDto> summary() {
        return ResponseEntity.ok(detectionService.getSummary());
    }

    /** GET /api/stats/hourly — today's hourly bar chart */
    @GetMapping("/stats/hourly")
    public ResponseEntity<HourlyChartDto> hourly() {
        return ResponseEntity.ok(detectionService.getHourlyChart());
    }

    /** GET /api/stats/weekly — weekly heatmap */
    @GetMapping("/stats/weekly")
    public ResponseEntity<WeeklyHeatmapDto> weekly() {
        return ResponseEntity.ok(detectionService.getWeeklyHeatmap());
    }

    /** GET /api/stats/methods — camera vs sound vs both */
    @GetMapping("/stats/methods")
    public ResponseEntity<MethodBreakdownDto> methods() {
        return ResponseEntity.ok(detectionService.getMethodBreakdown());
    }

    /** GET /api/detections?page=0&size=20 — paginated table */
    @GetMapping("/detections")
    public ResponseEntity<Page<DetectionDto>> detections(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(detectionService.getDetections(page, size));
    }

    /**
     * POST /api/detections — ingest a new detection from the AI module.
     * The robot/AI calls this endpoint when it detects a bird.
     */
    @PostMapping("/detections")
    public ResponseEntity<DetectionDto> ingest(@Valid @RequestBody IngestRequest req) {
        Sector sector = sectorRepo.findById(req.getSectorId())
                .orElseThrow(() -> new IllegalArgumentException("Unknown sector: " + req.getSectorId()));

        Detection detection = Detection.builder()
                .sector(sector)
                .detectedAt(req.getDetectedAt() != null ? req.getDetectedAt() : OffsetDateTime.now())
                .method(Detection.Method.valueOf(req.getMethod()))
                .confidence(req.getConfidence())
                .speciesEst(req.getSpeciesEst())
                .durationSecs(req.getDurationSecs())
                .imagePath(req.getImagePath())
                .audioPath(req.getAudioPath())
                .sirenTriggered(false) // set by SirenService
                .build();

        Detection saved = detectionService.ingest(detection);

        return ResponseEntity.ok(DetectionDto.builder()
                .id(saved.getId())
                .detectedAt(saved.getDetectedAt())
                .method(saved.getMethod().name())
                .confidence(saved.getConfidence())
                .sectorCode(sector.getCode())
                .build());
    }

    /** GET /api/sectors — list active farm sectors */
    @GetMapping("/sectors")
    public ResponseEntity<List<Sector>> sectors() {
        return ResponseEntity.ok(sectorRepo.findByActiveTrue());
    }

    // ── Request body for AI ingest endpoint ──────────────────────────────────

    @Data
    public static class IngestRequest {
        @NotNull
        private Integer sectorId;

        @NotBlank
        private String method;  // CAMERA | SOUND | BOTH

        @NotNull @DecimalMin("0") @DecimalMax("100")
        private BigDecimal confidence;

        private String speciesEst;
        private Integer durationSecs;
        private String imagePath;
        private String audioPath;
        private OffsetDateTime detectedAt;
    }
}
