package com.badminton.feedback.dto;

import com.badminton.feedback.model.AnalysisStatus;
import lombok.Builder;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class AnalysisResultResponse {
    private String analysisId;
    private String videoId;
    private String userId;
    private Integer smashScore;
    private Integer serveScore;
    private Integer footworkScore;
    private Integer postureScore;
    private Integer overallScore;
    private AnalysisStatus analysisStatus;
    private LocalDateTime analyzedAt;
    private List<FeedbackItemResponse> feedbackItems;
}
