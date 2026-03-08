import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { VideoService } from '../../services/video.service';

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="upload-container">
      <div class="page-header">
        <h1>Upload Practice Video</h1>
        <p>Upload your badminton practice video to receive AI-powered technique analysis</p>
      </div>

      <div class="upload-card"
           [class.drag-over]="isDragOver"
           (dragover)="onDragOver($event)"
           (dragleave)="isDragOver = false"
           (drop)="onDrop($event)"
           (click)="fileInput.click()">

        <input #fileInput type="file" accept=".mp4,.mov,video/mp4,video/quicktime"
               (change)="onFileSelected($event)" style="display:none">

        <div class="upload-content" *ngIf="state === 'idle' || state === 'error'">
          <div class="upload-icon">📹</div>
          <h2>Drag & Drop your video here</h2>
          <p>or click to browse</p>
          <div class="upload-specs">
            <span>MP4, MOV supported</span>
            <span>Maximum 60 seconds</span>
            <span>Up to 500 MB</span>
          </div>
          <div class="error-msg" *ngIf="errorMessage">{{ errorMessage }}</div>
        </div>

        <div class="upload-content" *ngIf="state === 'uploading'">
          <div class="spinner"></div>
          <h2>Uploading & queuing analysis...</h2>
          <p>{{ selectedFile?.name }}</p>
          <div class="progress-bar">
            <div class="progress-fill" [style.width.%]="uploadProgress"></div>
          </div>
        </div>

        <div class="upload-content success" *ngIf="state === 'success'">
          <div class="success-icon">✅</div>
          <h2>Video uploaded successfully!</h2>
          <p>Redirecting to analysis dashboard...</p>
        </div>
      </div>

      <div class="file-preview" *ngIf="selectedFile && state === 'idle'">
        <div class="file-info">
          <span class="file-name">📄 {{ selectedFile.name }}</span>
          <span class="file-size">{{ formatSize(selectedFile.size) }}</span>
        </div>
        <button class="btn-primary" (click)="upload(); $event.stopPropagation()">
          Analyze Technique
        </button>
      </div>

      <div class="tips-section">
        <h3>Tips for best results</h3>
        <ul>
          <li>Record from a side angle showing full body</li>
          <li>Ensure good lighting conditions</li>
          <li>Keep the camera stable throughout</li>
          <li>Include clear overhead smash or serve motions</li>
        </ul>
      </div>
    </div>
  `,
  styles: [`
    .upload-container {
      max-width: 700px;
      margin: 0 auto;
    }
    .page-header {
      text-align: center;
      margin-bottom: 2rem;
    }
    .page-header h1 {
      font-size: 2rem;
      font-weight: 700;
      color: #7c83fd;
      margin: 0 0 0.5rem;
    }
    .page-header p { color: #90a4ae; margin: 0; }

    .upload-card {
      border: 2px dashed #3d3d6e;
      border-radius: 16px;
      padding: 3rem 2rem;
      text-align: center;
      cursor: pointer;
      transition: all 0.3s;
      background: #12122a;
      min-height: 220px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .upload-card:hover, .upload-card.drag-over {
      border-color: #7c83fd;
      background: #1a1a3e;
    }
    .upload-content { width: 100%; }
    .upload-icon { font-size: 3rem; margin-bottom: 1rem; }
    .upload-content h2 { color: #e8eaf6; margin: 0 0 0.5rem; font-size: 1.3rem; }
    .upload-content p { color: #90a4ae; margin: 0 0 1rem; }
    .upload-specs {
      display: flex;
      gap: 1rem;
      justify-content: center;
      flex-wrap: wrap;
    }
    .upload-specs span {
      background: #1e2048;
      padding: 0.3rem 0.8rem;
      border-radius: 20px;
      font-size: 0.8rem;
      color: #7c83fd;
    }

    .error-msg {
      margin-top: 1rem;
      color: #ef5350;
      font-size: 0.9rem;
      background: rgba(239,83,80,0.1);
      padding: 0.5rem 1rem;
      border-radius: 8px;
    }

    .spinner {
      width: 48px;
      height: 48px;
      border: 4px solid #2d2d5e;
      border-top-color: #7c83fd;
      border-radius: 50%;
      animation: spin 0.9s linear infinite;
      margin: 0 auto 1rem;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .progress-bar {
      width: 100%;
      height: 6px;
      background: #2d2d5e;
      border-radius: 3px;
      margin-top: 1rem;
      overflow: hidden;
    }
    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #7c83fd, #00b4d8);
      border-radius: 3px;
      transition: width 0.3s;
    }

    .success-icon { font-size: 3rem; margin-bottom: 1rem; }
    .upload-content.success h2 { color: #66bb6a; }

    .file-preview {
      margin-top: 1.5rem;
      background: #12122a;
      border: 1px solid #2d2d5e;
      border-radius: 12px;
      padding: 1rem 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .file-info { display: flex; flex-direction: column; gap: 0.2rem; }
    .file-name { color: #e8eaf6; font-size: 0.9rem; }
    .file-size { color: #7986cb; font-size: 0.8rem; }

    .btn-primary {
      background: linear-gradient(135deg, #7c83fd, #00b4d8);
      color: white;
      border: none;
      padding: 0.7rem 1.5rem;
      border-radius: 8px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity 0.2s;
      white-space: nowrap;
    }
    .btn-primary:hover { opacity: 0.88; }

    .tips-section {
      margin-top: 2rem;
      background: #12122a;
      border: 1px solid #2d2d5e;
      border-radius: 12px;
      padding: 1.5rem;
    }
    .tips-section h3 { color: #7c83fd; margin: 0 0 1rem; }
    .tips-section ul { margin: 0; padding-left: 1.2rem; color: #90a4ae; }
    .tips-section li { margin-bottom: 0.4rem; }
  `]
})
export class UploadComponent {
  private videoService = inject(VideoService);
  private router = inject(Router);

  selectedFile: File | null = null;
  state: UploadState = 'idle';
  errorMessage = '';
  isDragOver = false;
  uploadProgress = 0;

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = true;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver = false;
    const file = event.dataTransfer?.files[0];
    if (file) this.setFile(file);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) this.setFile(file);
  }

  setFile(file: File): void {
    const allowed = ['video/mp4', 'video/quicktime'];
    if (!allowed.includes(file.type)) {
      this.errorMessage = 'Unsupported format. Please upload MP4 or MOV.';
      this.state = 'error';
      return;
    }
    this.selectedFile = file;
    this.errorMessage = '';
    this.state = 'idle';
  }

  upload(): void {
    if (!this.selectedFile) return;
    this.state = 'uploading';
    this.uploadProgress = 0;

    // Simulate progress while uploading
    const progressInterval = setInterval(() => {
      if (this.uploadProgress < 85) this.uploadProgress += 10;
    }, 300);

    this.videoService.uploadVideo(this.selectedFile).subscribe({
      next: (response) => {
        clearInterval(progressInterval);
        this.uploadProgress = 100;
        this.state = 'success';
        setTimeout(() => this.router.navigate(['/dashboard', response.videoId]), 1500);
      },
      error: (err) => {
        clearInterval(progressInterval);
        this.state = 'error';
        this.errorMessage = 'Upload failed. Please check the server and try again.';
        console.error('Upload error', err);
      }
    });
  }

  formatSize(bytes: number): string {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}
