package com.badminton.video.service;

import com.badminton.video.event.VideoUploadedEvent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;

import java.util.concurrent.CompletableFuture;

@Service
@RequiredArgsConstructor
@Slf4j
public class KafkaProducerService {

    private final KafkaTemplate<String, VideoUploadedEvent> kafkaTemplate;

    @Value("${app.kafka.topic.video-uploaded}")
    private String videoUploadedTopic;

    public void publishVideoUploadedEvent(VideoUploadedEvent event) {
        CompletableFuture<SendResult<String, VideoUploadedEvent>> future =
                kafkaTemplate.send(videoUploadedTopic, event.getVideoId(), event);

        future.whenComplete((result, ex) -> {
            if (ex == null) {
                log.info("Published VIDEO_UPLOADED event for videoId={} to topic={} partition={} offset={}",
                        event.getVideoId(),
                        result.getRecordMetadata().topic(),
                        result.getRecordMetadata().partition(),
                        result.getRecordMetadata().offset());
            } else {
                log.error("Failed to publish VIDEO_UPLOADED event for videoId={}: {}",
                        event.getVideoId(), ex.getMessage(), ex);
            }
        });
    }
}
