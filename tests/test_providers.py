from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from clinical_trials_assistant.providers import (
    CLINICAL_TRIALS_API_URL,
    MAX_TRIALS_PER_QUERY,
    fetch_clinical_trials,
)


class TestFetchClinicalTrialsDescriptions:
    """Test suite for fetch_clinical_trials_descriptions function."""

    @patch("clinical_trials_assistant.providers.requests.get")
    def test_http_error_raises_exception(self, mock_get: MagicMock) -> None:
        """Test that HTTP errors are properly propagated."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            fetch_clinical_trials("test query")

        # Verify the request was made with correct parameters
        mock_get.assert_called_once_with(
            url=f"{CLINICAL_TRIALS_API_URL}/studies",
            params={
                "query.term": "test query",
                "aggFilters": "results:with,status:com",
                "fields": "NCTId,OfficialTitle,BriefSummary,ResultsSection",
                "pageSize": MAX_TRIALS_PER_QUERY,
            },
        )

    @patch("clinical_trials_assistant.providers.requests.get")
    def test_missing_studies_field_raises_value_error(
        self, mock_get: MagicMock
    ) -> None:
        """Test that missing 'studies' field in response raises ValueError."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {}  # Missing 'studies' field
        mock_get.return_value = mock_response

        with pytest.raises(
            ValueError, match="Field `studies` is missing from the API response."
        ):
            fetch_clinical_trials("test query")

    @patch("clinical_trials_assistant.providers.requests.get")
    def test_successful_response_with_complete_data(self, mock_get: MagicMock) -> None:
        """Test successful parsing of a complete API response."""
        # Mock a successful response with complete trial data
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT12345678",
                            "officialTitle": "Test Clinical Trial for Ibuprofen",
                        },
                        "descriptionModule": {
                            "briefSummary": "This is a test summary of the clinical trial."
                        },
                    },
                    "resultsSection": {
                        "dummy_key_1": "dummy_value_1",
                        "dummy_key_2": "dummy_value_2",
                    },
                },
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT87654321",
                            "officialTitle": "Another Test Trial",
                        },
                        "descriptionModule": {"briefSummary": "Another test summary."},
                    },
                    "resultsSection": {
                        "dummy_key_3": "dummy_value_3",
                        "dummy_key_4": "dummy_value_4",
                    },
                },
            ]
        }
        mock_get.return_value = mock_response

        results = fetch_clinical_trials("test query")

        assert len(results) == 2

        # Check first trial
        assert results[0].nct_id == "NCT12345678"
        assert results[0].official_title == "Test Clinical Trial for Ibuprofen"
        assert (
            results[0].brief_summary == "This is a test summary of the clinical trial."
        )
        assert results[0].results_section == {
            "dummy_key_1": "dummy_value_1",
            "dummy_key_2": "dummy_value_2",
        }

        # Check second trial
        assert results[1].nct_id == "NCT87654321"
        assert results[1].official_title == "Another Test Trial"
        assert results[1].brief_summary == "Another test summary."
        assert results[1].results_section == {
            "dummy_key_3": "dummy_value_3",
            "dummy_key_4": "dummy_value_4",
        }

    @patch("clinical_trials_assistant.providers.requests.get")
    def test_empty_studies_list(self, mock_get: MagicMock) -> None:
        """Test handling of empty studies list."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"studies": []}
        mock_get.return_value = mock_response

        results = fetch_clinical_trials("nonexistent query")

        assert results == []

    @patch("clinical_trials_assistant.providers.requests.get")
    @patch("clinical_trials_assistant.providers.logger")
    def test_incomplete_trial_data_logs_warning(
        self, mock_logger: MagicMock, mock_get: MagicMock
    ) -> None:
        """Test that trials with missing fields are logged as warnings and still included."""
        # Mock response with incomplete trial data
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT12345678"
                            # Missing officialTitle
                        },
                        "descriptionModule": {
                            "briefSummary": "This is a test summary."
                        },
                    }
                    # Missing resultsSection
                },
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT87654321",
                            "officialTitle": "Complete Trial",
                        },
                        "descriptionModule": {"briefSummary": "Complete summary."},
                    },
                    "resultsSection": {
                        "dummy_key": "dummy_value",
                    },
                },
            ]
        }
        mock_get.return_value = mock_response

        results = fetch_clinical_trials("test query")

        # Should return only trials with complete data
        assert len(results) == 1

        # Check that warning was logged for incomplete trial
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Skipping trial with missing fields" in warning_call
        assert "NCT12345678" in warning_call

    @patch("clinical_trials_assistant.providers.requests.get")
    def test_correct_api_parameters(self, mock_get: MagicMock) -> None:
        """Test that the correct parameters are sent to the API."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"studies": []}
        mock_get.return_value = mock_response

        query = "diabetes treatment"
        fetch_clinical_trials(query)

        # Verify correct API call
        mock_get.assert_called_once_with(
            url=f"{CLINICAL_TRIALS_API_URL}/studies",
            params={
                "query.term": query,
                "aggFilters": "results:with,status:com",
                "fields": "NCTId,OfficialTitle,BriefSummary,ResultsSection",
                "pageSize": MAX_TRIALS_PER_QUERY,
            },
        )

    @patch("clinical_trials_assistant.providers.requests.get")
    def test_network_timeout_error(self, mock_get: MagicMock) -> None:
        """Test handling of network timeout errors."""
        mock_get.side_effect = requests.Timeout("Request timed out")

        with pytest.raises(requests.Timeout):
            fetch_clinical_trials("test query")

    @patch("clinical_trials_assistant.providers.requests.get")
    def test_connection_error(self, mock_get: MagicMock) -> None:
        """Test handling of connection errors."""
        mock_get.side_effect = requests.ConnectionError("Connection failed")

        with pytest.raises(requests.ConnectionError):
            fetch_clinical_trials("test query")
