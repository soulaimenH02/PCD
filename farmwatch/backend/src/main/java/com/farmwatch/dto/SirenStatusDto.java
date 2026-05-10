package com.farmwatch.dto;

import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;

@Data
@Builder
public class SirenStatusDto {
    private boolean active;
    private String mode;         // AUTO | MANUAL | DISABLED
    private OffsetDateTime activeSince;
    private Integer currentEventId;
}