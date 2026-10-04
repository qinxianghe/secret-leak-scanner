
import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Finding, Rule, ScanResult, Stats } from '../types';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  // 调试/开发直连后端；如有需要可改为相对路径并配置代理
  private apiUrl = 'http://localhost:8000/api';

  getStats(): Observable<Stats> {
    return this.http.get<Stats>(`${this.apiUrl}/stats`);
  }

  getFindings(limit: number, offset: number): Observable<Finding[]> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    // NOTE: The backend API spec for findings is minimal.
    // We are assuming it returns a richer Finding object for a good UI experience.
    return this.http.get<Finding[]>(`${this.apiUrl}/findings`, { params });
  }

  getRules(): Observable<Rule[]> {
    return this.http.get<Rule[]>(`${this.apiUrl}/rules`);
  }

  reloadRules(): Observable<{ message: string; count: number }> {
    return this.http.post<{ message: string; count: number }>(`${this.apiUrl}/rules/reload`, {});
  }
  
  scanContent(content: string): Observable<ScanResult> {
    return this.http.post<ScanResult>(`${this.apiUrl}/scan`, { content });
  }
  
  // NOTE: The following API endpoints are assumed for a complete application workflow.
  // The provided spec did not include them.

  updateFindingStatus(findingId: number, status: 'Resolved' | 'Ignored'): Observable<void> {
    // Assumes an endpoint like PATCH /api/findings/{id}
    return this.http.patch<void>(`${this.apiUrl}/findings/${findingId}`, { status });
  }

  updateRule(ruleId: string, enabled: boolean): Observable<void> {
    // Assumes an endpoint like PATCH /api/rules/{id}
    return this.http.patch<void>(`${this.apiUrl}/rules/${ruleId}`, { enabled });
  }
}
