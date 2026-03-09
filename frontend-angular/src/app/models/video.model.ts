export interface VideoUploadResponse {
  videoId: string;
  userId: string;
  videoUrl: string;
  originalFilename: string;
  fileSizeBytes: number;
  status: 'UPLOADED' | 'PROCESSING' | 'ANALYZED' | 'FAILED';
  uploadTime: string;
  message: string;
}

export interface FeedbackItem {
  category: 'SMASH' | 'SERVE' | 'FOOTWORK' | 'POSTURE' | 'BALANCE' | 'RECOVERY';
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  message: string;
  detail: string;
  faultyFrameUrl?: string;
  idealFrameUrl?: string;
  frameTimestampSec?: number;
}

export interface AnalysisResult {
  analysisId: string;
  videoId: string;
  userId: string;
  smashScore: number;
  serveScore: number;
  footworkScore: number;
  postureScore: number;
  overallScore: number;
  analysisStatus: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  analyzedAt: string;
  feedbackItems: FeedbackItem[];
}
