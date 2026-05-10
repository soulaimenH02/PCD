// src/app/models/detection.model.ts

export type DetectionMethod = 'CAMERA' | 'SOUND' | 'BOTH';
export type SirenMode = 'AUTO' | 'MANUAL' | 'DISABLED';

export interface DashboardSummary {
  detectionsToday: number;
  detectionsThisWeek: number;
  sirenTriggersToday: number;
  lastDetectionAt: string | null;
  sirenMode: SirenMode;
  sirenActive: boolean;
}

export interface HourSlot {
  hour: number;
  count: number;
}

export interface HourlyChart {
  slots: HourSlot[];
}

export interface WeeklyHeatmap {
  data: Record<string, number>; // "dow-hour" -> count
  maxValue: number;
}

export interface MethodBreakdown {
  cameraCount: number;
  soundCount: number;
  bothCount: number;
  total: number;
  cameraPercent: number;
  soundPercent: number;
  bothPercent: number;
}

export interface Detection {
  id: string;
  detectedAt: string;
  method: DetectionMethod;
  confidence: number;
  speciesEst: string | null;
  sectorCode: string;
  sectorName: string;
  sirenTriggered: boolean;
  durationSecs: number | null;
  imagePath: string | null;
}

export interface PagedResponse<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  number: number;
  size: number;
}

export interface SirenStatus {
  active: boolean;
  mode: SirenMode;
  activeSince: string | null;
  currentEventId: number | null;
}

export interface DetectionEvent {
  detectionId: string;
  detectedAt: string;
  method: DetectionMethod;
  confidence: number;
  speciesEst: string | null;
  sectorCode: string;
  sirenTriggered: boolean;
  bboxX?: number;
  bboxY?: number;
  bboxW?: number;
  bboxH?: number;
}

export interface Camera {
  id: number;
  name: string;
  sectorCode: string;
  streamUrl: string;
  active: boolean;
}
