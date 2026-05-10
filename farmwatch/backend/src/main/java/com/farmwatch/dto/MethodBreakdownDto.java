package com.farmwatch.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class MethodBreakdownDto {
    private long cameraCount;
    private long soundCount;
    private long bothCount;
    private long total;
    private double cameraPercent;
    private double soundPercent;
    private double bothPercent;
}