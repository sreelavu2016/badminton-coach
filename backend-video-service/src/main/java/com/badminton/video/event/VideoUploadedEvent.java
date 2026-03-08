package com.badminton.video.event;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class VideoUploadedEvent {
    private String eventType;
    private String videoId;
    private String userId;
    private String videoUrl;
    private String originalFilename;
    private Long fileSizeBytes;
    private LocalDateTime uploadTime;
}
