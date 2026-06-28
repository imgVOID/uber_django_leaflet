
import { LiveUpdateMessage, } from '../types/live';
import { CONFIG } from './live_constants';
// ==================== LiveSocket ====================
export class LiveSocket {
  private socket: WebSocket;

  constructor(private onUpdate: (data: LiveUpdateMessage) => void) {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    this.socket = new WebSocket(`${protocol}://${window.location.host}${CONFIG.wsPath}`);
    this.socket.onmessage = (event) => this.handleMessage(event);
  }

  private handleMessage(event: MessageEvent): void {
    const data = JSON.parse(event.data);
    if (data.type === 'driver.location.update') {
      this.onUpdate(data as LiveUpdateMessage);
    }
  }
}
