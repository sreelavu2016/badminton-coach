package com.badminton.feedback.dto;

import lombok.Data;

@Data
public class FeedbackItemRequest {
    private String category;
    private String severity;
    private String message;
    private String detail;
    private String faultyFrameUrl;
    private String idealFrameUrl;
    private Double frameTimestampSec;
}
