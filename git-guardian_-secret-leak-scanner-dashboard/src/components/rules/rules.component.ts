import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
// Fix: Corrected the import path for ApiService. The file `data.service.ts` is empty and not a module.
import { ApiService } from '../../services/api.service';
import { Rule } from '../../types';
import { catchError, of } from 'rxjs';

@Component({
  selector: 'app-rules',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './rules.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RulesComponent {
  private apiService = inject(ApiService);
  rules = toSignal(this.apiService.getRules().pipe(catchError(() => of([] as Rule[]))));
  
  reloadStatus = signal('');

  toggleRule(rule: Rule): void {
    // This is optimistic UI update. A more robust solution would handle API errors.
    // The API for this is assumed and not in the provided spec.
    // this.apiService.updateRule(rule.id, !rule.enabled).subscribe();
    console.log(`Toggling rule ${rule.id} to ${!rule.enabled}. API call is mocked.`);
  }
  
  reloadRules(): void {
    this.reloadStatus.set('正在重新加载规则...');
    this.apiService.reloadRules().subscribe({
      next: (res) => this.reloadStatus.set(`${res.message} (${res.count} 条规则已加载).`),
      error: () => this.reloadStatus.set('重新加载失败'),
    });
  }

  getSeverityClass(severity: Rule['severity']): string {
    switch (severity) {
      case 'Critical': return 'text-red-400 bg-red-900/50';
      case 'High': return 'text-orange-400 bg-orange-900/50';
      case 'Medium': return 'text-yellow-400 bg-yellow-900/50';
      case 'Low': return 'text-blue-400 bg-blue-900/50';
      default: return 'text-gray-400 bg-gray-700';
    }
  }
}
