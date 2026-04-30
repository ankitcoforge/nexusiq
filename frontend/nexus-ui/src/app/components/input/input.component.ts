import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';

@Component({
  selector: 'app-input',
  templateUrl: './input.component.html',
  styleUrls: ['./input.component.scss'],
})
export class InputComponent implements OnInit {
  @Output() fileSelected = new EventEmitter<File>();
  @Output() analyze = new EventEmitter<void>();
  @Output() send = new EventEmitter<string>();
  @Input() showAnalyze: boolean = false;

  message = '';
  toolsOpen = false;

  constructor() {}

  ngOnInit(): void {}

  onFileChange(event: Event) {
    const el = event.target as HTMLInputElement;
    const f = el.files && el.files[0];
    if (f) this.fileSelected.emit(f);
    el.value = '';
  }

  toggleTools() {
    this.toolsOpen = !this.toolsOpen;
  }

  triggerAnalyze() {
    this.analyze.emit();
  }

  triggerSend() {
    if (this.message && this.message.trim()) {
      this.send.emit(this.message.trim());
      this.message = '';
    }
  }
}
