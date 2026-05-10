// src/app/components/hourly-chart/hourly-chart.component.ts
import { Component, OnInit, OnDestroy, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { Subscription, interval } from 'rxjs';
import { startWith, switchMap } from 'rxjs/operators';
import { ApiService } from '../../services/api.service';
import { HourSlot } from '../../models/detection.model';

@Component({
  selector: 'app-hourly-chart',
  templateUrl: './hourly-chart.component.html',
  styleUrls: ['./hourly-chart.component.scss'],
})
export class HourlyChartComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  slots: HourSlot[] = [];
  private sub = new Subscription();
  private canvasReady = false;

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.sub.add(
      interval(60_000).pipe(startWith(0), switchMap(() => this.api.getHourlyChart()))
        .subscribe(chart => {
          this.slots = chart.slots;
          if (this.canvasReady) this.draw();
        })
    );
  }

  ngAfterViewInit(): void {
    this.canvasReady = true;
    if (this.slots.length) this.draw();
  }

  private draw(): void {
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width  = rect.width  * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const W = rect.width;
    const H = rect.height;
    const pad = { t: 8, r: 4, b: 20, l: 4 };
    const chartW = W - pad.l - pad.r;
    const chartH = H - pad.t - pad.b;

    ctx.clearRect(0, 0, W, H);

    const max = Math.max(...this.slots.map(s => s.count), 1);
    const barW = (chartW / this.slots.length) - 2;

    this.slots.forEach((slot, i) => {
      const barH = (slot.count / max) * chartH;
      const x = pad.l + i * (chartW / this.slots.length);
      const y = pad.t + chartH - barH;

      const isPeak = slot.count === max && slot.count > 0;
      ctx.fillStyle = isPeak
        ? 'rgba(201, 75, 30, 0.7)'
        : 'rgba(201, 75, 30, 0.22)';
      ctx.beginPath();
      ctx.roundRect(x + 1, Math.max(y, pad.t), barW, Math.max(barH, 1), [2, 2, 0, 0]);
      ctx.fill();

      // Hour labels every 4 hours
      if (slot.hour % 4 === 0) {
        ctx.fillStyle = 'rgba(122, 120, 112, 0.8)';
        ctx.font = '8px "Space Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(`${slot.hour}h`, x + barW / 2, H - 4);
      }
    });
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }
}
