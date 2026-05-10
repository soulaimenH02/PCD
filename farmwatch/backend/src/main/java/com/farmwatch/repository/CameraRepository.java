package com.farmwatch.repository;

import com.farmwatch.entity.Camera;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface CameraRepository extends JpaRepository<Camera, Integer> {
    List<Camera> findByActiveTrue();
    List<Camera> findBySectorIdAndActiveTrue(Integer sectorId);
}
