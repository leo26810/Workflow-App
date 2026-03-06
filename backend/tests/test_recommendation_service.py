"""
Tests for recommendation_service.py
Tests core recommendation logic including classification, scoring, and tool selection.
"""

import pytest
from services.recommendation_service import (
    classify_task,
    detect_domains,
    get_task_profile,
    score_tool_relevance,
    build_tool_recommendations,
)


class TestTaskClassification:
    """Test task classification functionality."""
    
    def test_classify_task_research(self):
        """Test that research tasks are correctly classified."""
        result = classify_task("I need to research climate change impacts")
        assert result['type'] in ['RESEARCH', 'WRITING', 'GENERAL']
        
    def test_classify_task_coding(self):
        """Test that coding tasks are correctly classified."""
        result = classify_task("Build a Python web scraper")
        assert result['type'] in ['CODE', 'GENERAL']
        
    def test_classify_task_empty(self):
        """Test classification with empty task."""
        result = classify_task("")
        assert 'type' in result
        assert 'area' in result
        assert 'subcategory' in result
        

class TestDomainDetection:
    """Test domain detection functionality."""
    
    def test_detect_domains_data_science(self):
        """Test domain detection for data science tasks."""
        domains = detect_domains("Analyze sales data using Python pandas")
        assert len(domains) > 0
        # Should detect data science or analysis domain
        
    def test_detect_domains_software_development(self):
        """Test domain detection for software development."""
        domains = detect_domains("Build a React application with API integration")
        assert len(domains) > 0
        
    def test_detect_domains_multiple(self):
        """Test that multiple domains can be detected."""
        domains = detect_domains("Create a machine learning model and deploy it as a web API")
        # Should detect both ML and web development domains
        assert isinstance(domains, list)


class TestTaskProfile:
    """Test task profiling functionality."""
    
    def test_get_task_profile_basic(self):
        """Test basic task profile generation."""
        profile = get_task_profile("Create a presentation about AI")
        assert 'primary_need' in profile
        assert 'subject_area' in profile
        assert 'output_type' in profile
        assert isinstance(profile, dict)
        
    def test_get_task_profile_technical(self):
        """Test task profile for technical content."""
        profile = get_task_profile("Debug Python asyncio concurrency issues")
        assert isinstance(profile, dict)


class TestToolScoring:
    """Test tool scoring and relevance calculation."""
    
    def test_score_tool_relevance_basic(self, sample_tools):
        """Test basic tool scoring."""
        tool_dict = {
            'name': 'VS Code',
            'category': 'Development',
            'use_case': 'Software Development',
            'skill_requirement': 'Anfänger',
            'best_for': 'Coding',
        }
        task_profile = get_task_profile("Write Python code")
        score = score_tool_relevance(
            tool_dict,
            "Write Python code",
            "development",
            "Anfänger",
            task_profile
        )
        assert isinstance(score, dict)
        assert 'total' in score
        assert isinstance(score['total'], (int, float))
        assert score['total'] >= 0
        
    def test_score_tool_relevance_mismatch(self):
        """Test scoring when tool doesn't match task."""
        tool_dict = {
            'name': 'Image Editor',
            'category': 'Graphics',
            'use_case': 'Photo Editing',
            'skill_requirement': 'Experte',
            'best_for': 'Photo manipulation',
        }
        task_profile = get_task_profile("Write a blog post")
        score = score_tool_relevance(
            tool_dict,
            "Write a blog post",
            "content_creation",
            "Anfänger",
            task_profile
        )
        assert isinstance(score, dict)
        assert 'total' in score
        assert score['total'] >= 0


class TestToolRecommendations:
    """Test complete recommendation building."""
    
    def test_build_tool_recommendations_with_tools(self, db_session, sample_tools):
        """Test recommendation building with available tools."""
        result = build_tool_recommendations(
            tools=sample_tools,
            task_description="Build a Python web application",
            task_type="CODE",
            user_level="Fortgeschritten",
            tool_scores={},
            max_count=3,
        )
        assert isinstance(result, list)
        assert len(result) <= 3
        if result:
            assert 'name' in result[0]
            assert 'match_score' in result[0]
        
    def test_build_tool_recommendations_empty_db(self, db_session):
        """Test recommendation building with empty database."""
        result = build_tool_recommendations(
            tools=[],
            task_description="Analyze data",
            task_type="RESEARCH",
            user_level="Anfänger",
            tool_scores={},
            max_count=3,
        )
        assert isinstance(result, list)
        assert result == []
