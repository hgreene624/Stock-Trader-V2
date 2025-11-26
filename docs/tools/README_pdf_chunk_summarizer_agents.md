# PDF Chunk Summarizer — Agent Playbook

## When to Use
- A user hands you a large PDF and asks for structured notes, summaries, or actionable insights.
- You need to split the workload into deterministic chunks so future agents can pick up where you left off.
- You must deposit the results inside `docs/Research Resources/` with both raw PDFs and Markdown notes.

## Steps for Agents
1. **Verify dependencies.**
   - Ensure `pdftotext` exists (`which pdftotext`). If missing, ask the user for installation guidance.
2. **Organize the workspace.**
   - Create `docs/Research Resources/<Title>/` and move/copy the PDF there.
   - Create a `notes/` subfolder for generated Markdown.
3. **Run the script.**
   ```
   python3 scripts/pdf_chunk_summarizer.py \
     "docs/Research Resources/<Title>/<Book>.pdf" \
     --output-dir "docs/Research Resources/<Title>/notes" \
     --chunk-pages 15 \
     --chunk-sentences 5 \
     --overall-sentences 12
   ```
   - Adjust `--chunk-pages` for very short or long chapters (10–20 is typical).
4. **Inspect outputs.**
   - Confirm `*-chunk-summaries.md` and `*-overall-summary.md` were created.
   - Skim the first/last chunk to ensure the content is narrative, not raw index text; if not, tweak chunk sizes or manually edit.
5. **Refine summaries.**
   - Replace any lingering quoted passages with paraphrased bullets and cite page ranges (e.g., “(pp.54-56)”).
   - Add project-specific insights (risks, tooling needs) under “Project-Relevant Highlights” or the final takeaway list.
6. **Report back.**
   - Mention both Markdown paths plus notable insights in your final response.
   - Suggest next steps (e.g., “Review chunk 6 notes before coding the regime detector”).

## Reminders
- Never overwrite the PDF; keep it alongside the notes.
- Do not rely solely on the auto-generated text—always interpret the content.
- Link these notes from Obsidian or other knowledge bases so the user can locate them later.
