package com.badminton.feedback.model;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "analysis_results")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AnalysisResult {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "analysis_id")
    private String analysisId;

    @Column(name = "video_id", nullable = false, unique = true)
    private String videoId;

    @Column(name = "user_id")
    private String userId;

    // Scores 0–100
    @Column(name = "smash_score")
    private Integer smashScore;

    @Column(name = "serve_score")
    private Integer serveScore;

    @Column(name = "footwork_score")
    private Integer footworkScore;

    @Column(name = "posture_score")
    private Integer postureScore;

    @Column(name = "overall_score")
    private Integer overallScore;

    // Raw AI metrics stored as JSON text
    @Column(name = "metrics_json", columnDefinition = "TEXT")
    private String metricsJson;

    @Enumerated(EnumType.STRING)
    @Column(name = "analysis_status")
    private AnalysisStatus analysisStatus;

    @Column(name = "analyzed_at")
    private LocalDateTime analyzedAt;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @OneToMany(mappedBy = "analysisResult", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<FeedbackItem> feedbackItems = new ArrayList<>();

    @PrePersist
    public void prePersist() {
        createdAt = LocalDateTime.now();
        if (analysisStatus == null) analysisStatus = AnalysisStatus.PENDING;
    }
}
