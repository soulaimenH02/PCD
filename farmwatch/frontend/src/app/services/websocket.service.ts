// src/app/services/websocket.service.ts
import { Injectable, OnDestroy } from '@angular/core';
import { Subject, BehaviorSubject } from 'rxjs';
import { DetectionEvent } from '../models/detection.model';
import { Client } from '@stomp/stompjs';

@Injectable({ providedIn: 'root' })
export class WebSocketService implements OnDestroy {
  private client!: Client;

  readonly detectionEvents$ = new Subject<DetectionEvent>();
  readonly sirenStatus$     = new Subject<any>();
  readonly connected$       = new BehaviorSubject<boolean>(false);

  constructor() {
    this.connect();
  }

  private connect(): void {
    this.client = new Client({
      // Use native WebSocket — no SockJS needed in dev
      brokerURL: 'ws://localhost:8082/ws/websocket',
      reconnectDelay: 5000,
      onConnect: () => {
        this.connected$.next(true);
        this.client.subscribe('/topic/detections', msg => {
          this.detectionEvents$.next(JSON.parse(msg.body));
        });
        this.client.subscribe('/topic/siren-status', msg => {
          this.sirenStatus$.next(JSON.parse(msg.body));
        });
      },
      onDisconnect: () => this.connected$.next(false),
      onStompError: frame => console.error('STOMP error', frame),
    });

    this.client.activate();
  }

  ngOnDestroy(): void {
    this.client?.deactivate();
  }
}