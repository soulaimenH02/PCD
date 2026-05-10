package com.farmwatch.service;

import com.farmwatch.dto.SirenStatusDto;
import com.farmwatch.entity.Detection;
import com.farmwatch.entity.SirenEvent;
import com.farmwatch.repository.SirenEventRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

@Service
@RequiredArgsConstructor
@Slf4j
public class SirenService {

    private final SirenEventRepository sirenEventRepo;
    private final SimpMessagingTemplate messagingTemplate;

    @Value("${farmwatch.siren.auto_duration_secs:10}")
    private int autoDurationSecs;

    @Value("${farmwatch.detection.confidence-threshold:80.0}")
    private double confidenceThreshold;

    private final AtomicBoolean sirenActive = new AtomicBoolean(false);
    private volatile String sirenMode = "AUTO";
    private volatile OffsetDateTime activeSince;
    private volatile Integer currentEventId;
    private volatile OffsetDateTime autoStopAt;

    // ── Status ────────────────────────────────────────────────────────────────

    public SirenStatusDto getStatus() {
        return SirenStatusDto.builder()
                .active(sirenActive.get())
                .mode(sirenMode)
                .activeSince(activeSince)
                .currentEventId(currentEventId)
                .build();
    }

    // ── Mode change ───────────────────────────────────────────────────────────

    public void setMode(String mode) {
        sirenMode = mode.toUpperCase();
        if ("DISABLED".equals(sirenMode) && sirenActive.get()) {
            stopSiren();
        }
        log.info("Siren mode changed to {}", sirenMode);
        broadcastStatus();
    }

    // ── Manual activation ─────────────────────────────────────────────────────

    @Transactional
    public void activateManual(String username) {
        if ("DISABLED".equals(sirenMode)) {
            // Return gracefully instead of throwing — frontend handles the mode
            log.warn("Siren activation ignored — mode is DISABLED");
            return;
        }
        SirenEvent event = SirenEvent.builder()
                .triggeredBy(SirenEvent.TriggerType.MANUAL)
                .triggeredAt(OffsetDateTime.now())
                .triggeredByUser(username)
                .build();
        SirenEvent saved = sirenEventRepo.save(event);
        activateSiren(saved.getId(), null);
    }

    @Transactional
    public void deactivateManual() {
        stopSiren();
    }

    // ── Auto-trigger on detection ─────────────────────────────────────────────

    @Transactional
    public void handleDetection(Detection detection) {
        if (!"AUTO".equals(sirenMode)) return;
        double conf = detection.getConfidence().doubleValue();
        if (conf < confidenceThreshold) return;

        if (!sirenActive.get()) {
            SirenEvent event = SirenEvent.builder()
                    .detection(detection)
                    .triggeredBy(SirenEvent.TriggerType.AUTO)
                    .triggeredAt(OffsetDateTime.now())
                    .build();
            SirenEvent saved = sirenEventRepo.save(event);
            autoStopAt = OffsetDateTime.now().plusSeconds(autoDurationSecs);
            activateSiren(saved.getId(), autoStopAt);
        }
    }

    // ── Scheduled auto-stop ───────────────────────────────────────────────────

    @Scheduled(fixedRate = 1000)
    public void checkAutoStop() {
        if (sirenActive.get() && autoStopAt != null
                && OffsetDateTime.now().isAfter(autoStopAt)) {
            stopSiren();
        }
    }

    // ── Internal helpers ──────────────────────────────────────────────────────

    private void activateSiren(Integer eventId, OffsetDateTime stopAt) {
        sirenActive.set(true);
        activeSince = OffsetDateTime.now();
        currentEventId = eventId;
        autoStopAt = stopAt;
        log.warn("SIREN ACTIVATED — eventId={}", eventId);
        broadcastStatus();
    }

    @Transactional
    protected void stopSiren() {
        if (!sirenActive.get()) return;
        sirenActive.set(false);
        autoStopAt = null;

        if (currentEventId != null) {
            sirenEventRepo.findById(currentEventId).ifPresent(ev -> {
                ev.setStoppedAt(OffsetDateTime.now());
                sirenEventRepo.save(ev);
            });
        }
        currentEventId = null;
        activeSince = null;
        log.info("Siren stopped");
        broadcastStatus();
    }

    // ── FIX: use HashMap instead of Map.of() to allow null values ────────────
    private void broadcastStatus() {
        Map<String, Object> payload = new HashMap<>();
        payload.put("active", sirenActive.get());
        payload.put("mode", sirenMode);
        // activeSince can be null — HashMap allows null values, Map.of() does not
        payload.put("activeSince", activeSince != null ? activeSince.toString() : null);

        messagingTemplate.convertAndSend("/topic/siren-status", payload);
    }
}