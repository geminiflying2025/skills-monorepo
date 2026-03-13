import { describe, expect, it, vi, afterEach } from 'vitest';
import { parseReportText } from './api';

describe('parseReportText', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('posts text to the backend and returns parsed report data', async () => {
    const payload = { sections: [] };
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => payload,
      }),
    );

    await expect(parseReportText('demo')).resolves.toEqual(payload);
  });

  it('throws a readable error when the backend returns an error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'bad request' }),
      }),
    );

    await expect(parseReportText('demo')).rejects.toThrow('bad request');
  });
});
