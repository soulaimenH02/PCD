package com.farmwatch.dto;

import lombok.Data;

@Data
public class SirenCommandDto {
    private String mode;         // AUTO | MANUAL | DISABLED (for mode changes)
    private String triggeredBy;  // username (for manual triggers)
}