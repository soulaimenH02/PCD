// src/app/components/siren/siren.component.ts
import { Component, Input, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { ApiService } from '../../services/api.service';
import { WebSocketService } from '../../services/websocket.service';
import { DashboardSummary, SirenMode } from '../../models/detection.model';

@Component({
  selector: 'app-siren',
  templateUrl: './siren.component.html',
  styleUrls: ['./siren.component.scss'],
})
export class SirenComponent implements OnInit, OnDestroy {
  @Input() summary!: DashboardSummary;

  sirenActive = false;
  sirenMode: SirenMode = 'AUTO';
  loading = false;
  modes: SirenMode[] = ['AUTO', 'MANUAL', 'DISABLED'];

  private sub = new Subscription();

  constructor(private api: ApiService, private ws: WebSocketService) {}

  ngOnInit(): void {
    // Sync from WebSocket status updates
    this.sub.add(
      this.ws.sirenStatus$.subscribe(status => {
        this.sirenActive = status.active;
        this.sirenMode   = status.mode;
      })
    );

    // Initial state from API
    this.api.getSirenStatus().subscribe(s => {
      this.sirenActive = s.active;
      this.sirenMode   = s.mode;
    });
  }

  toggleSiren(): void {
    this.loading = true;
    const action$ = this.sirenActive
      ? this.api.stopSiren()
      : this.api.activateSiren('operator');

    action$.subscribe({
      next: () => (this.loading = false),
      error: () => (this.loading = false),
    });
  }

  setMode(mode: SirenMode): void {
    this.api.setSirenMode(mode).subscribe(() => (this.sirenMode = mode));
  }

  get btnLabel(): string {
    if (this.loading) return '...';
    return this.sirenActive ? 'STOP' : 'ACTIVATE';
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }
}
