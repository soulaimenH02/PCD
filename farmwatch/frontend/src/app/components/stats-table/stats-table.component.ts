// src/app/components/stats-table/stats-table.component.ts
import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { Detection } from '../../models/detection.model';

@Component({
  selector: 'app-stats-table',
  templateUrl: './stats-table.component.html',
  styleUrls: ['./stats-table.component.scss'],
})
export class StatsTableComponent implements OnInit {
  detections: Detection[] = [];
  totalElements = 0;
  totalPages = 0;
  currentPage = 0;
  pageSize = 20;
  loading = false;

  // Sorting
  sortCol: keyof Detection = 'detectedAt';
  sortDir: 'asc' | 'desc' = 'desc';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.api.getDetections(this.currentPage, this.pageSize).subscribe({
      next: page => {
        this.detections    = page.content;
        this.totalElements = page.totalElements;
        this.totalPages    = page.totalPages;
        this.loading       = false;
      },
      error: () => (this.loading = false),
    });
  }

  goToPage(page: number): void {
    if (page < 0 || page >= this.totalPages) return;
    this.currentPage = page;
    this.load();
  }

  sort(col: keyof Detection): void {
    if (this.sortCol === col) {
      this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortCol = col;
      this.sortDir = 'desc';
    }
    // Client-side sort on current page
    this.detections = [...this.detections].sort((a, b) => {
      const va = a[col] ?? '';
      const vb = b[col] ?? '';
      const cmp = String(va).localeCompare(String(vb));
      return this.sortDir === 'asc' ? cmp : -cmp;
    });
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('en-GB');
  }

  formatTime(iso: string): string {
    return new Date(iso).toLocaleTimeString('en-GB', { hour12: false });
  }

  formatDuration(secs: number | null): string {
    if (!secs) return '—';
    return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m ${secs % 60}s`;
  }

  confidenceClass(conf: number): string {
    if (conf >= 90) return 'high';
    if (conf >= 75) return 'mid';
    return 'low';
  }

  get pages(): number[] {
    return Array.from({ length: this.totalPages }, (_, i) => i);
  }
}
