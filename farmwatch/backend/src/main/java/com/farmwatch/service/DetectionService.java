package com.farmwatch.service;

import com.farmwatch.dto.*;
import com.farmwatch.entity.Detection;
import com.farmwatch.entity.Sector;
import com.farmwatch.repository.DetectionRepository;
import com.farmwatch.repository.SectorRepository;
import com.farmwatch.websocket.DetectionEventPublisher;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.*;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class DetectionService {

    private final DetectionRepository detectionRepo;
    private final SectorRepository sectorRepo;
    private final SirenService sirenService;
    private final DetectionEventPublisher eventPublisher;

    // ── Dashboard summary ─────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public DashboardSummaryDto getSummary() {
        OffsetDateTime todayStart = OffsetDateTime.now().toLocalDate()
                .atStartOfDay().atOffset(ZoneOffset.UTC);
        OffsetDateTime todayEnd   = todayStart.plusDays(1);
        OffsetDateTime weekStart  = todayStart.minusDays(6);

        Detection last = detectionRepo.findTopByOrderByDetectedAtDesc();
        SirenStatusDto sirenStatus = sirenService.getStatus();

        return DashboardSummaryDto.builder()
                .detectionsToday(detectionRepo.countByDateRange(todayStart, todayEnd))
                .detectionsThisWeek(detectionRepo.countByDateRange(weekStart, todayEnd))
                .sirenTriggersToday(detectionRepo.countSirenTriggered(todayStart, todayEnd))
                .lastDetectionAt(last != null ? last.getDetectedAt() : null)
                .sirenMode(sirenStatus.getMode())
                .sirenActive(sirenStatus.isActive())
                .build();
    }

    // ── Hourly chart ──────────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public HourlyChartDto getHourlyChart() {
        OffsetDateTime start = OffsetDateTime.now().toLocalDate()
                .atStartOfDay().atOffset(ZoneOffset.UTC);
        OffsetDateTime end = start.plusDays(1);

        List<Object[]> rows = detectionRepo.countByHour(start, end);
        Map<Integer, Long> byHour = rows.stream()
                .collect(Collectors.toMap(
                        r -> ((Number) r[0]).intValue(),
                        r -> ((Number) r[1]).longValue()
                ));

        List<HourlyChartDto.HourSlot> slots = new ArrayList<>();
        for (int h = 0; h < 24; h++) {
            slots.add(HourlyChartDto.HourSlot.builder()
                    .hour(h)
                    .count(byHour.getOrDefault(h, 0L))
                    .build());
        }
        return HourlyChartDto.builder().slots(slots).build();
    }

    // ── Weekly heatmap ────────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public WeeklyHeatmapDto getWeeklyHeatmap() {
        OffsetDateTime end   = OffsetDateTime.now();
        OffsetDateTime start = end.minusDays(7);

        List<Object[]> rows = detectionRepo.countByDowAndHour(start, end);
        Map<String, Long> data = new LinkedHashMap<>();
        long maxValue = 0;

        for (Object[] row : rows) {
            int dow   = ((Number) row[0]).intValue();
            int hour  = ((Number) row[1]).intValue();
            long count = ((Number) row[2]).longValue();
            String key = dow + "-" + hour;
            data.put(key, count);
            if (count > maxValue) maxValue = count;
        }
        return WeeklyHeatmapDto.builder().data(data).maxValue(maxValue).build();
    }

    // ── Method breakdown ──────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public MethodBreakdownDto getMethodBreakdown() {
        OffsetDateTime end   = OffsetDateTime.now();
        OffsetDateTime start = end.minusDays(7);

        List<Object[]> rows = detectionRepo.countByMethod(start, end);
        Map<String, Long> counts = rows.stream()
                .collect(Collectors.toMap(r -> (String) r[0], r -> ((Number) r[1]).longValue()));

        long cam   = counts.getOrDefault("CAMERA", 0L);
        long sound = counts.getOrDefault("SOUND",  0L);
        long both  = counts.getOrDefault("BOTH",   0L);
        long total = cam + sound + both;

        double divisor = total == 0 ? 1 : total;
        return MethodBreakdownDto.builder()
                .cameraCount(cam).soundCount(sound).bothCount(both).total(total)
                .cameraPercent(Math.round(cam  / divisor * 1000) / 10.0)
                .soundPercent (Math.round(sound / divisor * 1000) / 10.0)
                .bothPercent  (Math.round(both  / divisor * 1000) / 10.0)
                .build();
    }

    // ── Paginated detection table ─────────────────────────────────────────────

    @Transactional(readOnly = true)
    public Page<DetectionDto> getDetections(int page, int size) {
        PageRequest pr = PageRequest.of(page, size, Sort.by("detectedAt").descending());
        return detectionRepo.findAllByOrderByDetectedAtDesc(pr)
                .map(this::toDto);
    }

    // ── Ingest new detection (called by AI module) ────────────────────────────

    @Transactional
    public Detection ingest(Detection detection) {
        Detection saved = detectionRepo.save(detection);
        log.info("New detection saved: {} confidence={}", saved.getMethod(), saved.getConfidence());

        // Auto-trigger siren if configured
        sirenService.handleDetection(saved);

        // Push to WebSocket subscribers
        eventPublisher.publish(toEventDto(saved));
        return saved;
    }

    // ── Mappers ───────────────────────────────────────────────────────────────

    private DetectionDto toDto(Detection d) {
        return DetectionDto.builder()
                .id(d.getId())
                .detectedAt(d.getDetectedAt())
                .method(d.getMethod().name())
                .confidence(d.getConfidence())
                .speciesEst(d.getSpeciesEst())
                .sectorCode(d.getSector() != null ? d.getSector().getCode() : null)
                .sectorName(d.getSector() != null ? d.getSector().getName() : null)
                .sirenTriggered(d.isSirenTriggered())
                .durationSecs(d.getDurationSecs())
                .imagePath(d.getImagePath())
                .build();
    }

    private DetectionEventDto toEventDto(Detection d) {
        return DetectionEventDto.builder()
                .detectionId(d.getId())
                .detectedAt(d.getDetectedAt())
                .method(d.getMethod().name())
                .confidence(d.getConfidence())
                .speciesEst(d.getSpeciesEst())
                .sectorCode(d.getSector() != null ? d.getSector().getCode() : null)
                .sirenTriggered(d.isSirenTriggered())
                .build();
    }
}
