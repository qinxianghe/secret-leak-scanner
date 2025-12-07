
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { ApiService } from '../../services/api.service';
import { Finding } from '../../types';
import { catchError, of, switchMap } from 'rxjs';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';

interface FindingsState {
  findings: Finding[];
  error: string | null;
  loading: boolean;
}

@Component({
  selector: 'app-findings',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './findings.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FindingsComponent {
  private apiService = inject(ApiService);
  
  // State
  pageSize = 10;
  currentPage = signal(0);
  expandedFindingId = signal<number | null>(null);

  // Data fetching triggered by currentPage changes
  private findings$ = toObservable(this.currentPage).pipe(
    switchMap(page => {
      const offset = page * this.pageSize;
      return this.apiService.getFindings(this.pageSize, offset).pipe(
        catchError(err => {
          console.error(err);
          return of({ error: 'Could not load findings.' });
        })
      );
    })
  );

  findings = toSignal(this.findings$, { initialValue: [] as Finding[]});
  
  // Methods
  nextPage(): void {
    this.currentPage.update(page => page + 1);
  }

  prevPage(): void {
    this.currentPage.update(page => Math.max(0, page - 1));
  }

  toggleExpand(findingId: number): void {
    this.expandedFindingId.update(current => (current === findingId ? null : findingId));
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

  getStatusClass(status: Finding['status']): string {
    switch (status) {
      case 'New': return 'bg-blue-500';
      case 'Resolved': return 'bg-green-500';
      case 'Ignored': return 'bg-gray-500';
      default: return 'bg-gray-600';
    }
  }
}
