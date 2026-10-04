import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../services/api.service';
import { Finding } from '../../types';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardComponent {
  private apiService = inject(ApiService);

  stats = toSignal(this.apiService.getStats().pipe(catchError(() => of(null))));
  allFindings = toSignal(this.apiService.getFindings(200, 0).pipe(catchError(() => of([] as Finding[]))));
  recentFindings = toSignal(this.apiService.getFindings(5, 0).pipe(catchError(() => of([] as Finding[]))));

  derivedStats = computed(() => {
    const findings = this.recentFindings();
    if (!findings || findings.length === 0) {
      return { reposAffected: 0, criticalCount: 0 };
    }
    const repos = new Set(findings.map(f => f.repo));
    const criticals = findings.filter(f => f.rule.severity === 'Critical').length;
    return {
      reposAffected: repos.size,
      criticalCount: criticals,
    };
  });

  // 近7天按日期聚合
  private trendDataSignal = computed(() => {
    const findings = this.allFindings() ?? [];
    const today = new Date();
    const dayMap = new Map<string, number>();
    for (let i = 0; i < 7; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const label = `${d.getMonth() + 1}/${d.getDate()}`;
      dayMap.set(label, 0);
    }
    findings.forEach(f => {
      const dt = new Date(f.created_at);
      if (isNaN(dt.getTime())) return;
      const label = `${dt.getMonth() + 1}/${dt.getDate()}`;
      if (dayMap.has(label)) {
        dayMap.set(label, (dayMap.get(label) || 0) + 1);
      }
    });
    return Array.from(dayMap.entries())
      .reverse()
      .map(([label, count]) => ({ label, count }));
  });

  private maxTrendCountSignal = computed(() => {
    const data = this.trendDataSignal();
    const max = Math.max(...data.map(d => d.count), 0);
    return max === 0 ? 1 : max;
  });

  get trendDataList() {
    return this.trendDataSignal();
  }

  get maxTrendCount() {
    return this.maxTrendCountSignal();
  }

  get hasTrendData() {
    return (this.trendDataSignal()?.some(d => d.count > 0)) ?? false;
  }

  private maxBarHeightPx = 150;
  getBarHeightPx(count: number): number {
    if (!count) return 10; // 占位高度
    const h = (count / this.maxTrendCount) * this.maxBarHeightPx;
    return Math.max(Math.min(h, this.maxBarHeightPx), 16);
  }

  getSeverityClass(severity: Finding['rule']['severity']): string {
    switch (severity) {
      case 'Critical': return 'text-red-400 bg-red-900/50';
      case 'High': return 'text-orange-400 bg-orange-900/50';
      case 'Medium': return 'text-yellow-400 bg-yellow-900/50';
      case 'Low': return 'text-blue-400 bg-blue-900/50';
      default: return 'text-gray-400 bg-gray-700';
    }
  }
}
