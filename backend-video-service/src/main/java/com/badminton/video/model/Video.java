package com.badminton.video.model;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "videos")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Video {

    @Id
    @Column(name = "video_id", length = 36)
    private String videoId;

    @Column(name = "user_id", nullable = false)
    private String userId;

    @Column(name = "video_url", nullable = false)
    private String videoUrl;

    @Column(name = "original_filename")
    private String originalFilename;

    @Column(name = "file_size_bytes")
    private Long fileSizeBytes;

    @Column(name = "content_type")
    private String contentType;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    private VideoStatus status;

    @Column(name = "upload_time", nullable = false)
    private LocalDateTime uploadTime;

    @Column(name = "updated_time")
    private LocalDateTime updatedTime;

    @PrePersist
    public void prePersist() {
        if (videoId == null) {
            videoId = UUID.randomUUID().toString();
        }
        if (uploadTime == null) {
            uploadTime = LocalDateTime.now();
        }
        if (status == null) {
            status = VideoStatus.UPLOADED;
        }
    }

    @PreUpdate
    public void preUpdate() {
        updatedTime = LocalDateTime.now();
    }
}
