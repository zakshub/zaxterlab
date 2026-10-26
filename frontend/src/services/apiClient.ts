/**
 * API Client Manager with dynamic Mode Switching (Demo vs Live)
 */

import { ApiClient } from '../types/api';
import { LiveApiAdapter } from './liveAdapter';
import { MockApiAdapter } from './mockAdapter';

export type ClientMode = 'demo' | 'live';

class ApiClientManager {
  private mode: ClientMode = 'demo';
  private mockAdapter: MockApiAdapter;
  private liveAdapter: LiveApiAdapter;

  constructor() {
    this.mockAdapter = new MockApiAdapter();
    this.liveAdapter = new LiveApiAdapter('/api');
  }

  public getMode(): ClientMode {
    return this.mode;
  }

  public setMode(newMode: ClientMode): void {
    this.mode = newMode;
  }

  public getClient(): ApiClient {
    return this.mode === 'live' ? this.liveAdapter : this.mockAdapter;
  }
}

export const clientManager = new ApiClientManager();
