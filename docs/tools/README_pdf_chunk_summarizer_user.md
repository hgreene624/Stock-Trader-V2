# PDF Chunk Summarizer — User Guide

## Purpose
Use this helper when a research PDF is too large to summarize in a single pass. It converts the PDF to text, slices it into page chunks, and produces two Markdown files:
1. `*-chunk-summaries.md` – sequential coverage of each chunk with key takeaways and project notes.
2. `*-overall-summary.md` – global recap plus Stock-Trader-V2–specific action items.

## Prerequisites
- Poppler’s `pdftotext` binary available in `PATH` (`brew install poppler` on macOS).
- Python 3.10+.

## Workflow
1. **Create a folder for the source.**  
   ```
   mkdir -p "docs/Research Resources/<Book Title>/notes"
   mv /path/to/book.pdf "docs/Research Resources/<Book Title>/"
   ```
2. **Run the script.**  
   ```
   python3 scripts/pdf_chunk_summarizer.py \
     "docs/Research Resources/<Book Title>/<Book>.pdf" \
     --output-dir "docs/Research Resources/<Book Title>/notes" \
     --chunk-pages 15 \
     --chunk-sentences 5 \
     --overall-sentences 12
   ```
3. **Review the output.**  
   - `... - chunk-summaries.md` lists each chunk with concise bullet points.
   - `... - overall-summary.md` consolidates the book and flags project takeaways.
4. **Edit for clarity.**  
   The script jump-starts the notes, but you should reread the Markdown to replace any remaining verbatim quotes with your own summaries and add page citations.

## Tips
- Adjust `--chunk-pages` if the PDF has very short chapters or extremely long sections.
- Re-run the script after edits only if you need a fresh baseline; otherwise keep manual tweaks by versioning the Markdown files in Git.
- Use Obsidian links to connect these summaries to daily journals or constitution notes.
