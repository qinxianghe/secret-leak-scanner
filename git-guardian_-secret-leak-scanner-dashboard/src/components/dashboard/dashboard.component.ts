
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../services/api.service';
import { Finding, Stats } from '../../types';

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

  trendData = [
    { day: '周一', count: 5 },
    { day: '周二', count: 8 },
    { day: '周三', count: 3 },
    { day: '周四', count: 12 },
    { day: '周五', count: 7 },
    { day: '周六', count: 9 },
    { day: '周日', count: 4 },
  ];
  maxTrendCount = Math.max(...this.trendData.map(d => d.count));

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
