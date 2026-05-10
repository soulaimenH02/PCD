// src/app/components/camera/camera.component.ts — REPLACE existing
import { Component, Input, OnInit, OnChanges, OnDestroy, SimpleChanges } from '@angular/core';
import { Subscription } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { DetectionEvent } from '../../models/detection.model';

interface CameraSource {
  id: string;
  label: string;
  streamUrl: string;    // shown as <img src>
  snapshotUrl: string;
  directStreamUrl: string;  // for manual refresh
}

@Component({
  selector: 'app-camera',
  templateUrl: './camera.component.html',
  styleUrls: ['./camera.component.scss'],
})
export class CameraComponent implements OnInit, OnChanges, OnDestroy {
  @Input() latestEvent: DetectionEvent | null = null;

  // Configure your camera sources here
  // The Spring Boot backend proxies these so Angular doesn't hit CORS
 sources: CameraSource[] = [
  {
    id: 'espcam',
    label: 'ESP-CAM',
    streamUrl: 'http://192.168.100.37:81/stream',
snapshotUrl: 'http://192.168.100.37:81/capture',
    directStreamUrl: 'http://192.168.100.37:81/stream',  // ← ESP-CAM IP
  },
  {
    id: 'pi',
    label: 'Pi Camera',
    streamUrl: 'http://localhost:8082/api/camera/live-stream?source=pi',
    snapshotUrl: 'http://localhost:8082/api/camera/snapshot?source=pi',
    directStreamUrl: 'http://192.168.100.35:4000/stream',  // ← Pi Flask
  },
];

  selectedSource: CameraSource = this.sources[0];
  streamError = false;
  birdDetected = false;
  detectionLabel = '';
  showBbox = false;
  bbox = { x: 0, y: 0, w: 0, h: 0 };

  // Add auth token to stream URL so the backend accepts it
 // get authenticatedStreamUrl(): string {
   // const token = this.auth.getToken();
    //return `${this.selectedSource.streamUrl}&token=${token}`;
  //}
get authenticatedStreamUrl(): string {
  return this.selectedSource.streamUrl;
}
  private detectionTimeout: any;

  constructor(private auth: AuthService) {}

  ngOnInit(): void {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['latestEvent'] && this.latestEvent) {
      this.showDetection(this.latestEvent);
    }
  }

  selectSource(source: CameraSource): void {
    this.selectedSource = source;
    this.streamError = false;
  }

  onStreamError(): void {
    this.streamError = true;
  }

  private showDetection(event: DetectionEvent): void {
    this.birdDetected = true;
    this.detectionLabel = `${event.speciesEst ?? 'Bird'} ${event.confidence.toFixed(0)}%`;

    if (event.bboxX != null) {
      this.bbox = { x: event.bboxX, y: event.bboxY!, w: event.bboxW!, h: event.bboxH! };
      this.showBbox = true;
    }

    clearTimeout(this.detectionTimeout);
    this.detectionTimeout = setTimeout(() => {
      this.birdDetected = false;
      this.showBbox = false;
    }, 5000);
  }

  ngOnDestroy(): void {
    clearTimeout(this.detectionTimeout);
  }
}
