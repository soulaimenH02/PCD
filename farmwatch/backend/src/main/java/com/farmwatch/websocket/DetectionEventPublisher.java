package com.farmwatch.websocket;

import com.farmwatch.dto.DetectionEventDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class DetectionEventPublisher {

    private final SimpMessagingTemplate messagingTemplate;

    /**
     * Broadcast a new detection event to all WebSocket subscribers.
     * Angular subscribes to /topic/detections
     */
    public void publish(DetectionEventDto event) {
        messagingTemplate.convertAndSend("/topic/detections", event);
        log.debug("Detection event pushed to WebSocket: {}", event.getDetectionId());
    }
}
