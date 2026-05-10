package com.farmwatch;

import org.springframework.boot.SpringApplication;



import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class FarmWatchApplication {
    public static void main(String[] args) {
        SpringApplication.run(FarmWatchApplication.class, args);
    }
}
