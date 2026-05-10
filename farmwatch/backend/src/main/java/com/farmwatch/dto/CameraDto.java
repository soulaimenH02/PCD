package com.farmwatch.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class CameraDto {
    private Integer id;
    private String name;
    private String sectorCode;
    private String streamUrl;      // proxied MJPEG URL safe for browser
    private boolean active;
}
