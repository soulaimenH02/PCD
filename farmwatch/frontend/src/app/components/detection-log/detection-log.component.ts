// src/app/components/detection-log/detection-log.component.ts
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Subscription } from 'rxjs';
import { WebSocketService } from '../../services/websocket.service';
import { DetectionEvent } from '../../models/detection.model';

interface LogEntry extends DetectionEvent {
  formattedTime: string;
}

@Component({
  selector: 'app-detection-log',
  templateUrl: './detection-log.component.html',
  styleUrls: ['./detection-log.component.scss'],
})
export class DetectionLogComponent implements OnInit, OnDestroy {
  entries: LogEntry[] = [];
  private sub = new Subscription();

  constructor(private ws: WebSocketService) {}

  ngOnInit(): void {
    this.sub.add(
      this.ws.detectionEvents$.subscribe(event => {
        const entry: LogEntry = {
          ...event,
          formattedTime: new Date(event.detectedAt).toLocaleTimeString('en-GB', { hour12: false }),
        };
        // Prepend and keep last 30
        this.entries = [entry, ...this.entries].slice(0, 30);
      })
    );
  }

  dotColor(method: string): string {
    switch (method) {
      case 'CAMERA': return '#4a8fc0';
      case 'SOUND':  return '#6aaa3a';
      case 'BOTH':   return 'var(--c-accent)';
      default:       return 'var(--c-muted)';
    }
  }

  ngOnDestroy(): void { this.sub.unsubscribe(); }
}
