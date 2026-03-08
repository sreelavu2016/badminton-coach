package com.badminton.feedback.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class FeedbackItemResponse {
    private String category;
    private String severity;
    private String message;
    private String detail;
}
