package com.badminton.feedback.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import java.util.List;

@Data
public class AnalysisResultRequest {

    @NotBlank
    private String videoId;

    private String userId;

    @Min(0) @Max(100)
    private Integer smashScore;

    @Min(0) @Max(100)
    private Integer serveScore;

    @Min(0) @Max(100)
    private Integer footworkScore;

    @Min(0) @Max(100)
    private Integer postureScore;

    @Min(0) @Max(100)
    private Integer overallScore;

    private String metricsJson;

    private List<FeedbackItemRequest> feedbackItems;
}
