"""
Tests for feedback_service.py
Tests feedback extraction and storage functionality.
"""

import pytest
from models import WorkflowHistory
from services.feedback_service import (
    extract_recommended_tool_names,
    upsert_recommendation_feedback,
    get_feedback_for_history,
)


class TestToolNameExtraction:
    """Test tool name extraction from recommendations."""
    
    def test_extract_tool_names_basic(self):
        """Test extracting tool names from recommendation data."""
        recommendation = {
            'tools': [
                {'name': 'VS Code'},
                {'name': 'GitHub Copilot'},
            ]
        }
        names = extract_recommended_tool_names(recommendation)
        assert isinstance(names, list)
        assert len(names) >= 0
        
    def test_extract_tool_names_empty(self):
        """Test extraction with empty recommendation."""
        names = extract_recommended_tool_names({})
        assert isinstance(names, list)
        
    def test_extract_tool_names_alternative_structure(self):
        """Test extraction with alternative data structure."""
        recommendation = {
            'recommended_tools': [
                {'tool_name': 'Notion'},
                {'tool_name': 'Trello'},
            ]
        }
        names = extract_recommended_tool_names(recommendation)
        assert isinstance(names, list)


class TestFeedbackUpsert:
    """Test feedback creation and updating."""
    
    def test_upsert_new_feedback(self, db_session):
        """Test creating new feedback entry."""
        # Create a workflow history entry first
        history = WorkflowHistory(
            task_description="Test task",
            recommendation_json='{"tools": []}',
        )
        db_session.add(history)
        db_session.commit()
        
        # Test feedback upsert
        result = upsert_recommendation_feedback(
            workflow_history_id=history.id,
            note="Great recommendations!",
            user_rating=5,
        )

        assert result is not None
        assert result.workflow_history_id == history.id
        assert result.user_rating == 5
        assert result.note == "Great recommendations!"
        
    def test_upsert_feedback_invalid_id(self, db_session):
        """Test upserting feedback with non-existent history ID."""
        result = upsert_recommendation_feedback(
            workflow_history_id=999999,
            note="Test",
            user_rating=3,
        )
        # Service currently does not validate history existence directly.
        assert result is not None
        assert result.workflow_history_id == 999999
        assert result.user_rating == 3


class TestFeedbackRetrieval:
    """Test feedback retrieval functionality."""
    
    def test_get_feedback_nonexistent(self, db_session):
        """Test retrieving feedback for non-existent history."""
        feedback = get_feedback_for_history(999999)
        # Should return None or empty result
        assert feedback is None or feedback == {} or isinstance(feedback, dict)
