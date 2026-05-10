package com.farmwatch.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class HourlyChartDto {
    private List<HourSlot> slots; // 24 entries, hour 0-23

    @Data @Builder
    public static class HourSlot {
        private int hour;
        private long count;
    }
}
