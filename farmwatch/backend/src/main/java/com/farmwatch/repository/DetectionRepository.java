package com.farmwatch.repository;

import com.farmwatch.entity.Detection;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Repository
public interface DetectionRepository extends JpaRepository<Detection, UUID> {

    // Paginated list for the stats table
    Page<Detection> findAllByOrderByDetectedAtDesc(Pageable pageable);

    // Count today's detections
    @Query("SELECT COUNT(d) FROM Detection d WHERE d.detectedAt >= :start AND d.detectedAt < :end")
    long countByDateRange(@Param("start") OffsetDateTime start, @Param("end") OffsetDateTime end);

    // Hourly breakdown for chart (returns hour 0-23 + count)
    @Query(value = """
        SELECT CAST(EXTRACT(HOUR FROM detected_at) AS INT) AS hour, COUNT(*) AS count
        FROM detections
        WHERE detected_at >= :start AND detected_at < :end
        GROUP BY hour
        ORDER BY hour
        """, nativeQuery = true)
    List<Object[]> countByHour(@Param("start") OffsetDateTime start, @Param("end") OffsetDateTime end);

    // Weekly heatmap: day-of-week (1=Mon..7=Sun) × hour
    @Query(value = """
        SELECT
            CAST(EXTRACT(ISODOW FROM detected_at) AS INT) AS dow,
            CAST(EXTRACT(HOUR   FROM detected_at) AS INT) AS hour,
            COUNT(*) AS count
        FROM detections
        WHERE detected_at >= :start AND detected_at < :end
        GROUP BY dow, hour
        ORDER BY dow, hour
        """, nativeQuery = true)
    List<Object[]> countByDowAndHour(@Param("start") OffsetDateTime start, @Param("end") OffsetDateTime end);

    // Method breakdown percentages
    @Query(value = """
        SELECT method, COUNT(*) AS count
        FROM detections
        WHERE detected_at >= :start AND detected_at < :end
        GROUP BY method
        """, nativeQuery = true)
    List<Object[]> countByMethod(@Param("start") OffsetDateTime start, @Param("end") OffsetDateTime end);

    // Most recent detection
    Detection findTopByOrderByDetectedAtDesc();

    // Count siren triggers in period
    @Query("SELECT COUNT(d) FROM Detection d WHERE d.sirenTriggered = true AND d.detectedAt >= :start AND d.detectedAt < :end")
    long countSirenTriggered(@Param("start") OffsetDateTime start, @Param("end") OffsetDateTime end);
}
