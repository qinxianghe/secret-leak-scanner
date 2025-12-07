
import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

import { DashboardComponent } from './components/dashboard/dashboard.component';
import { FindingsComponent } from './components/findings/findings.component';
import { RulesComponent } from './components/rules/rules.component';
import { SettingsComponent } from './components/settings/settings.component';
import { ScanComponent } from './components/scan/scan.component';

type Page = 'dashboard' | 'findings' | 'rules' | 'settings' | 'scan';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, DashboardComponent, FindingsComponent, RulesComponent, SettingsComponent, ScanComponent],
  templateUrl: './app.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent {
  currentPage = signal<Page>('dashboard');

  changePage(page: Page): void {
    this.currentPage.set(page);
  }
}
