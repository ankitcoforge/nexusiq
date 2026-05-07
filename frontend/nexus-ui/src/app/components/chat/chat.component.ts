import { Component, OnInit, Input } from '@angular/core';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-chat',
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss'],
})
export class ChatComponent implements OnInit {
  @Input() messages: Array<{
    role: string;
    content: string;
    type?: string;
    data?: any;
  }> = [];
  getVerdictClass(verdict: string): string {
    const map: Record<string, string> = {
      'Approve for Processing': 'approve',
      'Approve with Notation': 'warning',
      'Escalate to SIU': 'reject',
    };
    return map[verdict] || 'default';
  }

  @Input() sessionId: string | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {}

  // local UI state for toggling thought processes per step
  toggledThoughts: Record<string, boolean> = {};

  toggleThought(id: string) {
    this.toggledThoughts[id] = !this.toggledThoughts[id];
  }

  stepStatusClass(status: string) {
    const map: Record<string, string> = {
      passed: 'bg-success text-white',
      failed: 'bg-danger text-white',
      warning: 'bg-warning text-dark',
      unavailable: 'bg-secondary text-white',
      manual_review: 'bg-primary text-white',
    };
    return map[status] || 'bg-secondary text-white';
  }

  formatCurrency(v: any) {
    if (v == null || isNaN(Number(v))) return '—';
    return '$' + Number(v).toFixed(2);
  }

  downloadReport() {
    if (!this.sessionId) return;
    const url = this.api.reportPdfUrl(this.sessionId);
    window.open(url, '_blank');
  }
}
