"""Module for summarizing extracted text."""

import logging
import re
from collections import Counter

import spacy

from papermint.config import DEFAULT_SUMMARY_SENTENCES, SPACY_MODEL

logger = logging.getLogger(__name__)

# Load spaCy model at module level (lazy singleton)
_nlp = None
def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(SPACY_MODEL)
        except OSError:
            from spacy.cli import download
            download(SPACY_MODEL)
            _nlp = spacy.load(SPACY_MODEL)
            
        # We intentionally skip pytextrank here to avoid spaCy extension conflicts (E1037)
        # and instead rely on the built-in fallback sentence scorer which works perfectly.
            
    return _nlp


def _is_reference_line(text: str) -> bool:
    """Check if a line looks like a bibliographic reference rather than prose."""
    text = text.strip()
    if not text:
        return True
    # Numbered reference
    if re.match(r'^\s*\[?\d+\]?\.?\s', text):
        return True
    # DOI
    if re.search(r'10\.\d{4,9}/[^\s]+', text):
        return True
    # Multiple "Author, F." patterns on a single line
    if len(re.findall(r'[A-Z][a-z]+,\s+[A-Z]\.', text)) >= 2:
        return True
    return False


def _clean_for_summary(text: str) -> str:
    """Remove reference lines and noise from text before summarization."""
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        if not _is_reference_line(line):
            stripped = line.strip()
            # Skip very short lines (headers, page numbers)
            if len(stripped) > 20:
                clean_lines.append(stripped)
    return ' '.join(clean_lines)


def _basic_summarize(doc: spacy.tokens.Doc, num_sentences: int) -> str:
    """Improved extractive summarization using spaCy.
    
    Uses word frequency scoring with position awareness:
    - Sentences near the beginning and end get a boost.
    - Very short sentences are penalized.
    - Only content words (no stops, no punctuation) contribute to score.
    """
    sentences = list(doc.sents)
    if len(sentences) <= num_sentences:
        return " ".join([s.text.strip() for s in sentences])
        
    # Calculate word frequencies (content words only)
    words = [token.text.lower() for token in doc 
             if not token.is_stop and not token.is_punct and len(token.text) > 2]
    word_freq = Counter(words)
    
    # Normalize frequencies
    max_freq = max(word_freq.values()) if word_freq else 1
    for word in word_freq:
        word_freq[word] = word_freq[word] / max_freq
        
    # Score sentences
    sent_scores = {}
    total_sents = len(sentences)
    
    for i, sent in enumerate(sentences):
        # Content word score
        content_words = [t for t in sent if not t.is_stop and not t.is_punct and len(t.text) > 2]
        if not content_words:
            sent_scores[i] = 0.0
            continue
            
        score = sum(word_freq.get(t.text.lower(), 0) for t in content_words)
        
        # Normalize by content word count (not total token count)
        score = score / (len(content_words) + 1)
        
        # Position boost: sentences in first 20% or last 20% get a 30% boost
        position_ratio = i / total_sents
        if position_ratio < 0.2 or position_ratio > 0.8:
            score *= 1.3
            
        # Penalize very short sentences (< 5 words) — they're usually headers
        if len(list(sent)) < 5:
            score *= 0.3
            
        # Penalize sentences that look like reference fragments
        if _is_reference_line(sent.text):
            score *= 0.1
            
        sent_scores[i] = score
        
    # Get top N sentences by score, but keep original order
    top_sent_indices = sorted(sorted(sent_scores, key=sent_scores.get, reverse=True)[:num_sentences])
    
    return " ".join([sentences[i].text.strip() for i in top_sent_indices])


def summarize(text: str, num_sentences: int = DEFAULT_SUMMARY_SENTENCES) -> str:
    """Generate an extractive summary of the text.
    
    Pre-cleans the text to remove reference lines and noise, then uses
    position-aware TF-IDF scoring to select the most representative sentences.
    
    Args:
        text: The text to summarize.
        num_sentences: The number of sentences to include in the summary.
        
    Returns:
        The summarized text.
    """
    if not text or not text.strip():
        return ""
    
    # Pre-clean the text to remove reference lines
    clean_text = _clean_for_summary(text)
    if not clean_text.strip():
        # If cleaning removed everything, fall back to original
        clean_text = text
        
    nlp = _get_nlp()
    
    # Truncate text if it's too long to avoid memory issues (e.g., > 100k chars)
    if len(clean_text) > 100000:
        logger.warning("Text too long for summarization, truncating.")
        clean_text = clean_text[:100000]
        
    try:
        doc = nlp(clean_text)
    except Exception as e:
        logger.warning(f"spaCy summarization failed: {e}")
        # Simplest possible fallback if spaCy itself fails completely
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
        return ". ".join(sentences[:num_sentences]) + "." if sentences else ""
        
    # Check if text is shorter than requested summary
    sentences = list(doc.sents)
    if len(sentences) <= num_sentences:
        return clean_text.strip()
            
    return _basic_summarize(doc, num_sentences)
