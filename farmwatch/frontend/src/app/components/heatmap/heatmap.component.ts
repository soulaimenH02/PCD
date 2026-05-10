// src/app/components/heatmap/heatmap.component.ts
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { ApiService } from '../../services/api.service';
import { WeeklyHeatmap, MethodBreakdown } from '../../models/detection.model';

interface Cell {
  key: string;
  count: number;
  opacity: number;
}

@Component({
  selector: 'app-heatmap',
  templateUrl: './heatmap.component.html',
  styleUrls: ['./heatmap.component.scss'],
})
export class HeatmapComponent implements OnInit, OnDestroy {
  rows: Cell[][] = [];   // rows[hourIdx][dowIdx]
  hours = ['06','08','10','12','14','16','18','20'];
  days  = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];

  breakdown!: MethodBreakdown;

  private sub = new Subscription();

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.sub.add(
      this.api.getWeeklyHeatmap().subscribe(hm => this.buildGrid(hm))
    );
    this.sub.add(
      this.api.getMethodBreakdown().subscribe(b => (this.breakdown = b))
    );
  }

  private buildGrid(hm: WeeklyHeatmap): void {
    const displayHours = [6, 8, 10, 12, 14, 16, 18, 20];
    this.rows = displayHours.map(h =>
      [1, 2, 3, 4, 5, 6, 7].map(dow => {
        const key   = `${dow}-${h}`;
        const count = hm.data[key] ?? 0;
        const opacity = hm.maxValue > 0 ? 0.05 + (count / hm.maxValue) * 0.75 : 0.05;
        return { key, count, opacity };
      })
    );
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }
}
