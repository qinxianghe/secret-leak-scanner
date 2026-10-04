
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Whitelist } from '../../types';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './settings.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsComponent {
  // Using local mock data as API for whitelist is not specified.
  whitelist = signal<Whitelist[]>([
      { id: 'W001', type: 'Pattern', value: 'ghp_EXAMPLE_..._EXAMPLE1234', reason: 'Example token in documentation' },
      { id: 'W002', type: 'Path', value: 'tests/fixtures/', reason: 'Test data files' },
      { id: 'W003', type: 'Commit', value: 'c9d8e7f', reason: 'Initial import of legacy code' },
  ]);
}
