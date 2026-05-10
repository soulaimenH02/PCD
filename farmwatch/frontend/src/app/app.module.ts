// src/app/app.module.ts
import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { RouterModule, Routes } from '@angular/router';

import { AppComponent }            from './app.component';
import { LoginComponent }          from './components/login/login.component';
import { DashboardComponent }      from './components/dashboard/dashboard.component';
import { MetricsComponent }        from './components/metrics/metrics.component';
import { CameraComponent }         from './components/camera/camera.component';
import { SirenComponent }          from './components/siren/siren.component';
import { HourlyChartComponent }    from './components/hourly-chart/hourly-chart.component';
import { HeatmapComponent }        from './components/heatmap/heatmap.component';
import { StatsTableComponent }     from './components/stats-table/stats-table.component';
import { DetectionLogComponent }   from './components/detection-log/detection-log.component';
import { ChangePasswordComponent } from './components/change-password/change-password.component';

import { AuthGuard }       from './guards/auth.guard';
import { AuthInterceptor } from './services/auth.interceptor';

const routes: Routes = [
  { path: '',          redirectTo: 'login',     pathMatch: 'full' },
  { path: 'login',     component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [AuthGuard] },
  { path: '**',        redirectTo: 'login' },
];

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    DashboardComponent,
    MetricsComponent,
    CameraComponent,
    SirenComponent,
    HourlyChartComponent,
    HeatmapComponent,
    StatsTableComponent,
    DetectionLogComponent,
    ChangePasswordComponent,
  ],
  imports: [
    BrowserModule,
    HttpClientModule,
    FormsModule,
    RouterModule.forRoot(routes),
  ],
  providers: [
    AuthGuard,
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true,
    },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}