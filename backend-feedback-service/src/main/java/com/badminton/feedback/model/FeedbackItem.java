package com.badminton.feedback.model;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "feedback_items")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class FeedbackItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "analysis_id", nullable = false)
    private AnalysisResult analysisResult;

    @Enumerated(EnumType.STRING)
    @Column(name = "category", nullable = false)
    private FeedbackCategory category;

    @Enumerated(EnumType.STRING)
    @Column(name = "severity", nullable = false)
    private FeedbackSeverity severity;

    @Column(name = "message", nullable = false)
    private String message;

    @Column(name = "detail")
    private String detail;
}
