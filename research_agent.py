import os
from typing import List, TypedDict, Annotated, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# --- 環境変数の読み込み ---
from dotenv import load_dotenv
load_dotenv()

# --- 1. Pydanticモデルによる出力形式の定義 ---
class ResearchPlan(BaseModel):
    """調査計画を定義するクラス"""
    breadth: int = Field(description="調査の広さを示す並列検索クエリ数 (1-5)")
    depth: int = Field(description="調査の深さを示すフォローアップの階層数 (1-3)")
    explanation: str = Field(description="なぜこの広さと深さにしたかの簡単な説明")

class FollowUpQuestions(BaseModel):
    """ユーザーへのフォローアップ質問を定義するクラス"""
    questions: List[str] = Field(description="ユーザーの意図を明確にするための具体的な質問リスト")

class Queries(BaseModel):
    """生成された検索クエリのリストを定義するクラス"""
    queries: List[str] = Field(description="Web検索エンジンで実行するための具体的な検索クエリリスト")

class SearchResultSummary(BaseModel):
    """検索結果の要約と次のアクションを定義するクラス"""
    learnings: List[str] = Field(description="検索結果から得られた最も重要な学びや洞察のリスト")
    follow_up_queries: List[str] = Field(description="このトピックをさらに深掘りするための新しい検索クエリリスト")

# --- 2. 状態管理 (State) の定義 ---
class AgentState(TypedDict):
    initial_query: str
    combined_query: str
    research_plan: ResearchPlan
    queries_to_run: List[str]
    completed_queries: List[str]
    all_learnings: List[str]
    current_depth: int
    final_report: str
    follow_up_for_user: FollowUpQuestions

# --- 3. ツールとモデルの初期化 ---
google_api_key = os.getenv("GOOGLE_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

if not google_api_key:
    raise ValueError("Google API Key not found. Please set the GOOGLE_API_KEY environment variable in your .env file.")
if not tavily_api_key:
    raise ValueError("Tavily API Key not found. Please set the TAVILY_API_KEY environment variable in your .env file.")

model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, google_api_key=google_api_key)
creative_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7, google_api_key=google_api_key)
tavily_tool = TavilySearchResults(max_results=4, tavily_api_key=tavily_api_key)

# --- 4. LCELによるチェーンの定義 ---
plan_prompt = ChatPromptTemplate.from_template(
    """ユーザーの調査クエリを分析し、調査の広さ(breadth)と深さ(depth)を決定してください。クエリ: {query}"""
)
plan_chain = plan_prompt | model.with_structured_output(ResearchPlan)

ask_user_prompt = ChatPromptTemplate.from_template(
    """ユーザーの調査クエリに基づき、その意図をより明確にするためのフォローアップ質問を3つ生成してください。クエリ: {query}"""
)
ask_user_chain = ask_user_prompt | model.with_structured_output(FollowUpQuestions)

generate_queries_prompt = ChatPromptTemplate.from_template(
    """あなたはリサーチアシスタントです。以下のトピックについて調査するための検索クエリを{num_queries}個生成してください。
トピック: {topic}
これまでの学び:
{learnings}
実行済みのクエリ (これらは避けること):
{completed_queries}"""
)
generate_queries_chain = generate_queries_prompt | model.with_structured_output(Queries)

summarize_result_prompt = ChatPromptTemplate.from_template(
    """以下の検索結果を分析し、最も重要な学びと、さらに深掘りするための新しい検索クエリを抽出してください。
検索クエリ: {query}
検索結果:
{results}"""
)
summarize_result_chain = summarize_result_prompt | model.with_structured_output(SearchResultSummary)

generate_report_prompt = ChatPromptTemplate.from_template(
    """あなたはクリエイティブなストーリーテラーです。以下の調査結果を基に、魅力的で洞察に満ちたレポートを作成してください。
調査トピック: {topic}
主要な発見（学び）:
{learnings}"""
)
generate_report_chain = generate_report_prompt | creative_model

# --- 5. LangGraphノードの定義 ---
def plan_research_node(state: AgentState):
    print("--- 調査計画を策定中 ---")
    plan = plan_chain.invoke({"query": state["initial_query"]})
    return {"research_plan": plan}

def ask_user_node(state: AgentState):
    print("--- ユーザーへの質問を生成中 ---")
    questions = ask_user_chain.invoke({"query": state["initial_query"]})
    return {"follow_up_for_user": questions}

def generate_initial_queries_node(state: AgentState):
    print("--- 初期検索クエリを生成中 ---")
    result = generate_queries_chain.invoke({
        "num_queries": state["research_plan"].breadth,
        "topic": state["combined_query"],
        "learnings": "まだありません。",
        "completed_queries": "まだありません。"
    })
    return {"queries_to_run": result.queries, "completed_queries": [], "all_learnings": [], "current_depth": 1}

def execute_search_node(state: AgentState):
    print(f"--- 調査階層 {state['current_depth']} を実行中 ---")
    queries = state["queries_to_run"]
    summaries = [summarize_result_chain.invoke({"query": q, "results": tavily_tool.invoke(q)}) for q in queries]
    new_learnings = [l for s in summaries for l in s.learnings]
    all_learnings = state.get("all_learnings", []) + new_learnings
    next_queries = [q for s in summaries for q in s.follow_up_queries]
    completed = state.get("completed_queries", []) + queries
    return {"all_learnings": all_learnings, "completed_queries": completed, "queries_to_run": next_queries, "current_depth": state["current_depth"] + 1}

def generate_report_node(state: AgentState):
    print("--- 最終レポートを生成中 ---")
    report = generate_report_chain.invoke({"topic": state["combined_query"], "learnings": "\n- ".join(state["all_learnings"])})
    return {"final_report": report.content}

# --- 6. 条件分岐の定義 ---
def should_continue_research(state: AgentState):
    """調査を続けるか判断する関数"""
    return "execute_search" if state["current_depth"] <= state["research_plan"].depth else "generate_report"

def route_initial_step(state: AgentState):
    """
    グラフの開始地点を決定するルーター関数。
    ユーザーからの補足情報(combined_query)があるかどうかで分岐する。
    """
    print("--- 初期ルーティング ---")
    if state.get("combined_query"):
        print("--- ルート: 調査実行へ ---")
        return "generate_initial_queries"
    else:
        print("--- ルート: 計画策定へ ---")
        return "plan_research"

# --- 7. グラフの構築 ---
workflow = StateGraph(AgentState)

# すべてのノードをグラフに追加
workflow.add_node("plan_research", plan_research_node)
workflow.add_node("ask_user", ask_user_node)
workflow.add_node("generate_initial_queries", generate_initial_queries_node)
workflow.add_node("execute_search", execute_search_node)
workflow.add_node("generate_report", generate_report_node)

# ★★★ 変更点: 条件付きエントリーポイントのロジックを修正 ★★★
# 特殊なノード名 `__start__` から条件付きエッジを設定することで、
# `add_conditional_entry_point` と同じ動作を古いバージョンでも実現します。
workflow.add_conditional_edges(
    "__start__",
    route_initial_step,
    {
        "plan_research": "plan_research",
        "generate_initial_queries": "generate_initial_queries",
    },
)

# 残りのグラフの繋がりを定義
workflow.add_edge("plan_research", "ask_user")
# ユーザーに質問した後は、一旦グラフの実行を終了し、ユーザーの入力を待つ
workflow.add_edge("ask_user", END)

workflow.add_edge("generate_initial_queries", "execute_search")
workflow.add_conditional_edges(
    "execute_search",
    should_continue_research,
    {
        "execute_search": "execute_search", # ループ
        "generate_report": "generate_report"
    }
)
workflow.add_edge("generate_report", END)

# グラフをコンパイル
memory = MemorySaver()
deep_research_agent = workflow.compile(checkpointer=memory)

# --- 8. グラフの可視化 ---
try:
    png_data = deep_research_agent.get_graph().draw_png()
    with open("research_graph.png", "wb") as f:
        f.write(png_data)
    print("--- グラフの構造を research_graph.png に保存しました ---")
except Exception as e:
    print(f"--- グラフの可視化に失敗しました: {e} ---")

def get_agent_runnable():
    """コンパイル済みエージェントを返す"""
    return deep_research_agent
