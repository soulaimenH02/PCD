package com.farmwatch.dto;

import lombok.Builder;
import lombok.Data;

import java.util.Map;

@Data
@Builder
public class WeeklyHeatmapDto {
    // Map<"dow-hour", count>  e.g. "1-8" = Monday 08:00
    private Map<String, Long> data;
    private long maxValue;
}