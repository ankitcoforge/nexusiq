import { Component, OnInit, OnDestroy } from '@angular/core';
import { ApiService } from './services/api.service';

interface MessageItem {
  role: 'user' | 'assistant';
  content: string;
  type?: string;
  data?: any;
}

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
  title = 'nexus-ui';
  sessionId: string | null = null;
  messages: MessageItem[] = [];
  healthStatus: string | null = null;
  fileReady: boolean = false;
  private healthPollId: any = null;

  constructor(private api: ApiService) {}

  async ngOnInit(): Promise<void> {
    try {
      const d = await this.api.initSession();
      this.sessionId = d?.['session_id'] || d?.['sessionId'] || null;
      console.log('session', this.sessionId);
      // hydrate chat history if provided
      const history = d?.['chat_history'] || d?.['chatHistory'] || [];
      for (const m of history)
        this.messages.push({
          role: m.role,
          content: m.content,
          type: m['message_type'],
          data: m.data,
        });
    } catch (e) {
      console.warn('session create failed', e);
    }

    // start health polling
    this.pollHealth();
  }

  private pollHealth() {
    this.healthPollId = setInterval(async () => {
      try {
        const h = await this.api.health();
        this.healthStatus = h?.status || 'unknown';
      } catch (e) {
        this.healthStatus = 'down';
      }
    }, 5000);
  }

  ngOnDestroy(): void {
    if (this.healthPollId) clearInterval(this.healthPollId);
  }

  onFile(file: File) {
    if (!this.sessionId) return console.warn('no session');
    this.messages.push({ role: 'user', content: `📎 Uploaded: ${file.name}` });
    this.api
      .uploadFileAsync(this.sessionId, file)
      .then((d) => {
        this.messages.push({
          role: 'assistant',
          content: d?.['message'] || 'File uploaded',
        });
        // enable analyze button when upload reported success
        if (
          d?.['status'] === 'uploaded' ||
          !(d && typeof d['status'] !== 'undefined')
        ) {
          this.fileReady = true;
        }
      })
      .catch((e) => {
        this.messages.push({
          role: 'assistant',
          content: `❌ Upload failed: ${e.message}`,
        });
      });
  }

  onAnalyze() {
    if (!this.sessionId) return;
    this.messages.push({
      role: 'assistant',
      content: '🔍 Extracting invoice data...',
    });
    this.api
      .extractAsync(this.sessionId)
      .then((d) => {
        const invoice = d?.['invoice_data'] || d;
        this.messages.push({
          role: 'assistant',
          content: '📋 Extraction complete!',
          type: 'extraction',
          data: invoice,
        });
        // start verify stream
        this.messages.push({
          role: 'assistant',
          content: '🤖 Running verification pipeline...',
        });
        this.api.verifyStream(
          this.sessionId!,
          (update: any) => {
            if (update.type === 'step_start') {
              this.messages.push({
                role: 'assistant',
                content: `Step ${update.step}/5: ${update.name}...`,
              });
            } else if (update.type === 'step_complete') {
              this.messages.push({
                role: 'assistant',
                content: update.result?.summary || 'Step complete',
                type: 'step',
                data: update.result,
              });
            } else if (update.type === 'report') {
              this.messages.push({
                role: 'assistant',
                content: 'Verification complete',
                type: 'verdict',
                data: update.report,
              });
              // optionally enable export by setting state or leaving report URL available
            }
          },
          () => {
            console.log('verify complete');
          },
          (err) => {
            this.messages.push({
              role: 'assistant',
              content: `❌ Verification failed: ${err.message}`,
            });
          },
        );
      })
      .catch((e) => {
        this.messages.push({
          role: 'assistant',
          content: `❌ Extraction failed: ${e.message}`,
        });
      });
  }

  onSend(msg: string) {
    if (!this.sessionId) return;
    this.messages.push({ role: 'user', content: msg });
    this.api
      .sendMessageAsync(this.sessionId, msg)
      .then((d) => {
        const reply = d?.['response'] || d?.['message'] || 'No reply';
        this.messages.push({ role: 'assistant', content: reply });
      })
      .catch((e) => {
        this.messages.push({
          role: 'assistant',
          content: 'Sorry, I could not process your message.',
        });
      });
  }
}
