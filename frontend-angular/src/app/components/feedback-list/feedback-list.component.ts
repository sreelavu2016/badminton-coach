import { Component, Input } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { FeedbackItem } from '../../models/video.model';
import { environment } from '../../../environments/environment';

const VIDEO_API = environment.videoApiUrl;

@Component({
  selector: 'app-feedback-list',
  standalone: true,
  imports: [CommonModule, DecimalPipe],
  template: `
    <div class="feedback-list">
      <h3 class="section-title">Improvement Suggestions</h3>

      <div *ngIf="!items || items.length === 0" class="empty-state">
        No feedback items available yet.
      </div>

      <div *ngFor="let item of items" class="feedback-item" [class]="item.severity.toLowerCase()">
        <div class="feedback-header">
          <span class="severity-badge" [class]="item.severity.toLowerCase()">
            {{ severityIcon(item.severity) }} {{ item.severity }}
          </span>
          <span class="category-badge">{{ categoryIcon(item.category) }} {{ item.category }}</span>
          <span class="timestamp" *ngIf="item.frameTimestampSec">
            &#x23F1; {{ item.frameTimestampSec | number:'1.1-1' }}s
          </span>
        </div>

        <div class="feedback-message">{{ item.message }}</div>
        <div class="feedback-detail" *ngIf="item.detail">{{ item.detail }}</div>

        <!-- Faulty vs Ideal frame comparison -->
        <div class="frame-comparison" *ngIf="item.faultyFrameUrl && item.idealFrameUrl">
          <div class="frame-pair">
            <div class="frame-box">
              <img [src]="resolveUrl(item.faultyFrameUrl)"
                   alt="Your posture"
                   loading="lazy"
                   (error)="onImgError($event)" />
              <div class="frame-label faulty-label">Your Posture</div>
            </div>
            <div class="frame-arrow">&#x279C;</div>
            <div class="frame-box">
              <img [src]="resolveUrl(item.idealFrameUrl)"
                   alt="Ideal posture"
                   loading="lazy"
                   (error)="onImgError($event)" />
              <div class="frame-label ideal-label">Ideal Posture</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .section-title {
      color: #7c83fd;
      margin: 0 0 1rem;
      font-size: 1.1rem;
    }
    .empty-state { color: #546e7a; text-align: center; padding: 2rem; }

    .feedback-item {
      background: #12122a;
      border-radius: 10px;
      padding: 1rem;
      margin-bottom: 0.75rem;
      border-left: 4px solid #2d2d5e;
      transition: border-color 0.2s;
    }
    .feedback-item.critical { border-left-color: #ef5350; }
    .feedback-item.warning  { border-left-color: #ffa726; }
    .feedback-item.info     { border-left-color: #42a5f5; }

    .feedback-header {
      display: flex;
      gap: 0.5rem;
      align-items: center;
      margin-bottom: 0.5rem;
      flex-wrap: wrap;
    }

    .severity-badge, .category-badge {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.2rem 0.6rem;
      border-radius: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .severity-badge.critical { background: rgba(239,83,80,0.15); color: #ef5350; }
    .severity-badge.warning  { background: rgba(255,167,38,0.15); color: #ffa726; }
    .severity-badge.info     { background: rgba(66,165,245,0.15); color: #42a5f5; }

    .category-badge {
      background: rgba(124,131,253,0.15);
      color: #7c83fd;
    }

    .timestamp {
      margin-left: auto;
      font-size: 0.7rem;
      color: #546e7a;
    }

    .feedback-message {
      color: #e8eaf6;
      font-size: 0.95rem;
      font-weight: 500;
      margin-bottom: 0.3rem;
    }
    .feedback-detail {
      color: #78909c;
      font-size: 0.83rem;
      line-height: 1.5;
      margin-bottom: 0.5rem;
    }

    /* ── Frame comparison ───────────────────────────────────── */
    .frame-comparison {
      margin-top: 0.75rem;
      padding-top: 0.75rem;
      border-top: 1px solid rgba(255,255,255,0.06);
    }

    .frame-pair {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .frame-box {
      flex: 1;
      position: relative;
      border-radius: 8px;
      overflow: hidden;
    }

    .frame-box img {
      width: 100%;
      display: block;
      border-radius: 8px;
    }

    .frame-label {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      text-align: center;
      font-size: 0.62rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 0.2rem;
    }
    .faulty-label { background: rgba(239,83,80,0.8);  color: #fff; }
    .ideal-label  { background: rgba(56,180,90,0.8);  color: #fff; }

    .frame-arrow {
      font-size: 1.5rem;
      color: #7c83fd;
      flex-shrink: 0;
    }
  `]
})
export class FeedbackListComponent {
  @Input() items: FeedbackItem[] = [];

  /**
   * Convert a relative storage path like 'storage/frames/{id}/faulty_knee_bend.jpg'
   * into a full Video Service API URL.
   */
  resolveUrl(relUrl: string): string {
    if (!relUrl) return '';
    if (relUrl.startsWith('http')) return relUrl;   // already absolute (Azure Blob)

    // relUrl = 'storage/frames/{videoId}/{filename}'
    const parts = relUrl.split('/');
    const videoId  = parts[parts.length - 2];
    const filename = parts[parts.length - 1];
    return `${VIDEO_API}/${videoId}/frames/${filename}`;
  }

  onImgError(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }

  severityIcon(s: string): string {
    return s === 'CRITICAL' ? '🔴' : s === 'WARNING' ? '🟡' : 'ℹ️';
  }

  categoryIcon(c: string): string {
    const icons: Record<string, string> = {
      SMASH: '💥', SERVE: '🎾', FOOTWORK: '👟',
      POSTURE: '🧍', BALANCE: '⚖️', RECOVERY: '🔄',
    };
    return icons[c] || '📌';
  }
}
