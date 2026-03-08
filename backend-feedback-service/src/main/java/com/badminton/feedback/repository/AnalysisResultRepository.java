package com.badminton.feedback.repository;

import com.badminton.feedback.model.AnalysisResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.Optional;

@Repository
public interface AnalysisResultRepository extends JpaRepository<AnalysisResult, String> {
    Optional<AnalysisResult> findByVideoId(String videoId);
}
