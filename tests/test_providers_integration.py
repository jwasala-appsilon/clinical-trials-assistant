from clinical_trials_assistant.providers import (
    MAX_TRIALS_PER_QUERY,
    ClinicalTrial,
    fetch_clinical_trials,
)


class TestIntegrationFetchClinicalTrialsDescriptions:
    """Integration test suite for fetch_clinical_trials_descriptions function."""

    def test_successful_api_call_with_ibuprofen_query(self) -> None:
        """Integration test that the function returns valid results for a real API call with 'ibuprofen' query."""
        query = "ibuprofen"

        results = fetch_clinical_trials(query)

        assert len(results) > 0, "Should return at least one trial for ibuprofen query"
        assert len(results) <= MAX_TRIALS_PER_QUERY, (
            f"Should not exceed {MAX_TRIALS_PER_QUERY} trials"
        )

        # Check that all results are properly structured
        for trial in results:
            assert isinstance(trial, ClinicalTrial)
            assert trial.nct_id is not None and trial.nct_id.strip() != ""
            assert (
                trial.official_title is not None and trial.official_title.strip() != ""
            )
            assert trial.brief_summary is not None and trial.brief_summary.strip() != ""
            # NCT IDs should follow the pattern NCTXXXXXXXX
            assert trial.nct_id.startswith("NCT"), (
                f"NCT ID should start with 'NCT', got: {trial.nct_id}"
            )
            assert trial.results_section is not None, (
                f"Results section should not be None, got: {trial.results_section}"
            )
