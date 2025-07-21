from logging import getLogger

from langchain.chat_models import init_chat_model
from langchain.output_parsers.boolean import BooleanOutputParser
from langchain_core.messages import AIMessage
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
            "Is the following user message a question that can be answered by analyzing clinical trial results? Answer with YES or NO only in uppercase, no extra text.\n"
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
            "Suggest a query to clinicaltrials.gov in Essie expression syntax that maximizes a chance to retrieve studies that are relevant to user message.\n"
            "It should ideally consist of a few keywords, like medication names, disease names, or other relevant terms.\n"
            "User message: {message}"
        ),
        input_variables=["message"],
    )
    llm = init_chat_model("openai:gpt-4.1-mini")
    parser = StrOutputParser()

    chain = prompt | llm | parser

    query = chain.invoke({"message": state["messages"][-1].content})
    logger.info(f"Fetching clinical trials with query: {query}")
    studies = fetch_clinical_trials(query)

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
