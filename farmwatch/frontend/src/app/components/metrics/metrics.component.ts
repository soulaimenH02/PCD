// src/app/components/metrics/metrics.component.ts
import { Component, Input } from '@angular/core';
import { DashboardSummary } from '../../models/detection.model';

@Component({
  selector: 'app-metrics',
  templateUrl: './metrics.component.html',
  styleUrls: ['./metrics.component.scss'],
})
export class MetricsComponent {
  @Input() summary!: DashboardSummary;

  get lastDetection(): string {
    if (!this.summary?.lastDetectionAt) return '—';
    const d = new Date(this.summary.lastDetectionAt);
    return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  }
}
