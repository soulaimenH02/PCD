package com.farmwatch.dto;

import lombok.Builder;
import lombok.Data;

import java.time.OffsetDateTime;

@Data
@Builder
public class DashboardSummaryDto {
    private long detectionsToday;
    private long detectionsThisWeek;
    private long sirenTriggersToday;
    private OffsetDateTime lastDetectionAt;
    private String sirenMode;
    private boolean sirenActive;
}