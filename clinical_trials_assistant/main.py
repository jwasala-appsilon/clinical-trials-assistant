import streamlit as st
from langchain_core.messages import HumanMessage

from clinical_trials_assistant.nodes import State, graph


def start_streamlit_gui():
    st.set_page_config(page_title="Clinical Trials Assistant", page_icon="💬")

    st.title("💬 Clinical Trials Assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    user_input = st.text_input("You:", key="user_input")

    if user_input:
        st.session_state.messages.append(HumanMessage(user_input))
        response = graph.invoke(
            State(
                messages=st.session_state.messages,
                is_valid_request=None,
                retrieved_trials=None,
                top_reranked_results_ids=None,
            )
        )
        st.session_state.messages.append(response["messages"][-1])

    for msg in st.session_state.messages:
        if hasattr(msg, "content"):
            if msg.type == "human":
                st.markdown(f"**You:** {msg.content}")
            else:
                st.markdown(f"**Assistant:** {msg.content}")


if __name__ == "__main__":
    start_streamlit_gui()
