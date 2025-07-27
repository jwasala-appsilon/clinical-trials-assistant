import os

import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict
from langchain_core.messages import AIMessage, HumanMessage

from clinical_trials_assistant.nodes import State, graph


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    if (username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
        return None


@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(
        conninfo=os.getenv("DATABASE_URL").replace(
            "postgresql://", "postgresql+asyncpg://"
        )
    )


@cl.on_chat_start
async def on_chat_start():
    pass


@cl.on_message
async def on_message(message: cl.Message):
    messages = cl.user_session.get("messages") or []
    retrieved_trials = cl.user_session.get("retrieved_trials") or None
    top_reranked_results_ids = cl.user_session.get("top_reranked_results_ids") or None
    messages.append(HumanMessage(message.content))

    state = State(
        messages=messages,
        is_valid_request=None,
        retrieved_trials=retrieved_trials,
        top_reranked_results_ids=top_reranked_results_ids,
    )

    msg = cl.Message(content="", author="ai")

    with cl.Step(name="Clinical Trial Assistant"):
        async for data in graph.astream(state, stream_mode="updates"):
            # TODO: think about a better way to handle displaying steps
            # Currently, the step description appears when it's finished
            name_key = next(iter(data))
            name_formatted = {
                "validate": "validate_request",
                "retrieve": f"query_clinical_trials_gov",
                "rerank": "rerank_results",
                "answer": "prepare_answer",
            }.get(name_key)
            with cl.Step(name=name_formatted):
                if name_key == "answer":
                    content = data[name_key]["messages"][-1].content

    await msg.stream_token(content)
    await msg.send()

    messages.append(AIMessage(content))

    cl.user_session.set("messages", messages)
    cl.user_session.set(
        "retrieved_trials", data.get("answer", {}).get("retrieved_trials")
    )
    cl.user_session.set(
        "top_reranked_results_ids",
        data.get("answer", {}).get("top_reranked_results_ids"),
    )


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="ibuprofen ± caffeine for back pain treatment",
            message="What is the effect of ibuprofen ± caffeine for back pain treatment?",
        ),
        cl.Starter(
            label="adverse effects of pseudoephedrine for nasal congestion",
            message="What are the adverse effects of pseudoephedrine for nasal congestion?",
        ),
    ]


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    cl.user_session.set("messages", [])
    messages = []
    persisted_messages = [m for m in thread["steps"]]

    for message in persisted_messages:
        if message["type"] == "user_message":
            messages.append(HumanMessage(message["output"]))
        elif message["type"] == "assistant_message":
            messages.append(AIMessage(message["output"]))

    cl.user_session.set("messages", messages)
