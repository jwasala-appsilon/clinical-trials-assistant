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


def fetch_clinical_trials(query: str) -> list[ClinicalTrial]:
    """Fetch clinical trials that are both completed and have results.

    Args:
        query (str): Query in Essie expression syntax that will be run against fields belonging to the default search area, e.g. OfficialTitle, BriefSummary, Keyword, Condition.

    Returns:
        list[ClinicalTrialDescription]: A list of clinical trial descriptions that match the query.
    """

    response = requests.get(
        url=f"{CLINICAL_TRIALS_API_URL}/studies",
        params={
            "query.term": query,
            # Filters to ensure we only get completed trials with results
            "aggFilters": "results:with,status:com",
            "fields": "NCTId,OfficialTitle,BriefSummary,ResultsSection",
            "pageSize": MAX_TRIALS_PER_QUERY,
        },
    )

    response.raise_for_status()

    data = response.json()
    trials: list[ClinicalTrial] = []

    if "studies" not in data:
        raise ValueError("Field `studies` is missing from the API response.")

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
                f"Skipping trial with missing fields: NCTId={nct_id}, OfficialTitle={official_title}, BriefSummary={brief_summary}, ResultsSection={results_section}"
            )
            continue

        trials.append(
            ClinicalTrial(nct_id, official_title, brief_summary, results_section)
        )

    return trials
