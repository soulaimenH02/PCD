package com.farmwatch.repository;

import com.farmwatch.entity.Sector;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface SectorRepository extends JpaRepository<Sector, Integer> {
    List<Sector> findByActiveTrue();
}
