# notebooklm-py Practical Notes

- First-time setup may require:
  - `pip install "notebooklm-py[browser]"`
  - `playwright install chromium`
  - `pip install socksio` (if proxy/socks error appears)
- Some sites cannot be ingested directly by NotebookLM; use alternates.
- Typical artifact flow:
  1) generate -> task_id
  2) artifact poll/wait until completed
  3) download by artifact id
- Deck stability guidance:
  - Prefer 8-10 pages per generation batch.
  - If >10 pages total, split into multiple batches and merge.
  - Enforce one shared style contract across batches, then do one final harmonization pass.
