package com.farmwatch.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Data
@Builder
public class DetectionEventDto {
    private UUID detectionId;
    private OffsetDateTime detectedAt;
    private String method;
    private BigDecimal confidence;
    private String speciesEst;
    private String sectorCode;
    private boolean sirenTriggered;
    // Bounding box (camera detections)
    private Double bboxX;
    private Double bboxY;
    private Double bboxW;
    private Double bboxH;
}