package com.badminton.video.service;

import com.badminton.video.dto.VideoUploadResponse;
import com.badminton.video.event.VideoUploadedEvent;
import com.badminton.video.model.Video;
import com.badminton.video.model.VideoStatus;
import com.badminton.video.repository.VideoRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.Set;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class VideoService {

    private final VideoRepository videoRepository;
    private final VideoStorageService videoStorageService;
    private final KafkaProducerService kafkaProducerService;

    private static final Set<String> ALLOWED_FORMATS = Set.of("video/mp4", "video/quicktime");

    @Transactional
    public VideoUploadResponse uploadVideo(MultipartFile file, String userId) throws IOException {
        validateFile(file);

        String videoId = UUID.randomUUID().toString();
        String videoUrl = videoStorageService.storeVideo(videoId, file);

        Video video = Video.builder()
                .videoId(videoId)
                .userId(userId)
                .videoUrl(videoUrl)
                .originalFilename(file.getOriginalFilename())
                .fileSizeBytes(file.getSize())
                .contentType(file.getContentType())
                .status(VideoStatus.UPLOADED)
                .uploadTime(LocalDateTime.now())
                .build();

        videoRepository.save(video);
        log.info("Saved video record videoId={} for userId={}", videoId, userId);

        VideoUploadedEvent event = VideoUploadedEvent.builder()
                .eventType("VIDEO_UPLOADED")
                .videoId(videoId)
                .userId(userId)
                .videoUrl(videoUrl)
                .originalFilename(file.getOriginalFilename())
                .fileSizeBytes(file.getSize())
                .uploadTime(LocalDateTime.now())
                .build();

        kafkaProducerService.publishVideoUploadedEvent(event);

        return VideoUploadResponse.builder()
                .videoId(videoId)
                .userId(userId)
                .videoUrl(videoUrl)
                .originalFilename(file.getOriginalFilename())
                .fileSizeBytes(file.getSize())
                .status(VideoStatus.UPLOADED)
                .uploadTime(video.getUploadTime())
                .message("Video uploaded successfully. Analysis in progress.")
                .build();
    }

    @Transactional(readOnly = true)
    public VideoUploadResponse getVideo(String videoId) {
        Video video = videoRepository.findById(videoId)
                .orElseThrow(() -> new RuntimeException("Video not found: " + videoId));

        return VideoUploadResponse.builder()
                .videoId(video.getVideoId())
                .userId(video.getUserId())
                .videoUrl(video.getVideoUrl())
                .originalFilename(video.getOriginalFilename())
                .fileSizeBytes(video.getFileSizeBytes())
                .status(video.getStatus())
                .uploadTime(video.getUploadTime())
                .build();
    }

    @Transactional
    public void updateVideoStatus(String videoId, VideoStatus status) {
        videoRepository.findById(videoId).ifPresent(video -> {
            video.setStatus(status);
            videoRepository.save(video);
            log.info("Updated videoId={} status to {}", videoId, status);
        });
    }

    private void validateFile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("File is empty");
        }
        String contentType = file.getContentType();
        if (!ALLOWED_FORMATS.contains(contentType)) {
            throw new IllegalArgumentException(
                    "Unsupported format: " + contentType + ". Allowed: " + ALLOWED_FORMATS);
        }
        long maxBytes = 500L * 1024 * 1024; // 500 MB guard
        if (file.getSize() > maxBytes) {
            throw new IllegalArgumentException("File too large. Max 500 MB.");
        }
    }
}
