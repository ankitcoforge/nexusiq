import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { firstValueFrom } from 'rxjs';

interface ApiResponse {
  [key: string]: any;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private base = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  createSession(): Observable<ApiResponse> {
    return this.http.post<ApiResponse>(`${this.base}/session`, {});
  }

  uploadFile(sessionId: string, file: File): Observable<ApiResponse> {
    const fd = new FormData();
    fd.append('file', file);
    return this.http.post<ApiResponse>(`${this.base}/upload/${sessionId}`, fd);
  }

  extract(sessionId: string): Observable<ApiResponse> {
    return this.http.post<ApiResponse>(`${this.base}/extract/${sessionId}`, {});
  }

  verify(sessionId: string): Observable<any> {
    // returns a stream/observable; calling code should handle the response body reader
    return this.http.post<any>(
      `${this.base}/verify/${sessionId}`,
      {},
      { responseType: 'text' as 'json' },
    );
  }

  sendMessage(sessionId: string, message: string): Observable<ApiResponse> {
    return this.http.post<ApiResponse>(
      `${this.base}/chat/${sessionId}/message`,
      { message },
    );
  }

  reportPdfUrl(sessionId: string): string {
    return `${this.base}/report/${sessionId}/pdf`;
  }

  // ---------- Promise / Fetch helpers for streaming and easier integration

  async initSession(): Promise<ApiResponse> {
    const res = await fetch(`${this.base}/session`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to create session');
    return await res.json();
  }

  async uploadFileAsync(sessionId: string, file: File): Promise<ApiResponse> {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${this.base}/upload/${sessionId}`, {
      method: 'POST',
      body: fd,
    });
    if (!res.ok) throw new Error('Upload failed');
    return await res.json();
  }

  async extractAsync(sessionId: string): Promise<ApiResponse> {
    const res = await fetch(`${this.base}/extract/${sessionId}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Extract failed');
    return await res.json();
  }

  async sendMessageAsync(
    sessionId: string,
    message: string,
  ): Promise<ApiResponse> {
    const res = await fetch(`${this.base}/chat/${sessionId}/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error('Send message failed');
    return await res.json();
  }

  /**
   * Verify with streaming support. Calls `onUpdate` for each parsed JSON line received.
   */
  async verifyStream(
    sessionId: string,
    onUpdate: (u: any) => void,
    onComplete?: () => void,
    onError?: (e: any) => void,
  ): Promise<void> {
    try {
      const res = await fetch(`${this.base}/verify/${sessionId}`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Verify request failed');
      if (!res.body) {
        onComplete?.();
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const parsed = JSON.parse(line);
            onUpdate(parsed);
          } catch (e) {
            // ignore parse errors but surface if requested
            console.warn('Could not parse stream line', e, line);
          }
        }
      }
      if (buffer.trim()) {
        try {
          onUpdate(JSON.parse(buffer));
        } catch (_) {
          /* ignore */
        }
      }
      onComplete?.();
    } catch (e) {
      onError?.(e);
      throw e;
    }
  }

  async health(): Promise<any> {
    const res = await fetch(`${this.base}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return await res.json();
  }
}
