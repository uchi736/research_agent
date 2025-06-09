import streamlit as st
import uuid
from research_agent import get_agent_runnable, FollowUpQuestions

# Streamlitページの基本設定
st.set_page_config(page_title="Deep Research Agent", layout="wide")
st.title("🧠 Deep Research Agent")
st.markdown("`LangChain` と `LangGraph` を利用した深掘り調査エージェント。トピックを入力すると、エージェントが自律的に調査計画を立て、Web検索を行い、最終的なレポートを作成します。")

# --- セッション管理 ---
if "agent" not in st.session_state:
    st.session_state.agent = get_agent_runnable()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "step" not in st.session_state:
    st.session_state.step = "start"
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- UIコンポーネント ---
def display_messages():
    """これまでのやり取りを表示する"""
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

def reset_conversation():
    """セッションをリセットして最初からやり直す"""
    st.session_state.clear()
    st.session_state.step = "start"
    st.session_state.messages = []


# --- サイドバー ---
st.sidebar.title("設定")
st.sidebar.button("最初からやり直す", on_click=reset_conversation)
st.sidebar.markdown("---")
st.sidebar.subheader("LangSmith トレース")
st.sidebar.markdown(
    """
    [LangSmith](https://smith.langchain.com/) でエージェントの動作を詳細に追跡するには、`.env` ファイルに以下の設定を追加してください:
    ```
    LANGCHAIN_TRACING_V2="true"
    LANGCHAIN_API_KEY="YOUR_LANGSMITH_API_KEY"
    LANGCHAIN_PROJECT="Deep Research Agent"
    ```
    設定後、このアプリケーションを再起動してください。
    """
)


# --- アプリケーションのメインロジック ---

# 1. 初期クエリの入力ステップ
if st.session_state.step == "start":
    st.info("調査したいトピックや質問を入力してください。")
    initial_query = st.text_input("調査トピック:", key="initial_query_input")
    
    if initial_query:
        st.session_state.messages.append({"role": "user", "content": initial_query})
        
        with st.spinner("エージェントが調査計画を立て、質問を生成しています..."):
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            inputs = {"initial_query": initial_query}
            
            for event in st.session_state.agent.stream(inputs, config, stream_mode="values"):
                if "follow_up_for_user" in event:
                    st.session_state.follow_up_questions = event["follow_up_for_user"].questions
                    st.session_state.research_plan = event["research_plan"]
                    st.session_state.step = "answer_follow_ups"
                    st.rerun()

# 2. フォローアップ質問への回答ステップ
elif st.session_state.step == "answer_follow_ups":
    display_messages()
    
    with st.chat_message("assistant"):
        st.markdown("調査の精度を高めるため、いくつか質問させてください。")
        st.info(f"**調査計画:** 広さ `({st.session_state.research_plan.breadth})`, 深さ `({st.session_state.research_plan.depth})`\n\n**理由:** {st.session_state.research_plan.explanation}")
        
        with st.form("follow_up_form"):
            answers = []
            for i, q in enumerate(st.session_state.follow_up_questions):
                answers.append({"question": q, "answer": st.text_input(q, key=f"answer_{i}")})
            
            if st.form_submit_button("回答を送信して調査を開始"):
                initial_query = st.session_state.messages[0]['content']
                answers_text = "\n".join([f"Q: {a['question']}\nA: {a['answer']}" for a in answers if a['answer']])
                st.session_state.combined_query = f"初期クエリ: {initial_query}\n\nユーザーによる補足:\n{answers_text}"
                
                st.session_state.messages.append({"role": "user", "content": f"フォローアップへの回答:\n```\n{answers_text}\n```"})
                st.session_state.step = "researching"
                st.rerun()

# 3. 調査実行ステップ
elif st.session_state.step == "researching":
    display_messages()
    
    with st.chat_message("assistant"):
        st.markdown("ありがとうございます。ただいまから深掘り調査を開始します。")

        with st.spinner("AIエージェントが調査を実行中です..."):
            progress_area = st.empty()
            
            config = {"configurable": {"thread_id": st.session_state.thread_id}}
            inputs = {"combined_query": st.session_state.combined_query}

            final_report = None
            for event in st.session_state.agent.stream(inputs, config, stream_mode="values"):
                # リアルタイムに進捗を表示
                if "generate_initial_queries" in event:
                    progress_area.info("最初の検索クエリを生成しています...")
                elif "execute_search" in event:
                    current_state = event["execute_search"]
                    progress_area.info(f"**階層 {current_state.get('current_depth', 1)} の調査中...**\n\n次のクエリを実行します:\n- " + "\n- ".join(current_state.get('queries_to_run', [])))
                elif "generate_report" in event:
                    progress_area.info("すべての調査が完了しました。最終レポートを作成しています...")

                if "final_report" in event:
                    final_report = event["final_report"]

            if final_report:
                st.session_state.messages.append({"role": "assistant", "content": final_report})
                st.session_state.step = "done"
                st.rerun()

# 4. 完了ステップ
elif st.session_state.step == "done":
    display_messages()
    st.success("調査が完了しました。")

# 最初の表示
if st.session_state.step == "start":
    display_messages()
