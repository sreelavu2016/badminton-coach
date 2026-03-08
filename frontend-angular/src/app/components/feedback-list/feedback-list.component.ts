import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FeedbackItem } from '../../models/video.model';

@Component({
  selector: 'app-feedback-list',
  standalone: true,
  imports: [CommonModule],
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
        </div>
        <div class="feedback-message">{{ item.message }}</div>
        <div class="feedback-detail" *ngIf="item.detail">{{ item.detail }}</div>
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
    }
  `]
})
export class FeedbackListComponent {
  @Input() items: FeedbackItem[] = [];

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
