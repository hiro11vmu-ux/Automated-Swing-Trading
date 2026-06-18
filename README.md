# AGIX 売買シグナル LINE通知ツール

AGIX (KraneShares Public-Private AI & Technology ETF) の価格を毎日チェックし、
移動平均(SMA20/50) + RSI(14) + MACD + 簡易ファンダメンタルズ(PER) を
スコア化して「買い/中立/売り」をLINEに自動通知します。

GitHub Actionsで動くため、パソコンやスマホを開いていなくても毎日自動実行されます。

---

## セットアップ手順

### ステップ1: GitHubリポジトリを作る

1. https://github.com にログイン（アカウントがなければ無料登録）
2. 右上の「+」→「New repository」
3. リポジトリ名を決める（例: `agix-signal-bot`）。Public/Privateはどちらでも可（Privateでも無料枠でActionsは動きます）
4. このフォルダ内のファイル（`signal_checker.py`, `requirements.txt`, `.github/workflows/daily_signal.yml`）をそのままアップロード
   - 「Add file」→「Upload files」でドラッグ&ドロップでOK
   - `.github/workflows/daily_signal.yml` はフォルダ構造を保ったままアップロードする必要があります（GitHub上で直接フォルダを作ってファイルを置くのが確実です）

### ステップ2: Alpha Vantage APIキーを確認

すでに登録済みとのことなので、https://www.alphavantage.co/support/#api-key でキーを確認してください。

⚠️ 無料プランはレート制限が厳しめです（5 calls/分、500 calls/日程度）。
このツールは1日1回の実行で2リクエストしか使わないので問題ありません。

### ステップ3: LINE公式アカウントを作る

1. https://entry.line.biz/start/jp/ にアクセスし、LINE公式アカウントを新規作成（無料）
   - 個人の通知用なので、アカウント名は何でも構いません（例: 「AGIXシグナル通知」）
2. 作成後、LINE Official Account Manager（https://manager.line.biz/）にログイン
3. 左メニューの「設定」→「Messaging API」を選択し、「Messaging APIを利用する」を有効化
4. 同じ画面で以下を取得:
   - **チャネルアクセストークン**: 「発行」ボタンを押して発行（長期トークン）
   - **チャネルシークレット**（今回は使いませんが、表示されているもの）

### ステップ4: 自分のLINEユーザーIDを取得

1. ステップ3で作った公式アカウントを、自分のLINEアプリで友達追加する
   （Official Account Managerの画面にQRコードが表示されています）
2. 自分のユーザーIDを知る一番簡単な方法:
   - LINE Developers Console（https://developers.line.biz/console/）→ 作成したチャネルを開く
   - 「Messaging API設定」タブの下にある「あなたのユーザーID」という欄はないため、
     代わりに以下のいずれかで取得します:
     - 方法A: Webhookを一時的に有効にし、自分から公式アカウントにメッセージを送って
       受信したWebhookイベントの `source.userId` を確認する（要: 簡易サーバー or 検証ツール）
     - 方法B（簡単）: LINE Official Account Managerの「チャット」画面で自分とのトーク履歴を開き、
       URLやAPIレスポンスからではなく、下記の「LINE Bot SDK Webhookテストツール」的な
       無料サービス（例: https://webhook.site/ や ngrok + 簡易Flaskサーバー）を一時的に使う
   - もっとも簡単なのは、最初の1回だけ手動でPythonスクリプトを実行し、
     Webhook受信用の小さなテストコードでuserIdをコンソールに出力させて確認する方法です。
     必要であれば、その確認用スクリプトも作成します。

### ステップ5: GitHubにシークレットを登録

リポジトリの `Settings` → `Secrets and variables` → `Actions` → `New repository secret` で以下を登録:

| Name | Value |
|---|---|
| `ALPHA_VANTAGE_API_KEY` | Alpha VantageのAPIキー |
| `LINE_CHANNEL_ACCESS_TOKEN` | ステップ3で発行したチャネルアクセストークン |
| `LINE_USER_ID` | ステップ4で取得した自分のユーザーID |

### ステップ6: 動作確認

1. リポジトリの「Actions」タブを開く
2. 左メニューから「AGIX Daily Signal Check」を選択
3. 右側の「Run workflow」ボタンで手動実行
4. 数十秒後、LINEに通知が届けば成功です

成功すれば、以降は平日の米国市場オープン後（日本時間 夏時間23:35頃 / 冬時間0:35頃）に自動実行されます。

---

## 実行スケジュールについて

`.github/workflows/daily_signal.yml` 内のcron式 `35 14 * * 1-5` はUTC基準で固定しています。
米国の夏時間/冬時間切り替えにより、実際の現地時間ベースでのタイミングが1時間前後する点はご了承ください。
気になる場合は、半年ごとに以下のように手動で変更してください:

- 夏時間 (3月〜11月頃): `cron: "35 14 * * 1-5"` (ET 10:35頃)
- 冬時間 (11月〜3月頃): `cron: "35 15 * * 1-5"` (ET 10:35頃)

## 既知の制約

- AGIXは2024年7月上場の新しいETFのため、Alpha Vantageの`OVERVIEW`エンドポイントで
  PER等の一部ファンダメンタルズ項目が欠落する場合があります。欠落時は自動的にその項目を
  スコア計算から除外します。
- 非公開企業（Anthropic, xAI, SpaceXなど）への投資部分の財務情報はAPIでは取得できません。
- 本ツールは情報提供のみを目的としており、投資助言ではありません。投資判断は自己責任で行ってください。
