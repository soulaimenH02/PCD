package com.farmwatch.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Data
@Builder
public class DetectionDto {
    private UUID id;
    private OffsetDateTime detectedAt;
    private String method;
    private BigDecimal confidence;
    private String speciesEst;
    private String sectorCode;
    private String sectorName;
    private boolean sirenTriggered;
    private Integer durationSecs;
    private String imagePath;
}