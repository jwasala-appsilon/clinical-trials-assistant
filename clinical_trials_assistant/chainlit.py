import os
import re

import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict
from langchain_core.messages import AIMessage, HumanMessage

from clinical_trials_assistant.nodes import State, graph
from clinical_trials_assistant.providers import ClinicalTrial
import sqlalchemy
from sqlalchemy import text


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
    conninfo = os.getenv("DATABASE_URL")
    conninfo_async = conninfo.replace("postgresql://", "postgresql+asyncpg://").replace(
        "sqlite:///", "sqlite+aiosqlite:///"
    )

    # Check if migrations are applied
    # For demonstration, assume a table called 'alembic_version' exists after migration
    sync_conninfo = conninfo.replace("postgresql+asyncpg://", "postgresql://").replace(
        "sqlite+aiosqlite:///", "sqlite:///"
    )
    engine = sqlalchemy.create_engine(sync_conninfo)
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
            )
        )
        migration_applied = result.fetchone() is not None

        if not migration_applied:
            # Run DDL script
            ddl_path = os.path.join(os.path.dirname(__file__), "../scripts/ddl.sql")
            with open(ddl_path, "r") as ddl_file:
                statements = re.split(r";\s*$", ddl_file.read(), flags=re.MULTILINE)
                for statement in statements:
                    if statement:
                        conn.execute(text(statement))
                        conn.commit()

    return SQLAlchemyDataLayer(conninfo=conninfo_async)


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
    retrieved_state = {}

    with cl.Step(name="Clinical Trial Assistant"):
        async for mode, data in graph.astream(
            state, stream_mode=["updates", "messages"]
        ):
            if mode == "updates":
                name_key = next(iter(data))
                name_formatted = {
                    "validate": "validate_request",
                    "retrieve": f"query_clinical_trials_gov",
                    "rerank": "rerank_results",
                    "answer": "prepare_answer",
                }.get(name_key)
                retrieved_state = data.get(name_key, {})

                if name_key == "rerank":
                    # Create sidebar with top retrieved trials
                    top_trials_ids: list[str] = retrieved_state.get(
                        "top_reranked_results_ids", []
                    )
                    top_trials: list[ClinicalTrial] = [
                        trial
                        for trial in retrieved_state.get("retrieved_trials", [])
                        if trial.nct_id in top_trials_ids
                    ]

                    await cl.ElementSidebar.set_elements(
                        [
                            cl.Text(
                                content=f"{t.nct_id}: {t.official_title}", name=t.nct_id
                            )
                            for t in top_trials
                        ]
                    )
                    await cl.ElementSidebar.set_title("Retrieved Trials")

                with cl.Step(name=name_formatted):
                    pass
            else:
                token, metadata = data

                # Workaround to skip the last token which is a repetition of entire message
                if len(token.content) > 100:
                    continue

                if metadata["langgraph_node"] == "answer":
                    await msg.stream_token(token.content)

    messages.append(AIMessage(msg.content))

    # Update session
    cl.user_session.set("messages", messages)
    cl.user_session.set("retrieved_trials", retrieved_state.get("retrieved_trials"))
    cl.user_session.set(
        "top_reranked_results_ids",
        retrieved_state.get("top_reranked_results_ids"),
    )


@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="ibuprofen ± caffeine for back pain treatment",
            message="What is the effect of ibuprofen ± caffeine for back pain treatment?",
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
