package com.badminton.feedback.controller;

import com.badminton.feedback.dto.AnalysisResultRequest;
import com.badminton.feedback.dto.AnalysisResultResponse;
import com.badminton.feedback.service.AnalysisService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/analysis")
@RequiredArgsConstructor
@Slf4j
@CrossOrigin(origins = "*")
public class AnalysisController {

    private final AnalysisService analysisService;

    /**
     * Called by the Python AI service after analysis is complete.
     */
    @PostMapping
    public ResponseEntity<AnalysisResultResponse> saveAnalysis(
            @Valid @RequestBody AnalysisResultRequest request) {
        log.info("Received analysis result for videoId={}", request.getVideoId());
        AnalysisResultResponse response = analysisService.saveAnalysis(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    /**
     * Called by Angular frontend to retrieve results.
     * GET /api/analysis/{videoId}
     */
    @GetMapping("/{videoId}")
    public ResponseEntity<AnalysisResultResponse> getAnalysis(@PathVariable String videoId) {
        try {
            AnalysisResultResponse response = analysisService.getAnalysisByVideoId(videoId);
            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            log.warn("Analysis not found for videoId={}", videoId);
            return ResponseEntity.notFound().build();
        }
    }

    /**
     * Health check.
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP", "service", "feedback-service"));
    }
}
