// src/app/services/api.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  DashboardSummary, HourlyChart, WeeklyHeatmap,
  MethodBreakdown, Detection, PagedResponse,
  SirenStatus, Camera
} from '../models/detection.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = 'http://localhost:8082/api';

  constructor(private http: HttpClient) {}

  // ── Stats ────────────────────────────────────────────────────────────────
  getSummary(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(`${this.base}/stats/summary`);
  }
  getHourlyChart(): Observable<HourlyChart> {
    return this.http.get<HourlyChart>(`${this.base}/stats/hourly`);
  }
  getWeeklyHeatmap(): Observable<WeeklyHeatmap> {
    return this.http.get<WeeklyHeatmap>(`${this.base}/stats/weekly`);
  }
  getMethodBreakdown(): Observable<MethodBreakdown> {
    return this.http.get<MethodBreakdown>(`${this.base}/stats/methods`);
  }

  // ── Detections ───────────────────────────────────────────────────────────
  getDetections(page = 0, size = 20): Observable<PagedResponse<Detection>> {
    const params = new HttpParams().set('page', page).set('size', size);
    return this.http.get<PagedResponse<Detection>>(`${this.base}/detections`, { params });
  }

  // ── Siren ────────────────────────────────────────────────────────────────
  getSirenStatus(): Observable<SirenStatus> {
    return this.http.get<SirenStatus>(`${this.base}/siren/status`);
  }
  activateSiren(triggeredBy = 'user'): Observable<any> {
    return this.http.post(`${this.base}/siren/activate`, { triggeredBy });
  }
  stopSiren(): Observable<any> {
    return this.http.post(`${this.base}/siren/stop`, {});
  }
  setSirenMode(mode: string): Observable<any> {
    return this.http.post(`${this.base}/siren/mode`, { mode });
  }

  // ── Cameras ──────────────────────────────────────────────────────────────
  getCameras(): Observable<Camera[]> {
    return this.http.get<Camera[]>(`${this.base}/camera`);
  }
  switchCamera(sector: string): Observable<any> {
    return this.http.post(`${this.base}/camera/switch`, { sector });
  }
}
