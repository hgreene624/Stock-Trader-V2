#!/usr/bin/env python3
"""
Utility to split a PDF into page chunks and build Markdown summaries.

The script relies on `pdftotext` (Poppler) to extract page text,
then applies lightweight heuristics to summarize each chunk and to
surface sentences that look relevant for trading research.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import re
import subprocess
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

STOPWORDS = {
    "the", "and", "to", "of", "in", "that", "is", "it", "for", "on",
    "as", "with", "are", "this", "be", "by", "or", "an", "from", "at",
    "we", "can", "not", "will", "a", "our", "their", "has", "have",
    "but", "they", "its", "if", "into", "more", "than",
}

BAN_SUBSTRINGS = [
    "p1:", "printer:", "jwbk", "figure", "table", "chapter",
    "contents", "index", "copyright",
]

PROJECT_KEYWORDS = [
    "strategy", "strategies", "system", "systems", "algorithm",
    "risk", "capital", "execution", "portfolio", "data",
    "research", "automation", "testing", "backtest", "position",
    "liquidity", "edge", "market", "trading", "model",
]


def run_pdftotext(pdf_path: Path) -> List[str]:
    """Return a list of page strings extracted via pdftotext."""
    result = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        capture_output=True,
        check=True,
    )
    text = result.stdout.decode("utf-8", errors="ignore")
    pages = [page.strip() for page in text.split("\f") if page.strip()]
    if not pages:
        raise RuntimeError(f"No pages extracted from {pdf_path}")
    return pages


def chunk_pages(pages: Sequence[str], chunk_size: int) -> Iterable[Tuple[int, int, int, str]]:
    """Yield (chunk_index, start_page, end_page, chunk_text)."""
    total_pages = len(pages)
    for idx in range(0, total_pages, chunk_size):
        chunk_index = idx // chunk_size + 1
        start_page = idx + 1
        end_page = min(idx + chunk_size, total_pages)
        chunk_text = "\n".join(pages[idx:end_page])
        yield chunk_index, start_page, end_page, chunk_text


def _bad_sentence(clean: str) -> bool:
    lower = clean.lower()
    if len(clean.split()) < 6:
        return True
    if any(token in lower for token in BAN_SUBSTRINGS):
        return True
    letters = sum(ch.isalpha() for ch in clean)
    uppers = sum(ch.isupper() for ch in clean if ch.isalpha())
    digits = sum(ch.isdigit() for ch in clean)
    if letters and uppers / letters > 0.85:
        return True
    if len(clean) > 0 and digits / len(clean) > 0.25:
        return True
    return False


def split_sentences(text: str) -> List[str]:
    """Naive sentence splitting with additional filtering."""
    sent_candidates = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = []
    for sent in sent_candidates:
        clean = sent.strip()
        if len(clean) < 25:
            continue
        clean = clean.replace("\n", " ")
        if _bad_sentence(clean):
            continue
        sentences.append(clean)
    return sentences


def _score_sentences(sentences: Sequence[str]) -> List[Tuple[float, str]]:
    """Return (score, sentence) tuples based on word frequency."""
    if not sentences:
        return []
    word_freq: collections.Counter[str] = collections.Counter()
    for sent in sentences:
        for word in re.findall(r"[A-Za-z]{3,}", sent.lower()):
            if word in STOPWORDS:
                continue
            word_freq[word] += 1

    scores: List[Tuple[float, str]] = []
    for sent in sentences:
        score = sum(word_freq.get(word, 0) for word in re.findall(r"[A-Za-z]{3,}", sent.lower()))
        scores.append((score, sent))
    return scores


def summarize_sentences(sentences: Sequence[str], max_sentences: int = 5) -> List[str]:
    """Score sentences via word frequency to build a simple summary."""
    if not sentences:
        return []

    scores = _score_sentences(sentences)
    if not scores:
        return list(sentences[:max_sentences])

    top = sorted(scores, key=lambda x: x[0], reverse=True)
    selected = [sent for _, sent in top[:max_sentences]]
    return selected


def extract_highlights(sentences: Sequence[str], limit: int = 3) -> List[str]:
    """Select sentences containing trading/project keywords."""
    highlights: List[str] = []
    seen = set()
    scores = _score_sentences(sentences)
    for score, sent in sorted(scores, key=lambda x: x[0], reverse=True):
        lower = sent.lower()
        if any(keyword in lower for keyword in PROJECT_KEYWORDS):
            normalized = re.sub(r"\s+", " ", sent.strip())
            if normalized not in seen:
                highlights.append(normalized)
                seen.add(normalized)
        if len(highlights) >= limit:
            break
    return highlights


def build_chunk_markdown(
    chunks: Iterable[Tuple[int, int, int, str]],
    chunk_summary_sentences: int,
) -> Tuple[str, List[str]]:
    """Return Markdown text for chunk summaries and a list of collected sentences."""
    lines: List[str] = []
    collected: List[str] = []
    generated_ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append("# Chunk Summaries")
    lines.append("")
    lines.append(f"_Generated on {generated_ts}_")
    lines.append("")
    for chunk_index, start_page, end_page, text in chunks:
        sentences = split_sentences(text)
        summary = summarize_sentences(sentences, max_sentences=chunk_summary_sentences)
        highlights = extract_highlights(sentences)
        collected.extend(summary)

        lines.append(f"## Chunk {chunk_index} (Pages {start_page}–{end_page})")
        lines.append("")
        if summary:
            lines.append("### Main Points")
            for sent in summary:
                lines.append(f"- {sent}")
            lines.append("")
        else:
            lines.append("_No content extracted for this chunk._")
            lines.append("")

        if highlights:
            lines.append("### Project-Relevant Highlights")
            for sent in highlights:
                lines.append(f"- {sent}")
            lines.append("")
    return "\n".join(lines).strip() + "\n", collected


def build_overall_markdown(
    title: str,
    summary_sentences: Sequence[str],
    full_text_sentences: Sequence[str],
    takeaways: int = 10,
) -> str:
    """Return Markdown text for the overall summary file."""
    lines = [f"# {title}", ""]
    if summary_sentences:
        lines.append("## Overall Summary")
        for sent in summary_sentences:
            lines.append(f"- {sent}")
        lines.append("")

    highlights = extract_highlights(full_text_sentences, limit=takeaways)
    if highlights:
        lines.append("## Key Project Takeaways")
        for sent in highlights:
            lines.append(f"- {sent}")
        lines.append("")

    generated_ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines.append(f"_Generated on {generated_ts}_")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a PDF in page chunks.")
    parser.add_argument("pdf", type=Path, help="Path to the PDF file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where Markdown outputs will be written.",
    )
    parser.add_argument(
        "--chunk-pages",
        type=int,
        default=10,
        help="Number of pages per chunk (default: 10).",
    )
    parser.add_argument(
        "--chunk-sentences",
        type=int,
        default=5,
        help="Maximum sentences per chunk summary (default: 5).",
    )
    parser.add_argument(
        "--overall-sentences",
        type=int,
        default=12,
        help="Sentences to keep in the overall summary (default: 12).",
    )
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = run_pdftotext(args.pdf)
    chunk_iter = list(chunk_pages(pages, args.chunk_pages))

    chunk_md, _ = build_chunk_markdown(
        chunk_iter,
        chunk_summary_sentences=args.chunk_sentences,
    )

    chunk_md_path = output_dir / f"{args.pdf.stem} - chunk-summaries.md"
    chunk_md_path.write_text(chunk_md, encoding="utf-8")

    all_sentences: List[str] = []
    for _, _, _, text in chunk_iter:
        all_sentences.extend(split_sentences(text))

    overall_summary_sentences = summarize_sentences(
        all_sentences,
        max_sentences=args.overall_sentences,
    )

    overall_md = build_overall_markdown(
        title=f"{args.pdf.stem} — Overall Summary",
        summary_sentences=overall_summary_sentences,
        full_text_sentences=all_sentences,
    )

    overall_md_path = output_dir / f"{args.pdf.stem} - overall-summary.md"
    overall_md_path.write_text(overall_md, encoding="utf-8")

    print(f"Chunk summaries written to: {chunk_md_path}")
    print(f"Overall summary written to: {overall_md_path}")


if __name__ == "__main__":
    main()
