import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { interval, Subscription, switchMap, catchError, of, takeWhile } from 'rxjs';
import { VideoService } from '../../services/video.service';
import { AnalysisResult, VideoUploadResponse } from '../../models/video.model';
import { ScoreCardComponent } from '../../components/score-card/score-card.component';
import { FeedbackListComponent } from '../../components/feedback-list/feedback-list.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, ScoreCardComponent, FeedbackListComponent],
  template: `
    <div class="dashboard">

      <!-- Back + title -->
      <div class="page-header">
        <a routerLink="/upload" class="back-link">← Upload Another Video</a>
        <h1>Technique Analysis Dashboard</h1>
        <p class="video-id">Video ID: {{ videoId }}</p>
      </div>

      <!-- Loading State -->
      <div class="loading-state" *ngIf="!analysis && !loadError">
        <div class="spinner-large"></div>
        <h2>AI is analyzing your technique...</h2>
        <p>This usually takes 20–60 seconds depending on video length.</p>
        <div class="status-steps">
          <div class="step" [class.active]="true">📤 Video uploaded</div>
          <div class="step" [class.active]="true">⚙️ Frames extracted</div>
          <div class="step" [class.active]="pollingCount > 1">🦴 Pose detected</div>
          <div class="step" [class.active]="pollingCount > 3">📊 Scores calculated</div>
          <div class="step" [class.active]="!!analysis">✅ Analysis complete</div>
        </div>
      </div>

      <!-- Error State -->
      <div class="error-state" *ngIf="loadError">
        <div class="error-icon">⚠️</div>
        <h2>Analysis not ready yet</h2>
        <p>{{ loadError }}</p>
        <button class="btn-secondary" (click)="retry()">Retry</button>
      </div>

      <!-- Analysis Ready -->
      <div class="analysis-content" *ngIf="analysis">

        <!-- Overall Score Banner -->
        <div class="overall-banner">
          <div class="overall-label">Overall Score</div>
          <div class="overall-score" [class]="overallClass">{{ analysis.overallScore }}</div>
          <div class="overall-grade" [class]="overallClass">{{ overallGrade }}</div>
          <div class="overall-date">Analyzed: {{ analysis.analyzedAt | date:'medium' }}</div>
        </div>

        <!-- Score Cards Grid -->
        <div class="scores-grid">
          <app-score-card icon="💥" label="Smash" [score]="analysis.smashScore" />
          <app-score-card icon="🎾" label="Serve"  [score]="analysis.serveScore" />
          <app-score-card icon="👟" label="Footwork" [score]="analysis.footworkScore" />
          <app-score-card icon="🧍" label="Posture" [score]="analysis.postureScore" />
        </div>

        <!-- Video + Feedback Layout -->
        <div class="main-content-grid">

          <!-- Video Player -->
          <div class="video-section">
            <h3 class="section-title">Video Review</h3>
            <div class="video-wrapper">
              <video controls class="video-player" *ngIf="videoStreamUrl">
                <source [src]="videoStreamUrl" type="video/mp4">
                Your browser does not support video playback.
              </video>
            </div>

            <!-- Raw Metrics Summary -->
            <div class="metrics-summary" *ngIf="parsedMetrics">
              <h4>Raw AI Metrics</h4>
              <div class="metrics-grid">
                <div class="metric" *ngFor="let m of metricsEntries">
                  <span class="metric-key">{{ m.label }}</span>
                  <span class="metric-val">{{ m.value }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Feedback List -->
          <div class="feedback-section">
            <app-feedback-list [items]="analysis.feedbackItems" />
          </div>

        </div>
      </div>
    </div>
  `,
  styles: [`
    .dashboard { max-width: 1100px; margin: 0 auto; }

    .page-header { margin-bottom: 2rem; }
    .back-link {
      color: #7c83fd;
      text-decoration: none;
      font-size: 0.9rem;
      display: inline-block;
      margin-bottom: 0.75rem;
    }
    .back-link:hover { text-decoration: underline; }
    .page-header h1 {
      font-size: 1.8rem;
      color: #e8eaf6;
      margin: 0 0 0.25rem;
    }
    .video-id { color: #546e7a; font-size: 0.8rem; margin: 0; }

    /* Loading */
    .loading-state {
      text-align: center;
      padding: 4rem 2rem;
    }
    .spinner-large {
      width: 64px;
      height: 64px;
      border: 5px solid #2d2d5e;
      border-top-color: #7c83fd;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 1.5rem;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .loading-state h2 { color: #e8eaf6; margin: 0 0 0.5rem; }
    .loading-state p { color: #78909c; }
    .status-steps {
      display: flex;
      gap: 0.5rem;
      justify-content: center;
      flex-wrap: wrap;
      margin-top: 1.5rem;
    }
    .step {
      padding: 0.4rem 0.9rem;
      border-radius: 20px;
      font-size: 0.8rem;
      background: #12122a;
      border: 1px solid #2d2d5e;
      color: #546e7a;
      transition: all 0.3s;
    }
    .step.active { border-color: #7c83fd; color: #7c83fd; background: #1a1a3e; }

    /* Error */
    .error-state {
      text-align: center;
      padding: 3rem;
    }
    .error-icon { font-size: 3rem; margin-bottom: 1rem; }
    .error-state h2 { color: #ef5350; }
    .btn-secondary {
      margin-top: 1rem;
      background: transparent;
      border: 2px solid #7c83fd;
      color: #7c83fd;
      padding: 0.6rem 1.5rem;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.9rem;
    }
    .btn-secondary:hover { background: #1a1a3e; }

    /* Overall Banner */
    .overall-banner {
      background: linear-gradient(135deg, #1a1a3e 0%, #16213e 100%);
      border: 1px solid #2d2d5e;
      border-radius: 16px;
      padding: 2rem;
      text-align: center;
      margin-bottom: 2rem;
    }
    .overall-label { color: #90a4ae; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.1em; }
    .overall-score {
      font-size: 5rem;
      font-weight: 800;
      line-height: 1;
      margin: 0.5rem 0;
    }
    .overall-grade { font-size: 1.2rem; font-weight: 600; }
    .overall-date { color: #546e7a; font-size: 0.8rem; margin-top: 0.5rem; }

    .excellent { color: #66bb6a; }
    .good { color: #42a5f5; }
    .fair { color: #ffa726; }
    .poor { color: #ef5350; }

    /* Scores Grid */
    .scores-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }

    /* Main Content Grid */
    .main-content-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }
    @media (max-width: 768px) {
      .main-content-grid { grid-template-columns: 1fr; }
    }

    /* Video */
    .section-title {
      color: #7c83fd;
      margin: 0 0 1rem;
      font-size: 1.1rem;
    }
    .video-wrapper {
      background: #000;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid #2d2d5e;
    }
    .video-player {
      width: 100%;
      height: auto;
      display: block;
    }

    /* Metrics */
    .metrics-summary {
      margin-top: 1rem;
      background: #12122a;
      border: 1px solid #2d2d5e;
      border-radius: 10px;
      padding: 1rem;
    }
    .metrics-summary h4 { color: #7c83fd; margin: 0 0 0.75rem; font-size: 0.9rem; }
    .metrics-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.4rem;
    }
    .metric {
      display: flex;
      justify-content: space-between;
      font-size: 0.78rem;
      padding: 0.3rem 0;
      border-bottom: 1px solid #1e1e3a;
    }
    .metric-key { color: #78909c; }
    .metric-val { color: #e8eaf6; font-weight: 600; }
  `]
})
export class DashboardComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private videoService = inject(VideoService);

  videoId = '';
  analysis: AnalysisResult | null = null;
  loadError = '';
  pollingCount = 0;
  videoStreamUrl = '';
  parsedMetrics: Record<string, unknown> | null = null;
  metricsEntries: { label: string; value: string }[] = [];

  private pollSub: Subscription | null = null;

  ngOnInit(): void {
    this.videoId = this.route.snapshot.paramMap.get('videoId') ?? '';
    this.videoStreamUrl = this.videoService.getVideoStreamUrl(this.videoId);
    this.startPolling();
  }

  startPolling(): void {
    this.pollSub = interval(4000).pipe(
      takeWhile(() => !this.analysis),
      switchMap(() => this.videoService.getAnalysis(this.videoId).pipe(
        catchError(() => of(null))
      ))
    ).subscribe(result => {
      this.pollingCount++;
      if (result && result.analysisStatus === 'COMPLETED') {
        this.analysis = result;
        this.buildMetrics(result);
        this.pollSub?.unsubscribe();
      }
    });

    // Also try immediately
    this.videoService.getAnalysis(this.videoId).pipe(
      catchError(() => of(null))
    ).subscribe(result => {
      if (result && result.analysisStatus === 'COMPLETED') {
        this.analysis = result;
        this.buildMetrics(result);
        this.pollSub?.unsubscribe();
      }
    });
  }

  buildMetrics(result: AnalysisResult): void {
    try {
      // metricsJson is not exposed in AnalysisResult but accessible from backend
      // Here we build display metrics from scores
      this.metricsEntries = [
        { label: 'Smash Score', value: `${result.smashScore}/100` },
        { label: 'Serve Score', value: `${result.serveScore}/100` },
        { label: 'Footwork Score', value: `${result.footworkScore}/100` },
        { label: 'Posture Score', value: `${result.postureScore}/100` },
        { label: 'Overall Score', value: `${result.overallScore}/100` },
        { label: 'Feedback Items', value: `${result.feedbackItems?.length ?? 0}` },
      ];
    } catch {
      // ignore
    }
  }

  retry(): void {
    this.loadError = '';
    this.analysis = null;
    this.pollingCount = 0;
    this.startPolling();
  }

  get overallClass(): string {
    const s = this.analysis?.overallScore ?? 0;
    if (s >= 80) return 'excellent';
    if (s >= 60) return 'good';
    if (s >= 40) return 'fair';
    return 'poor';
  }

  get overallGrade(): string {
    const s = this.analysis?.overallScore ?? 0;
    if (s >= 80) return 'Excellent Technique';
    if (s >= 60) return 'Good — Keep Improving';
    if (s >= 40) return 'Fair — Focused Practice Needed';
    return 'Needs Significant Improvement';
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }
}
