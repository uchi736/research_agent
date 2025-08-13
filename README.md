# Deep Research Agent 🧠

LangChainとLangGraphを使用して構築された高度なAI駆動の調査アシスタント。任意のトピックについて自律的に詳細な調査を実施し、引用付きの包括的なレポートを生成します。

## 機能

- **自律的な調査計画**: クエリに基づいて調査の幅と深さを自動的に決定
- **多層的な調査**: より深い洞察を得るためのフォローアップクエリによる反復検索
- **インタラクティブなユーザーエンゲージメント**: 調査の意図をより理解するための明確化質問
- **出典の帰属**: 適切な引用と参照リンクを含むレポートの生成
- **リアルタイムの進捗追跡**: 調査プロセス中の視覚的フィードバック
- **Webベースインターフェース**: ユーザーフレンドリーなStreamlitアプリケーション

## アーキテクチャ

エージェントは、LangGraphによって駆動される状態ベースのワークフローを使用し、以下のコンポーネントで構成されています：

1. **調査計画**: 初期クエリを分析して調査戦略を決定
2. **ユーザー明確化**: 調査範囲を絞り込むためのフォローアップ質問を生成
3. **クエリ生成**: 包括的なカバレッジのための最適化された検索クエリを作成
4. **反復検索**: 検索を実行し、結果に基づいてフォローアップクエリを生成
5. **レポート生成**: すべての結果を引用付きの構造化されたレポートに統合

## 前提条件

- Python 3.8以上
- Google Gemini APIキー
- Tavily Search APIキー

## インストール

1. リポジトリをクローン:
```bash
git clone https://github.com/uchi736/research_agent.git
cd research_agent
```

2. 仮想環境を作成:
```bash
python -m venv myenv
source myenv/bin/activate  # Windowsの場合: myenv\Scripts\activate
```

3. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

4. 環境変数を設定:
プロジェクトルートに`.env`ファイルを作成し、以下を追加:
```env
GOOGLE_API_KEY=あなたのGoogle APIキー
TAVILY_API_KEY=あなたのTavily APIキー

# オプション: LangSmithトレーシング用
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=あなたのLangSmith APIキー
LANGCHAIN_PROJECT=Deep Research Agent
```

## 使用方法

1. Streamlitアプリケーションを起動:
```bash
streamlit run app.py
```

2. ブラウザを開いて `http://localhost:8501` にアクセス

3. 調査トピックまたは質問を入力

4. 調査範囲を絞り込むためのフォローアップ質問に回答

5. エージェントが調査を実施してレポートを生成するまで待機

## プロジェクト構造

```
deepresearch/
├── app.py                 # Streamlit Webインターフェース
├── research_agent.py      # コアエージェントロジックとワークフロー
├── requirements.txt       # Python依存関係
├── .env                  # 環境変数（作成が必要）
└── README.md            # このファイル
```

## 主要コンポーネント

### research_agent.py
- **Pydanticモデル**: 調査計画、クエリ、結果のための構造化データモデル
- **LangChainチェーン**: さまざまな調査タスクのためのLCELチェーン
- **LangGraphワークフロー**: 調査プロセスを管理する状態マシン
- **検索統合**: Web検索のためのTavily API
- **引用管理**: ソースを追跡し、適切な引用を作成

### app.py
- **セッション管理**: インタラクション全体で会話状態を維持
- **インタラクティブUI**: 調査クエリのためのユーザーフレンドリーなインターフェース
- **進捗追跡**: 調査中のリアルタイム更新
- **メッセージ履歴**: 完全な会話フローを表示

## 動作の仕組み

1. **初期クエリ**: ユーザーが調査トピックを提供
2. **計画作成**: エージェントがクエリを分析し、調査計画を作成
3. **明確化**: エージェントが範囲をよりよく理解するためのフォローアップ質問
4. **反復検索**: エージェントが複数層の検索を実行:
   - トピックに基づく初期の幅広い検索
   - 初期結果に基づくフォローアップ検索
   - 計画された深さに達するまで継続
5. **レポート生成**: すべての結果を引用付きの包括的なレポートに統合

## 設定

### 調査パラメータ
- **幅（Breadth）**: 並列検索クエリの数（1-5）
- **深さ（Depth）**: フォローアップ検索層の数（1-3）

### モデル設定
- **プライマリモデル**: Google Gemini 2.0 Flash（temperature=0）
- **クリエイティブモデル**: Google Gemini 2.0 Flash（temperature=0.7）レポート生成用

## APIキー

### Google Gemini API
[Google AI Studio](https://makersuite.google.com/app/apikey)からAPIキーを取得

### Tavily Search API
[Tavily](https://tavily.com/)からAPIキーを取得

## トラブルシューティング

### よくある問題

1. **APIキーエラー**: `.env`ファイルに有効なAPIキーが含まれていることを確認
2. **インポートエラー**: `pip install -r requirements.txt`ですべての依存関係がインストールされていることを確認
3. **グラフの可視化**: グラフPNGの生成に失敗する場合、システムにgraphvizがインストールされていることを確認

## 貢献

貢献を歓迎します！プルリクエストを送信したり、バグや機能リクエストのためのイシューを開いてください。

## ライセンス

このプロジェクトはオープンソースで、MITライセンスの下で利用可能です。

## 謝辞

- [LangChain](https://github.com/langchain-ai/langchain)と[LangGraph](https://github.com/langchain-ai/langgraph)で構築
- 言語処理に[Google Gemini](https://deepmind.google/technologies/gemini/)を使用
- Web検索機能は[Tavily](https://tavily.com/)によって提供
- [Streamlit](https://streamlit.io/)でインターフェースを作成

## 作者

uchi736によって作成

---

詳細情報やサポートについては、[GitHub](https://github.com/uchi736/research_agent/issues)でイシューを開いてください。