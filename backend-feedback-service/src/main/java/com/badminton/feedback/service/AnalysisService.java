package com.badminton.feedback.service;

import com.badminton.feedback.dto.*;
import com.badminton.feedback.model.*;
import com.badminton.feedback.repository.AnalysisResultRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class AnalysisService {

    private final AnalysisResultRepository repository;

    @Transactional
    public AnalysisResultResponse saveAnalysis(AnalysisResultRequest request) {
        // Upsert: if a record exists for this video, update it
        AnalysisResult result = repository.findByVideoId(request.getVideoId())
                .orElse(AnalysisResult.builder()
                        .videoId(request.getVideoId())
                        .build());

        result.setUserId(request.getUserId());
        result.setSmashScore(request.getSmashScore());
        result.setServeScore(request.getServeScore());
        result.setFootworkScore(request.getFootworkScore());
        result.setPostureScore(request.getPostureScore());
        result.setOverallScore(request.getOverallScore());
        result.setMetricsJson(request.getMetricsJson());
        result.setAnalysisStatus(AnalysisStatus.COMPLETED);
        result.setAnalyzedAt(LocalDateTime.now());

        // Replace feedback items
        result.getFeedbackItems().clear();
        if (request.getFeedbackItems() != null) {
            List<FeedbackItem> items = request.getFeedbackItems().stream()
                    .map(req -> FeedbackItem.builder()
                            .analysisResult(result)
                            .category(FeedbackCategory.valueOf(req.getCategory().toUpperCase()))
                            .severity(FeedbackSeverity.valueOf(req.getSeverity().toUpperCase()))
                            .message(req.getMessage())
                            .detail(req.getDetail())
                            .build())
                    .collect(Collectors.toList());
            result.getFeedbackItems().addAll(items);
        }

        AnalysisResult saved = repository.save(result);
        log.info("Saved analysis for videoId={} overallScore={}", saved.getVideoId(), saved.getOverallScore());
        return toResponse(saved);
    }

    @Transactional(readOnly = true)
    public AnalysisResultResponse getAnalysisByVideoId(String videoId) {
        AnalysisResult result = repository.findByVideoId(videoId)
                .orElseThrow(() -> new RuntimeException("Analysis not found for videoId: " + videoId));
        return toResponse(result);
    }

    private AnalysisResultResponse toResponse(AnalysisResult r) {
        List<FeedbackItemResponse> items = r.getFeedbackItems().stream()
                .map(fi -> FeedbackItemResponse.builder()
                        .category(fi.getCategory().name())
                        .severity(fi.getSeverity().name())
                        .message(fi.getMessage())
                        .detail(fi.getDetail())
                        .build())
                .collect(Collectors.toList());

        return AnalysisResultResponse.builder()
                .analysisId(r.getAnalysisId())
                .videoId(r.getVideoId())
                .userId(r.getUserId())
                .smashScore(r.getSmashScore())
                .serveScore(r.getServeScore())
                .footworkScore(r.getFootworkScore())
                .postureScore(r.getPostureScore())
                .overallScore(r.getOverallScore())
                .analysisStatus(r.getAnalysisStatus())
                .analyzedAt(r.getAnalyzedAt())
                .feedbackItems(items)
                .build();
    }
}
