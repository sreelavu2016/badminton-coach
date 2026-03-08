package com.badminton.video.controller;

import com.badminton.video.dto.VideoUploadResponse;
import com.badminton.video.service.VideoService;
import com.badminton.video.service.VideoStorageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.InputStreamResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.util.Map;

@RestController
@RequestMapping("/api/videos")
@RequiredArgsConstructor
@Slf4j
@CrossOrigin(origins = "*")
public class VideoController {

    private final VideoService videoService;
    private final VideoStorageService videoStorageService;

    /**
     * Upload a badminton practice video.
     * curl -X POST http://localhost:8081/api/videos/upload
     *      -F "file=@/path/to/video.mp4"
     *      -F "userId=user123"
     */
    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<VideoUploadResponse> uploadVideo(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "userId", defaultValue = "anonymous") String userId) {

        log.info("Received upload request: filename={} size={} userId={}",
                file.getOriginalFilename(), file.getSize(), userId);

        try {
            VideoUploadResponse response = videoService.uploadVideo(file, userId);
            return ResponseEntity.status(HttpStatus.CREATED).body(response);
        } catch (IllegalArgumentException e) {
            log.warn("Validation error: {}", e.getMessage());
            return ResponseEntity.badRequest().build();
        } catch (IOException e) {
            log.error("Storage error during upload", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        }
    }

    /**
     * Get video metadata.
     */
    @GetMapping("/{videoId}")
    public ResponseEntity<VideoUploadResponse> getVideo(@PathVariable String videoId) {
        try {
            VideoUploadResponse response = videoService.getVideo(videoId);
            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * Stream / download a video file.
     */
    @GetMapping("/{videoId}/stream")
    public ResponseEntity<Resource> streamVideo(@PathVariable String videoId) {
        try {
            VideoUploadResponse videoMeta = videoService.getVideo(videoId);
            InputStream stream = videoStorageService.openVideoStream(videoMeta.getVideoUrl());
            String filename = videoMeta.getVideoUrl().substring(
                    videoMeta.getVideoUrl().lastIndexOf('/') + 1);
            Resource resource = new InputStreamResource(stream);
            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + filename + "\"")
                    .contentType(MediaType.parseMediaType("video/mp4"))
                    .body(resource);
        } catch (IOException e) {
            log.error("Error streaming video {}: {}", videoId, e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).build();
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * Health check.
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP", "service", "video-service"));
    }
}
