import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from collections import Counter
import re
from datetime import datetime
import logging

class AnalyticsEngine:
    """Analytics engine for analyzing parsed verdict content"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_text_statistics(self, content: str) -> Dict[str, Any]:
        """Analyze basic text statistics"""
        if not content:
            return {}
            
        # Basic text stats
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        
        return {
            'word_count': len(words),
            'sentence_count': len([s for s in sentences if s.strip()]),
            'paragraph_count': len(paragraphs),
            'avg_words_per_sentence': len(words) / max(len([s for s in sentences if s.strip()]), 1),
            'avg_words_per_paragraph': len(words) / max(len(paragraphs), 1),
            'unique_words': len(set(words)),
            'lexical_diversity': len(set(words)) / max(len(words), 1)
        }
        
    def analyze_legal_terms(self, content: str) -> Dict[str, Any]:
        """Analyze legal terms and phrases"""
        if not content:
            return {}
            
        # Hebrew legal terms (basic examples)
        legal_terms = {
            'בית דין': 'court',
            'פס"ד': 'verdict',
            'בקשה': 'request',
            'תביעה': 'lawsuit',
            'החלטה': 'decision',
            'ערעור': 'appeal',
            'צו': 'order',
            'סעד': 'remedy',
            'פיצוי': 'compensation',
            'ביטול': 'cancellation'
        }
        
        term_counts = {}
        for hebrew_term, english_term in legal_terms.items():
            count = content.count(hebrew_term)
            if count > 0:
                term_counts[english_term] = count
                
        return {
            'legal_terms_found': term_counts,
            'total_legal_terms': sum(term_counts.values()),
            'unique_legal_terms': len(term_counts)
        }
        
    def analyze_document_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure and formatting"""
        if not content:
            return {}
            
        lines = content.split('\n')
        
        # Count different types of lines
        empty_lines = len([line for line in lines if not line.strip()])
        numbered_lines = len([line for line in lines if re.match(r'^\d+\.', line.strip())])
        all_caps_lines = len([line for line in lines if line.strip().isupper() and len(line.strip()) > 3])
        
        return {
            'total_lines': len(lines),
            'empty_lines': empty_lines,
            'numbered_lines': numbered_lines,
            'all_caps_lines': all_caps_lines,
            'content_lines': len(lines) - empty_lines
        }
        
    def generate_comprehensive_analysis(self, content: str) -> Dict[str, Any]:
        """Generate comprehensive analysis of document content"""
        if not content:
            return {}
            
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'text_statistics': self.analyze_text_statistics(content),
            'legal_terms': self.analyze_legal_terms(content),
            'document_structure': self.analyze_document_structure(content)
        }
        
        # Add summary metrics
        text_stats = analysis['text_statistics']
        legal_stats = analysis['legal_terms']
        
        analysis['summary'] = {
            'document_length': text_stats.get('word_count', 0),
            'legal_complexity': legal_stats.get('total_legal_terms', 0),
            'structure_score': analysis['document_structure'].get('content_lines', 0)
        }
        
        return analysis
        
    def compare_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare multiple documents"""
        if not documents:
            return {}
            
        comparisons = {
            'document_count': len(documents),
            'avg_word_count': np.mean([d.get('word_count', 0) for d in documents]),
            'avg_legal_terms': np.mean([d.get('total_legal_terms', 0) for d in documents]),
            'file_types': Counter([d.get('file_type', 'unknown') for d in documents]),
            'parsing_success_rate': len([d for d in documents if d.get('parsed_successfully', False)]) / len(documents)
        }
        
        return comparisons
        
    def generate_report(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Generate a human-readable report from analysis results"""
        if not analysis_results:
            return "No analysis results available."
            
        report = []
        report.append("=== VERDICT ANALYSIS REPORT ===")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Documents analyzed: {len(analysis_results)}")
        report.append("")
        
        # Summary statistics
        successful_parses = [r for r in analysis_results if r.get('parsed_successfully', False)]
        if successful_parses:
            avg_words = np.mean([r.get('word_count', 0) for r in successful_parses])
            avg_legal_terms = np.mean([r.get('total_legal_terms', 0) for r in successful_parses])
            
            report.append("SUMMARY STATISTICS:")
            report.append(f"- Average word count: {avg_words:.1f}")
            report.append(f"- Average legal terms: {avg_legal_terms:.1f}")
            report.append(f"- Successfully parsed: {len(successful_parses)}/{len(analysis_results)}")
            report.append("")
            
        # File type distribution
        file_types = Counter([r.get('file_type', 'unknown') for r in analysis_results])
        if file_types:
            report.append("FILE TYPE DISTRIBUTION:")
            for file_type, count in file_types.most_common():
                report.append(f"- {file_type}: {count}")
            report.append("")
            
        return '\n'.join(report) 