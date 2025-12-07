
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ScanResult, ScanFinding } from '../../types';

@Component({
  selector: 'app-scan',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './scan.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScanComponent {
  private apiService = inject(ApiService);

  contentToScan = signal('');
  scanResult = signal<ScanResult | null>(null);
  isLoading = signal(false);
  error = signal<string | null>(null);

  performScan(): void {
    if (!this.contentToScan().trim()) {
      return;
    }
    this.isLoading.set(true);
    this.error.set(null);
    this.scanResult.set(null);

    this.apiService.scanContent(this.contentToScan()).subscribe({
      next: (result) => {
        this.scanResult.set(result);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error(err);
        this.error.set('扫描过程中发生错误');
        this.isLoading.set(false);
      },
    });
  }

  getSeverityClass(severity: ScanFinding['severity']): string {
    switch (severity) {
      case 'Critical': return 'border-red-500 bg-red-900/30 text-red-300';
      case 'High': return 'border-orange-500 bg-orange-900/30 text-orange-300';
      case 'Medium': return 'border-yellow-500 bg-yellow-900/30 text-yellow-300';
      case 'Low': return 'border-blue-500 bg-blue-900/30 text-blue-300';
      default: return 'border-gray-600 bg-gray-700/30 text-gray-300';
    }
  }
}
