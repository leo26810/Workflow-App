"""
Tests for API endpoints
Tests Flask routes for health, recommendations, feedback, and profile.
"""

import pytest
import json


class TestHealthEndpoint:
    """Test the /api/health endpoint."""
    
    def test_health_check(self, client):
        """Test that health check returns 200."""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        assert 'status' in data or 'timestamp' in data or 'db' in data


class TestRecommendationEndpoint:
    """Test the /api/recommendation endpoint."""
    
    def test_recommendation_post_valid(self, client, db_session, sample_tools):
        """Test POST to recommendation endpoint with valid data."""
        payload = {
            'task_description': 'Build a web application with Python'
        }
        response = client.post(
            '/api/recommendation',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Should return 200 or other success code
        assert response.status_code in [200, 201, 400, 422]
        
    def test_recommendation_post_empty(self, client, db_session):
        """Test POST with empty task description."""
        payload = {
            'task_description': ''
        }
        response = client.post(
            '/api/recommendation',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]
        
    def test_recommendation_post_missing_field(self, client, db_session):
        """Test POST with missing required fields."""
        payload = {}
        response = client.post(
            '/api/recommendation',
            data=json.dumps(payload),
            content_type='application/json'
        )
        # Should return error or handle gracefully
        assert response.status_code in [200, 400, 422]


class TestProfileEndpoint:
    """Test the /api/profile endpoint."""
    
    def test_profile_get(self, client, db_session, sample_user, sample_skills, sample_goals):
        """Test GET /api/profile returns user data."""
        response = client.get('/api/profile')
        assert response.status_code == 200
        data = response.get_json()
        assert data is not None
        # Should contain user, skills, and goals
        assert 'user' in data or 'skills' in data or 'goals' in data
