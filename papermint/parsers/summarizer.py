"""Module for summarizing extracted text."""

import logging
from collections import Counter
import spacy
from papermint.config import SPACY_MODEL, DEFAULT_SUMMARY_SENTENCES

logger = logging.getLogger(__name__)

# Load spaCy model at module level (lazy singleton)
_nlp = None
def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load(SPACY_MODEL)
        except OSError:
            import spacy.cli
            spacy.cli.download(SPACY_MODEL)
            _nlp = spacy.load(SPACY_MODEL)
            
        # Try to add pytextrank
        try:
            import pytextrank
            _nlp.add_pipe("textrank")
        except ImportError:
            logger.info("pytextrank not installed, falling back to basic summarization.")
            
    return _nlp

def _basic_summarize(doc: spacy.tokens.Doc, num_sentences: int) -> str:
    """Basic TF-IDF-like summarization using spaCy."""
    sentences = list(doc.sents)
    if len(sentences) <= num_sentences:
        return " ".join([s.text.strip() for s in sentences])
        
    # Calculate word frequencies
    words = [token.text.lower() for token in doc if not token.is_stop and not token.is_punct]
    word_freq = Counter(words)
    
    # Normalize frequencies
    max_freq = max(word_freq.values()) if word_freq else 1
    for word in word_freq:
        word_freq[word] = word_freq[word] / max_freq
        
    # Score sentences
    sent_scores = {}
    for i, sent in enumerate(sentences):
        score = 0
        for token in sent:
            word = token.text.lower()
            if word in word_freq:
                score += word_freq[word]
        # Normalize by length to avoid bias towards very long sentences
        sent_scores[i] = score / (len(sent) + 1)
        
    # Get top N sentences by score, but keep original order
    top_sent_indices = sorted(sorted(sent_scores, key=sent_scores.get, reverse=True)[:num_sentences])
    
    return " ".join([sentences[i].text.strip() for i in top_sent_indices])

def summarize(text: str, num_sentences: int = DEFAULT_SUMMARY_SENTENCES) -> str:
    """Generate an extractive summary of the text.
    
    Uses pytextrank if available, otherwise falls back to a simple TF-IDF-like approach.
    
    Args:
        text: The text to summarize.
        num_sentences: The number of sentences to include in the summary.
        
    Returns:
        The summarized text.
    """
    if not text or not text.strip():
        return ""
        
    nlp = _get_nlp()
    
    # Process the text
    # Truncate text if it's too long to avoid memory issues (e.g., > 100k chars)
    if len(text) > 100000:
        logger.warning("Text too long for summarization, truncating.")
        text = text[:100000]
        
    doc = nlp(text)
    
    # Check if text is shorter than requested summary
    sentences = list(doc.sents)
    if len(sentences) <= num_sentences:
        return text.strip()
        
    # Check if textrank is available
    if doc.has_annotation("EXT"):
        # Not a perfect check, but if pytextrank is in pipeline, doc._.textrank will be available
        try:
            summary_sentences = []
            # pytextrank specific logic
            for sent in doc._.textrank.summary(limit_sentences=num_sentences):
                summary_sentences.append(sent.text.strip())
            return " ".join(summary_sentences)
        except AttributeError:
            pass
            
    # Fallback to basic summarization
    return _basic_summarize(doc, num_sentences)
