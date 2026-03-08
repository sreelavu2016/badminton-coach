package com.badminton.video.dto;

import com.badminton.video.model.VideoStatus;
import lombok.Builder;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@Builder
public class VideoUploadResponse {
    private String videoId;
    private String userId;
    private String videoUrl;
    private String originalFilename;
    private Long fileSizeBytes;
    private VideoStatus status;
    private LocalDateTime uploadTime;
    private String message;
}
