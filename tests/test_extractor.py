#!/usr/bin/env python3
"""
Unit tests for the AIExtractor module.
Tests AI-powered data extraction functionality with mocked data.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from src.extractor import AIExtractor

class TestAIExtractor:
    """Test cases for AIExtractor class"""
    
    @pytest.fixture
    def extractor(self):
        """Create AIExtractor instance for testing"""
        return AIExtractor()
        
    @pytest.fixture
    def sample_content(self):
        """Sample document content for testing"""
        return """
        בית המשפט המחוזי בתל אביב
        כבוד השופט דוד כהן
        תיק 12345/23
        בין התובע: ישראל ישראלי
        לבין הנתבע: משה כהן
        תאריך: 15/12/2023
        """
    
    def test_extractor_initialization(self, extractor):
        """Test that extractor initializes correctly with config"""
        assert extractor is not None
        assert hasattr(extractor, 'court_patterns')
        assert hasattr(extractor, 'judge_patterns')
        assert hasattr(extractor, 'case_patterns')
        assert len(extractor.court_patterns) > 0
        assert len(extractor.judge_patterns) > 0
        assert len(extractor.case_patterns) > 0
    
    def test_extract_court_name(self, extractor, sample_content):
        """Test court name extraction"""
        court_name = extractor._extract_court_name(sample_content)
        assert court_name == "בית המשפט המחוזי בתל אביב"
    
    def test_extract_judge_name(self, extractor, sample_content):
        """Test judge name extraction"""
        judge_name = extractor._extract_judge_name(sample_content)
        assert judge_name == "כבוד השופט דוד כהן"
    
    def test_extract_verdict_id(self, extractor, sample_content):
        """Test verdict ID extraction"""
        verdict_id = extractor._extract_verdict_id(sample_content)
        assert verdict_id == "12345/23"
    
    def test_extract_verdict_date(self, extractor, sample_content):
        """Test verdict date extraction"""
        verdict_date = extractor._extract_verdict_date(sample_content)
        assert verdict_date == "15/12/2023"
    
    def test_extract_parties(self, extractor, sample_content):
        """Test parties extraction"""
        parties = extractor._extract_parties(sample_content)
        assert parties is not None
        assert "ישראל ישראלי" in parties
        assert "משה כהן" in parties
    
    def test_extract_verdict_type(self, extractor, sample_content):
        """Test verdict type extraction"""
        verdict_type = extractor._extract_verdict_type(sample_content)
        # Should return None for this sample as no verdict type is specified
        assert verdict_type is None
    
    def test_different_court_patterns(self, extractor):
        """Test extraction with different court patterns"""
        courts = [
            "בית המשפט העליון",
            "בית המשפט המחוזי",
            "בית המשפט השלום",
            "בית הדין הרבני הגדול",
            "בית הדין הרבני האזורי"
        ]
        
        for court in courts:
            content = f"{court}\nכבוד השופט דוד כהן"
            extracted = extractor._extract_court_name(content)
            assert extracted == court
    
    def test_different_judge_patterns(self, extractor):
        """Test extraction with different judge patterns"""
        judges = [
            "כבוד השופט דוד כהן",
            "כבוד השופטת שרה לוי",
            "כבוד הדיינים: הרב משה כהן",
            "הרב דוד לוי"
        ]
        
        for judge in judges:
            content = f"בית המשפט המחוזי\n{judge}"
            extracted = extractor._extract_judge_name(content)
            assert extracted == judge
    
    def test_empty_content(self, extractor):
        """Test extraction with empty content"""
        result = extractor.extract_verdict_data("test.docx", "")
        assert result['confidence_score'] == 0.0
        assert result['verdict_id'] is None
        assert result['court_name'] is None
    
    def test_none_content(self, extractor):
        """Test extraction with None content"""
        result = extractor.extract_verdict_data("test.docx", None)
        assert result['confidence_score'] == 0.0
        assert result['verdict_id'] is None
        assert result['court_name'] is None
    
    def test_whitespace_content(self, extractor):
        """Test extraction with whitespace-only content"""
        result = extractor.extract_verdict_data("test.docx", "   \n\t   ")
        assert result['confidence_score'] == 0.0
        assert result['verdict_id'] is None
        assert result['court_name'] is None
    
    def test_fallback_extraction(self, extractor):
        """Test fallback extraction when regex fails"""
        content = """
        בית המשפט המחוזי
        כבוד השופט דוד כהן
        תיק 12345/23
        """
        result = extractor.extract_verdict_data("test.docx", content)
        assert result['court_name'] is not None
        assert result['judge_name'] is not None
        assert result['verdict_id'] is not None
        assert result['confidence_score'] > 0.0
    
    def test_confidence_calculation(self, extractor):
        """Test confidence score calculation"""
        data = {
            'verdict_id': '12345/23',
            'court_name': 'בית המשפט המחוזי',
            'judge_name': 'כבוד השופט דוד כהן',
            'case_number': '12345/23',
            'verdict_date': '15/12/2023',
            'parties': 'ישראל ישראלי vs משה כהן',
            'verdict_type': 'פסק דין',
            'confidence_score': 0.0,
            'extraction_timestamp': '2023-12-15T10:00:00',
            'file_path': 'test.docx'
        }
        confidence = extractor._calculate_confidence(data)
        assert confidence > 0.0
        assert confidence <= 1.0
    
    def test_validation_and_cleaning(self, extractor):
        """Test data validation and cleaning"""
        data = {
            'verdict_id': '  12345/23  ',
            'court_name': '  בית המשפט המחוזי  ',
            'judge_name': '  כבוד השופט דוד כהן  ',
            'case_number': '  12345/23  ',
            'verdict_date': '  15/12/2023  ',
            'parties': '  ישראל ישראלי vs משה כהן  ',
            'verdict_type': '  פסק דין  ',
            'confidence_score': 0.8,
            'extraction_timestamp': '2023-12-15T10:00:00',
            'file_path': 'test.docx'
        }
        cleaned = extractor._validate_and_clean_result(data)
        assert cleaned['verdict_id'] == '12345/23'
        assert cleaned['court_name'] == 'בית המשפט המחוזי'
        assert cleaned['judge_name'] == 'כבוד השופט דוד כהן'
    
    def test_performance_with_large_content(self, extractor):
        """Test performance with large content"""
        large_content = "בית המשפט המחוזי\n" * 1000 + "כבוד השופט דוד כהן\n" * 1000
        result = extractor.extract_verdict_data("test.docx", large_content)
        assert result['court_name'] is not None
        assert result['judge_name'] is not None
        assert result['confidence_score'] > 0.0
    
    def test_error_handling(self, extractor):
        """Test error handling in extraction"""
        with patch.object(extractor, '_extract_court_name', side_effect=Exception("Test error")):
            result = extractor.extract_verdict_data("test.docx", "test content")
            assert result['confidence_score'] >= 0.0
            assert 'error' in result or result['court_name'] is None
    
    def test_create_empty_result(self, extractor):
        """Test creation of empty result"""
        empty_result = extractor._create_empty_result()
        assert empty_result['verdict_id'] is None
        assert empty_result['court_name'] is None
        assert empty_result['judge_name'] is None
        assert empty_result['confidence_score'] == 0.0
        assert 'extraction_timestamp' in empty_result
        assert 'file_path' in empty_result 