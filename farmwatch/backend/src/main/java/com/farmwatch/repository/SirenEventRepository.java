package com.farmwatch.repository;

import com.farmwatch.entity.SirenEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SirenEventRepository extends JpaRepository<SirenEvent, Integer> {
    SirenEvent findTopByStoppedAtIsNullOrderByTriggeredAtDesc();
}
