import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { VideoUploadResponse, AnalysisResult } from '../models/video.model';
import { environment } from '../../environments/environment';

const VIDEO_API = environment.videoApiUrl;
const ANALYSIS_API = environment.analysisApiUrl;

@Injectable({ providedIn: 'root' })
export class VideoService {
  private http = inject(HttpClient);

  uploadVideo(file: File, userId = 'anonymous'): Observable<VideoUploadResponse> {
    const form = new FormData();
    form.append('file', file);
    form.append('userId', userId);
    return this.http.post<VideoUploadResponse>(`${VIDEO_API}/upload`, form);
  }

  getVideo(videoId: string): Observable<VideoUploadResponse> {
    return this.http.get<VideoUploadResponse>(`${VIDEO_API}/${videoId}`);
  }

  getAnalysis(videoId: string): Observable<AnalysisResult> {
    return this.http.get<AnalysisResult>(`${ANALYSIS_API}/${videoId}`);
  }

  getVideoStreamUrl(videoId: string): string {
    return `${VIDEO_API}/${videoId}/stream`;
  }
}
