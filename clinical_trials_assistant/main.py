import chainlit as cl
from langchain_core.messages import AIMessage, HumanMessage

from clinical_trials_assistant.nodes import State, graph


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("messages", [])


@cl.on_message
async def on_message(message: cl.Message):
    messages = cl.user_session.get("messages") or []
    messages.append(HumanMessage(message.content))

    state = State(
        messages=messages,
        is_valid_request=None,
        retrieved_trials=None,
        top_reranked_results_ids=None,
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


import chainlit as cl


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
        )
    ]
