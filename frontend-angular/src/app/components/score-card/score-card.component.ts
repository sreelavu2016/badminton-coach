import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-score-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="score-card">
      <div class="score-icon">{{ icon }}</div>
      <div class="score-label">{{ label }}</div>
      <div class="score-ring" [style]="ringStyle">
        <span class="score-value">{{ score }}</span>
      </div>
      <div class="score-bar">
        <div class="score-fill"
             [style.width.%]="score"
             [class]="scoreClass"></div>
      </div>
      <div class="score-grade" [class]="scoreClass">{{ grade }}</div>
    </div>
  `,
  styles: [`
    .score-card {
      background: #12122a;
      border: 1px solid #2d2d5e;
      border-radius: 16px;
      padding: 1.5rem;
      text-align: center;
      transition: transform 0.2s, border-color 0.2s;
    }
    .score-card:hover {
      transform: translateY(-3px);
      border-color: #7c83fd;
    }
    .score-icon { font-size: 2rem; margin-bottom: 0.5rem; }
    .score-label {
      font-size: 0.85rem;
      color: #90a4ae;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 1rem;
    }
    .score-ring {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      border: 6px solid;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1rem;
    }
    .score-value {
      font-size: 1.4rem;
      font-weight: 700;
      color: #e8eaf6;
    }
    .score-bar {
      height: 6px;
      background: #1e1e4a;
      border-radius: 3px;
      overflow: hidden;
      margin-bottom: 0.5rem;
    }
    .score-fill {
      height: 100%;
      border-radius: 3px;
      transition: width 1s ease;
    }
    .score-grade {
      font-size: 0.8rem;
      font-weight: 600;
    }
    .excellent { color: #66bb6a; background: #66bb6a; }
    .good { color: #42a5f5; background: #42a5f5; }
    .fair { color: #ffa726; background: #ffa726; }
    .poor { color: #ef5350; background: #ef5350; }
    .score-fill.excellent, .score-fill.good, .score-fill.fair, .score-fill.poor {
      color: transparent;
    }
    .score-ring.excellent { border-color: #66bb6a; }
    .score-ring.good { border-color: #42a5f5; }
    .score-ring.fair { border-color: #ffa726; }
    .score-ring.poor { border-color: #ef5350; }
  `]
})
export class ScoreCardComponent {
  @Input() label = '';
  @Input() icon = '';
  @Input() score = 0;

  get scoreClass(): string {
    if (this.score >= 80) return 'excellent';
    if (this.score >= 60) return 'good';
    if (this.score >= 40) return 'fair';
    return 'poor';
  }

  get grade(): string {
    if (this.score >= 80) return 'Excellent';
    if (this.score >= 60) return 'Good';
    if (this.score >= 40) return 'Fair';
    return 'Needs Work';
  }

  get ringStyle(): string {
    const colours: Record<string, string> = {
      excellent: '#66bb6a',
      good: '#42a5f5',
      fair: '#ffa726',
      poor: '#ef5350',
    };
    return `border-color: ${colours[this.scoreClass]}`;
  }
}
