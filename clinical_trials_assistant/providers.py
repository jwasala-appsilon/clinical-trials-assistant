from dataclasses import dataclass
from logging import getLogger
from typing import Any

import requests

logger = getLogger(__name__)


CLINICAL_TRIALS_API_URL = "https://clinicaltrials.gov/api/v2"
MAX_TRIALS_PER_QUERY = 30


@dataclass
class ClinicalTrial:
    nct_id: str
    official_title: str
    brief_summary: str
    results_section: dict[str, Any]


def fetch_clinical_trials(query: dict) -> list[ClinicalTrial]:
    """Fetch clinical trials that are both completed and have results.

    Args:
        query (dict): Dict where keys are valid ClinicalTrials.gov query parameters
            (e.g., 'query.term', 'query.cond', 'query.locn', etc.)
            and values are Essie expressions for that search area.

    Returns:
        list[ClinicalTrial]: A list of clinical trial descriptions that match the query.
    """
    if not isinstance(query, dict):
        raise TypeError("`query` must be a dict of query parameters.")

    # Allowed query.* keys based on API search areas
    allowed_keys = {
        "query.cond",
        "query.term",
        "query.locn",
        "query.titles",
        "query.intr",
        "query.outc",
        "query.spons",
        "query.lead",
        "query.id",
        "query.patient",
    }

    # Filter only allowed keys and ignore None/empty values
    query_params = {k: v for k, v in query.items() if k in allowed_keys and v}

    if not query_params:
        raise ValueError("No valid non-empty query.* parameters provided.")

    # Add required filters and fields
    query_params.update(
        {
            "aggFilters": "results:with,status:com",  # Only completed with results
            "fields": "NCTId,OfficialTitle,BriefSummary,ResultsSection",
            "pageSize": MAX_TRIALS_PER_QUERY,
        }
    )

    response = requests.get(
        url=f"{CLINICAL_TRIALS_API_URL}/studies",
        params=query_params,
    )
    response.raise_for_status()
    data = response.json()

    if "studies" not in data:
        raise ValueError("Field `studies` is missing from the API response.")

    trials: list[ClinicalTrial] = []
    for trial in data["studies"]:
        nct_id = (
            trial.get("protocolSection", {})
            .get("identificationModule", {})
            .get("nctId")
        )
        official_title = (
            trial.get("protocolSection", {})
            .get("identificationModule", {})
            .get("officialTitle")
        )
        brief_summary = (
            trial.get("protocolSection", {})
            .get("descriptionModule", {})
            .get("briefSummary")
        )
        results_section = trial.get("resultsSection", {})

        if not all([nct_id, official_title, brief_summary, results_section]):
            logger.warning(
                f"Skipping trial with missing fields: "
                f"NCTId={nct_id}, OfficialTitle={official_title}, "
                f"BriefSummary={brief_summary}, ResultsSection={results_section}"
            )
            continue

        trials.append(
            ClinicalTrial(nct_id, official_title, brief_summary, results_section)
        )

    return trials
