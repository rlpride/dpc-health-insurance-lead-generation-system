"""Unit tests for lead scoring algorithm."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

from models.lead_score import LeadScore
from models.company import Company
from workers.scoring_worker import ScoringWorker


class TestLeadScore:
    """Test cases for LeadScore model."""
    
    def test_calculate_grade_a_plus(self):
        """Test grade calculation for A+ score."""
        assert LeadScore.calculate_grade(95) == "A+"
        assert LeadScore.calculate_grade(100) == "A+"
    
    def test_calculate_grade_a(self):
        """Test grade calculation for A score."""
        assert LeadScore.calculate_grade(90) == "A"
        assert LeadScore.calculate_grade(94) == "A"
    
    def test_calculate_grade_a_minus(self):
        """Test grade calculation for A- score."""
        assert LeadScore.calculate_grade(85) == "A-"
        assert LeadScore.calculate_grade(89) == "A-"
    
    def test_calculate_grade_b_plus(self):
        """Test grade calculation for B+ score."""
        assert LeadScore.calculate_grade(80) == "B+"
        assert LeadScore.calculate_grade(84) == "B+"
    
    def test_calculate_grade_b(self):
        """Test grade calculation for B score."""
        assert LeadScore.calculate_grade(75) == "B"
        assert LeadScore.calculate_grade(79) == "B"
    
    def test_calculate_grade_b_minus(self):
        """Test grade calculation for B- score."""
        assert LeadScore.calculate_grade(70) == "B-"
        assert LeadScore.calculate_grade(74) == "B-"
    
    def test_calculate_grade_c_plus(self):
        """Test grade calculation for C+ score."""
        assert LeadScore.calculate_grade(65) == "C+"
        assert LeadScore.calculate_grade(69) == "C+"
    
    def test_calculate_grade_c(self):
        """Test grade calculation for C score."""
        assert LeadScore.calculate_grade(60) == "C"
        assert LeadScore.calculate_grade(64) == "C"
    
    def test_calculate_grade_c_minus(self):
        """Test grade calculation for C- score."""
        assert LeadScore.calculate_grade(55) == "C-"
        assert LeadScore.calculate_grade(59) == "C-"
    
    def test_calculate_grade_d(self):
        """Test grade calculation for D score."""
        assert LeadScore.calculate_grade(0) == "D"
        assert LeadScore.calculate_grade(54) == "D"
    
    def test_is_high_quality_true(self):
        """Test high quality detection for scores >= 80."""
        lead_score = LeadScore(total_score=80)
        assert lead_score.is_high_quality is True
        
        lead_score.total_score = 95
        assert lead_score.is_high_quality is True
    
    def test_is_high_quality_false(self):
        """Test high quality detection for scores < 80."""
        lead_score = LeadScore(total_score=79)
        assert lead_score.is_high_quality is False
        
        lead_score.total_score = 50
        assert lead_score.is_high_quality is False
    
    def test_is_medium_quality_true(self):
        """Test medium quality detection for scores 60-79."""
        lead_score = LeadScore(total_score=60)
        assert lead_score.is_medium_quality is True
        
        lead_score.total_score = 75
        assert lead_score.is_medium_quality is True
        
        lead_score.total_score = 79
        assert lead_score.is_medium_quality is True
    
    def test_is_medium_quality_false(self):
        """Test medium quality detection outside 60-79 range."""
        lead_score = LeadScore(total_score=59)
        assert lead_score.is_medium_quality is False
        
        lead_score.total_score = 80
        assert lead_score.is_medium_quality is False
    
    def test_to_dict(self):
        """Test lead score dictionary conversion."""
        company_id = uuid4()
        lead_score_id = uuid4()
        created_at = datetime.utcnow()
        
        lead_score = LeadScore(
            id=lead_score_id,
            company_id=company_id,
            total_score=85,
            score_grade="A-",
            industry_score=80,
            size_score=90,
            location_score=85,
            data_quality_score=85,
            engagement_score=75,
            industry_risk_level="medium",
            size_category="large", 
            scoring_factors={"test": "data"},
            score_reasons=["High employee count", "Good location"],
            recommendations="Focus on decision makers",
            created_at=created_at
        )
        
        result = lead_score.to_dict()
        
        expected = {
            "id": str(lead_score_id),
            "company_id": str(company_id),
            "total_score": 85,
            "score_grade": "A-",
            "industry_score": 80,
            "size_score": 90,
            "location_score": 85,
            "data_quality_score": 85,
            "engagement_score": 75,
            "industry_risk_level": "medium",
            "size_category": "large",
            "scoring_factors": {"test": "data"},
            "score_reasons": ["High employee count", "Good location"],
            "recommendations": "Focus on decision makers",
            "created_at": created_at.isoformat(),
        }
        
        assert result == expected
    
    def test_to_dict_none_created_at(self):
        """Test dictionary conversion with None created_at."""
        lead_score = LeadScore(
            id=uuid4(),
            company_id=uuid4(),
            total_score=75,
            created_at=None
        )
        
        result = lead_score.to_dict()
        assert result["created_at"] is None


class TestScoringWorkerCalculateScore:
    """Test cases for ScoringWorker calculate_score method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.worker = ScoringWorker("test-worker-123")
    
    def test_calculate_score_basic(self):
        """Test basic score calculation."""
        # Create mock company
        company = Mock(spec=Company)
        company.naics_code = "621111"
        company.employee_count_min = 50
        company.state = "CA"
        company.contacts = []
        
        result = self.worker.calculate_score(company)
        
        # Check structure
        assert "total_score" in result
        assert "industry_score" in result
        assert "size_score" in result
        assert "location_score" in result
        assert "data_quality_score" in result
        assert "factors" in result
        
        # Check total score calculation (average of component scores)
        expected_total = (70 + 80 + 75 + 85) // 4
        assert result["total_score"] == expected_total
        
        # Check factors
        factors = result["factors"]
        assert factors["naics_code"] == "621111"
        assert factors["employee_count"] == 50
        assert factors["state"] == "CA"
        assert factors["has_contacts"] is False
    
    def test_calculate_score_with_contacts(self):
        """Test score calculation with contacts."""
        company = Mock(spec=Company)
        company.naics_code = "621111"
        company.employee_count_min = 100
        company.state = "TX"
        company.contacts = [Mock(), Mock()]  # Mock contacts
        
        result = self.worker.calculate_score(company)
        
        factors = result["factors"]
        assert factors["has_contacts"] is True
        assert len(company.contacts) == 2


class TestScoringWorkerProcessMessage:
    """Test cases for ScoringWorker process_message method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.worker = ScoringWorker("test-worker-123")
        self.worker.settings = Mock()
        self.worker.settings.high_score_threshold = 80
    
    @patch('workers.scoring_worker.get_db_session')
    @patch.object(ScoringWorker, 'publish_message')
    def test_process_message_success_high_score(self, mock_publish, mock_db_session):
        """Test successful message processing with high score."""
        # Setup mocks
        mock_db = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        company_id = str(uuid4())
        company = Mock(spec=Company)
        company.id = company_id
        company.naics_code = "621111"
        company.employee_count_min = 100
        company.state = "CA"
        company.contacts = []
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = company
        
        # Mock calculate_score to return high score
        with patch.object(self.worker, 'calculate_score') as mock_calc:
            mock_calc.return_value = {
                "total_score": 85,
                "industry_score": 80,
                "size_score": 90,
                "location_score": 85,
                "data_quality_score": 85,
                "factors": {"test": "data"}
            }
            
            result = self.worker.process_message({"company_id": company_id})
        
        # Assertions
        assert result is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Check that high score triggered CRM sync
        mock_publish.assert_called_once_with(
            {"company_id": company_id},
            "companies.to_sync.tasks"
        )
        
        # Check LeadScore creation
        lead_score_call = mock_db.add.call_args[0][0]
        assert lead_score_call.company_id == company_id
        assert lead_score_call.total_score == 85
        assert lead_score_call.score_grade == "A-"
    
    @patch('workers.scoring_worker.get_db_session')
    @patch.object(ScoringWorker, 'publish_message')
    def test_process_message_success_low_score(self, mock_publish, mock_db_session):
        """Test successful message processing with low score."""
        mock_db = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        
        company_id = str(uuid4())
        company = Mock(spec=Company)
        company.id = company_id
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = company
        
        with patch.object(self.worker, 'calculate_score') as mock_calc:
            mock_calc.return_value = {
                "total_score": 65,  # Below threshold
                "industry_score": 60,
                "size_score": 70,
                "location_score": 65,
                "data_quality_score": 65,
                "factors": {"test": "data"}
            }
            
            result = self.worker.process_message({"company_id": company_id})
        
        assert result is True
        # Should not publish to CRM sync queue
        mock_publish.assert_not_called()
    
    def test_process_message_no_company_id(self):
        """Test message processing without company_id."""
        result = self.worker.process_message({})
        assert result is False
    
    def test_process_message_invalid_company_id(self):
        """Test message processing with invalid company_id."""
        result = self.worker.process_message({"company_id": "invalid"})
        assert result is False
    
    @patch('workers.scoring_worker.get_db_session')
    def test_process_message_company_not_found(self, mock_db_session):
        """Test message processing when company not found."""
        mock_db = Mock()
        mock_db_session.return_value.__enter__.return_value = mock_db
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        result = self.worker.process_message({"company_id": str(uuid4())})
        assert result is False
    
    @patch('workers.scoring_worker.get_db_session')
    def test_process_message_database_error(self, mock_db_session):
        """Test message processing with database error."""
        mock_db_session.side_effect = Exception("Database connection failed")
        
        result = self.worker.process_message({"company_id": str(uuid4())})
        assert result is False


@pytest.fixture
def sample_lead_score():
    """Fixture for creating sample LeadScore instance."""
    return LeadScore(
        id=uuid4(),
        company_id=uuid4(),
        total_score=85,
        score_grade="A-",
        industry_score=80,
        size_score=90,
        location_score=85,
        data_quality_score=85,
        created_at=datetime.utcnow()
    )


class TestLeadScoreIntegration:
    """Integration tests for LeadScore with real-like scenarios."""
    
    def test_score_grade_consistency(self, sample_lead_score):
        """Test that score grade matches the total score."""
        sample_lead_score.total_score = 92
        expected_grade = LeadScore.calculate_grade(92)
        sample_lead_score.score_grade = expected_grade
        
        assert sample_lead_score.score_grade == "A"
        assert sample_lead_score.is_high_quality is True
    
    def test_score_boundaries(self):
        """Test scoring at boundary conditions."""
        boundary_scores = [55, 60, 65, 70, 75, 80, 85, 90, 95]
        expected_grades = ["C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]
        
        for score, expected_grade in zip(boundary_scores, expected_grades):
            assert LeadScore.calculate_grade(score) == expected_grade