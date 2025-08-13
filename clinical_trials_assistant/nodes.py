from logging import getLogger

from langchain.chat_models import init_chat_model
from langchain.output_parsers.boolean import BooleanOutputParser
from langchain_core.messages import AIMessage
from langchain_core.output_parsers.json import JsonOutputParser
from langchain_core.output_parsers.list import CommaSeparatedListOutputParser
from langchain_core.output_parsers.string import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langgraph.graph import END, START, MessagesState, StateGraph

from clinical_trials_assistant.providers import ClinicalTrial, fetch_clinical_trials

logger = getLogger(__name__)


class State(MessagesState):
    """State for the clinical trials assistant."""

    retrieved_trials: list[ClinicalTrial] | None
    top_reranked_results_ids: list[str] | None
    is_valid_request: bool | None


def determine_if_followup_question(state: State) -> bool:
    return state["retrieved_trials"] is not None


def determine_if_valid_request(state: State) -> bool:
    return state["is_valid_request"] or False


def determine_if_retrieved_trials_available(state: State) -> bool:
    return state["retrieved_trials"] is not None and len(state["retrieved_trials"]) > 0


def determine_if_reranked_trials_relevant(state: State) -> bool:
    return (
        state["top_reranked_results_ids"] is not None
        and len(state["top_reranked_results_ids"]) > 0
    )


def validate(state: State) -> State:
    prompt = PromptTemplate(
        template=(
            "Is the following user message a question that can be at least partially answered by analyzing clinical trials' descriptions and results? Answer with YES or NO only in uppercase, no extra text.\n"
            "User message: {message}"
        ),
        input_variables=["message"],
    )
    llm = init_chat_model("openai:gpt-4.1-mini")
    parser = BooleanOutputParser()

    chain = prompt | llm | parser

    state["is_valid_request"] = chain.invoke({"message": state["messages"][-1].content})
    return state


def retrieve(state: State) -> State:
    prompt = PromptTemplate(
        template=(
            "You are building ClinicalTrials.gov API search requests.\n"
            "You must output a single valid JSON object with zero or more of the following keys "
            "(only those relevant to the user request):\n"
            "  - query.cond   → Conditions or disease (ConditionSearch area)\n"
            "  - query.term   → Other terms (BasicSearch area)\n"
            "  - query.locn   → Location terms (LocationSearch area)\n"
            "  - query.titles → Title / acronym (TitleSearch area)\n"
            "  - query.intr   → Intervention / treatment (InterventionSearch area)\n"
            "  - query.outc   → Outcome measure (OutcomeSearch area)\n"
            "  - query.spons  → Sponsor / collaborator (SponsorSearch area)\n"
            "  - query.lead   → Lead sponsor name (LeadSponsorName field)\n"
            "  - query.id     → Study IDs (IdSearch area)\n"
            "  - query.patient→ PatientSearch area (broad multi-field relevance)\n\n"
            "Each value must be an Essie search expression targeting that area.\n"
            "Do NOT include unrelated keys. Keep values concise but specific.\n\n"
            "============================\n"
            "📘 Essie Syntax Crash Course\n"
            "============================\n"
            "- Boolean: OR, AND, NOT\n"
            '- Grouping: "quoted phrase" or ( ... )\n'
            "- Context operators:\n"
            "    AREA[<SearchArea>]term → search in specific field/area\n"
            "    EXPANSION[Concept|Term|None|Relaxation|Lossy]term → synonym/stemming control\n"
            "    COVERAGE[FullMatch|StartsWith|EndsWith|Contains]term → match control\n"
            "    SEARCH[Location]( ... ) → match multiple fields in same section\n"
            "- Source operators:\n"
            "    RANGE[min,max] → date/number range (e.g., AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX])\n"
            "      Important - only use RANGE with individual fields, eg. AREA[LastUpdatePostDate]RANGE[2023-01-15,MAX] and not AREA[BasicSearch]RANGE[2023-01-15,MAX]\n"
            "    MISSING → find where field has no value\n"
            "- Scoring: TILT[FieldName]term → bias ranking by date/size\n\n"
            "============================\n"
            "🎯 Key Search Areas (for AREA[])\n"
            "============================\n"
            "ConditionSearch (query.cond): Condition, BriefTitle, OfficialTitle, ConditionMeshTerm, ConditionAncestorTerm, Keyword, NCTId.\n\n"
            "BasicSearch (query.term): NCTId, Acronym, BriefTitle, OfficialTitle, Condition, InterventionName, InterventionOtherName, Phase, StdAge, PrimaryOutcomeMeasureKeyword, BriefSummary, ArmGroupLabel, SecondaryOutcomeMeasure, InterventionDescription, ArmGroupDescription, PrimaryOutcomeDescription, LeadSponsorName, OrgStudyId, SecondaryId, NCTIdAlias, InterventionType, ArmGroupType, SecondaryOutcomeDescription, LocationFacility, LocationState, LocationCountry, LocationCity, LocationStatus, BioSpecDescription, ResponsiblePartyInvestigatorFullName, ResponsiblePartyInvestigatorTitle, ResponsiblePartyInvestigatorAffiliation, ResponsiblePartyOldNameTitle, ResponsiblePartyOldOrganization, OverallOfficialAffiliation, OverallOfficialRole, OverallOfficialName, CentralContactName, ConditionMeshTerm, InterventionMeshTerm, DesignAllocation, DesignInterventionModel, DesignMasking, DesignWhoMasked, DesignObservationalModel, DesignPrimaryPurpose, DesignTimePerspective, StudyType, ConditionAncestorTerm, InterventionAncestorTerm, CollaboratorName, OtherOutcomeMeasure, OutcomeMeasureTitle, OtherOutcomeDescription, OutcomeMeasureDescription, LocationContactName.\n\n"
            "LocationSearch (query.locn): LocationCity, LocationState, LocationCountry, LocationFacility, LocationZip.\n\n"
            "TitleSearch (query.titles): Acronym, BriefTitle, OfficialTitle.\n\n"
            "InterventionSearch (query.intr): InterventionName, InterventionType, ArmGroupType, InterventionOtherName, BriefTitle, OfficialTitle, ArmGroupLabel, InterventionMeshTerm, Keyword, InterventionAncestorTerm, InterventionDescription, ArmGroupDescription.\n\n"
            "OutcomeSearch (query.outc): PrimaryOutcomeMeasure, SecondaryOutcomeMeasure, PrimaryOutcomeDescription, SecondaryOutcomeDescription, OtherOutcomeMeasure, OutcomeMeasureTitle, OtherOutcomeDescription, OutcomeMeasureDescription, OutcomeMeasurePopulationDescription.\n\n"
            "SponsorSearch (query.spons): LeadSponsorName, CollaboratorName, OrgFullName.\n\n"
            "LeadSponsorName (query.lead): LeadSponsorName.\n\n"
            "IdSearch (query.id): NCTId, NCTIdAlias, Acronym, OrgStudyId, SecondaryId.\n\n"
            "PatientSearch (query.patient): Acronym, Condition, BriefTitle, OfficialTitle, ConditionMeshTerm, ConditionAncestorTerm, BriefSummary, Keyword, InterventionName, InterventionOtherName, PrimaryOutcomeMeasure, StdAge, ArmGroupLabel, SecondaryOutcomeMeasure, InterventionDescription, ArmGroupDescription, PrimaryOutcomeDescription, LeadSponsorName, OrgStudyId, SecondaryId, NCTIdAlias, SecondaryOutcomeDescription, LocationFacility, LocationState, LocationCountry, LocationCity, BioSpecDescription, ResponsiblePartyInvestigatorFullName, ResponsiblePartyInvestigatorTitle, ResponsiblePartyInvestigatorAffiliation, ResponsiblePartyOldNameTitle, ResponsiblePartyOldOrganization, OverallOfficialAffiliation, OverallOfficialName, CentralContactName, DesignInterventionModel, DesignMasking, DesignWhoMasked, DesignObservationalModel, DesignPrimaryPurpose, DesignTimePerspective, InterventionMeshTerm, InterventionAncestorTerm, CollaboratorName, OtherOutcomeMeasure, OtherOutcomeDescription, LocationContactName.\n\n"
            "============================\n"
            "User message: {message}\n"
            "Return ONLY a JSON object with the relevant query.* keys and Essie expressions.\n"
            "Keep the query very simple by only including most important keywords and filters explicitly asked by the user. \n"
        ),
        input_variables=["message"],
    )

    llm = init_chat_model("openai:gpt-4.1")
    parser = JsonOutputParser()
    chain = prompt | llm | parser

    query_dict = chain.invoke({"message": state["messages"][-1].content})
    logger.info(
        f"Fetching clinical trials with query dict: {query_dict}, type: {type(query_dict)}"
    )
    studies = fetch_clinical_trials(query_dict)

    state["retrieved_trials"] = studies
    return state


def rerank(state: State) -> State:
    if not state["retrieved_trials"]:
        raise ValueError("No trials retrieved to rerank.")

    prompt = PromptTemplate(
        template=(
            "Given user message and a list of description and NCT IDs of clinical trials, return a comma-separated list of NCT IDs of up to three most relevant trials.\n"
            "If no trials seem to address the user question, return an empty list.\n"
            "User message: {message}\n"
            "Clinical trials:\n"
            "{trials}"
        ),
        input_variables=["message", "trials"],
    )
    llm = init_chat_model("openai:gpt-4.1-mini")
    parser = CommaSeparatedListOutputParser()

    chain = prompt | llm | parser

    trials = "\n".join(
        f"{trial.nct_id}: {trial.official_title} - {trial.brief_summary}"
        for trial in state["retrieved_trials"]
    )

    state["top_reranked_results_ids"] = chain.invoke(
        {
            "message": state["messages"][-1].content,
            "trials": trials,
        }
    )

    return state


def answer(state: State) -> State:
    if not determine_if_valid_request(state):
        state["messages"].append(
            AIMessage(
                "This is not a valid question related to clinical trials. Please ask something else."
            )
        )
        return state
    if not determine_if_retrieved_trials_available(
        state
    ) or not determine_if_reranked_trials_relevant(state):
        state["messages"].append(
            AIMessage(
                "I could not find any clinical trials related to your question. Please try asking something else."
            )
        )
        return state

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant, providing information about clinical trials. Your answers should be based only on following studies:\n{trials}",
            ),
            *state["messages"],
        ]
    )
    llm = init_chat_model("openai:gpt-4.1-mini")
    parser = StrOutputParser()

    chain = prompt | llm | parser

    trials = "\n".join(
        f"{trial.nct_id}: {trial.official_title} - {trial.brief_summary}\n{trial.results_section}"
        for trial in state["retrieved_trials"] or []
        if trial.nct_id in (state["top_reranked_results_ids"] or [])
    )

    response = AIMessage(
        chain.invoke({"trials": trials}),
    )

    state["messages"].append(response)

    return state


builder = StateGraph(State)

builder.add_node("validate", validate)
builder.add_node("retrieve", retrieve)
builder.add_node("rerank", rerank)
builder.add_node("answer", answer)

builder.add_edge(START, "validate")

# Only proceed to the full retrieval logic if it's the first valid question.
# Otherwise, assume that the answer can be provided directly (either a decline message or a followup answer.)
builder.add_conditional_edges(
    "validate",
    lambda state: {
        (True, True): "answer",
        (True, False): "retrieve",
        (False, True): "answer",
        (False, False): "answer",
    }.get((determine_if_valid_request(state), determine_if_followup_question(state))),
)

builder.add_conditional_edges(
    "retrieve",
    determine_if_retrieved_trials_available,
    {
        True: "rerank",
        False: "answer",
    },
)

builder.add_edge("rerank", "answer")

builder.add_edge("answer", END)

graph = builder.compile()
