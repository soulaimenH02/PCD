// src/app/components/dashboard/dashboard.component.ts — REPLACE existing
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription, interval } from 'rxjs';
import { switchMap, startWith } from 'rxjs/operators';
import { ApiService }    from '../../services/api.service';
import { WebSocketService } from '../../services/websocket.service';
import { AuthService }   from '../../services/auth.service';
import { DashboardSummary, DetectionEvent } from '../../models/detection.model';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit, OnDestroy {
  summary!: DashboardSummary;
  wsConnected = false;
  currentTime = new Date();
  latestEvent: DetectionEvent | null = null;
  showChangePassword = false;

  private subs = new Subscription();

  constructor(
    private api: ApiService,
    private ws: WebSocketService,
    public auth: AuthService
  ) {}

  ngOnInit(): void {
    this.subs.add(
      interval(30_000).pipe(startWith(0), switchMap(() => this.api.getSummary()))
        .subscribe(s => (this.summary = s))
    );
    this.subs.add(
      interval(1000).subscribe(() => (this.currentTime = new Date()))
    );
    this.subs.add(
      this.ws.detectionEvents$.subscribe(event => {
        this.latestEvent = event;
        this.api.getSummary().subscribe(s => (this.summary = s));
      })
    );
    this.subs.add(
      this.ws.sirenStatus$.subscribe(status => {
        if (this.summary) {
          this.summary.sirenActive = status.active;
          this.summary.sirenMode   = status.mode;
        }
      })
    );
    this.subs.add(this.ws.connected$.subscribe(c => (this.wsConnected = c)));
  }

  ngOnDestroy(): void { this.subs.unsubscribe(); }

  get formattedTime(): string {
    return this.currentTime.toLocaleTimeString('en-GB', { hour12: false });
  }

  logout(): void { this.auth.logout(); }
}
