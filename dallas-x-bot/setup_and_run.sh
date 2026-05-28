#!/bin/bash
# One-shot setup + run script for dallas-x-bot.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/yukihikocom-commits/dallasnewsxautomation/claude/serene-mccarthy-J8euK/dallas-x-bot/setup_and_run.sh | bash
# Or after cloning:
#   bash setup_and_run.sh

set -e

REPO_URL="https://github.com/yukihikocom-commits/dallasnewsxautomation.git"
BRANCH="claude/serene-mccarthy-J8euK"
INSTALL_DIR="$HOME/dallasnewsxautomation"

echo "==> dallas-x-bot セットアップ開始"

# 1. Clone or update repo
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "==> 既存のリポジトリを更新中..."
    cd "$INSTALL_DIR"
    git fetch origin "$BRANCH"
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    echo "==> リポジトリをクローン中: $INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    git checkout "$BRANCH"
fi

cd "$INSTALL_DIR/dallas-x-bot"

# 2. Install dependencies
echo "==> Python依存関係をインストール中..."
pip3 install -q -r requirements.txt

# 3. Setup .env
if [ ! -f .env ]; then
    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "==> 環境変数 ANTHROPIC_API_KEY を .env に書き込み中..."
        echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" > .env
    else
        echo ""
        echo "⚠️  ANTHROPIC_API_KEY が設定されていません"
        echo "    以下のいずれかで設定してください:"
        echo "    A) 環境変数: export ANTHROPIC_API_KEY=sk-..."
        echo "       (~/.zshrc に追記すると永続化されます)"
        echo "    B) .envファイル: $INSTALL_DIR/dallas-x-bot/.env に書き込み"
        echo "       例: echo 'ANTHROPIC_API_KEY=sk-...' > .env"
        echo ""
        read -p "今ここでAPIキーを入力する場合は貼り付けてEnter (skipなら空のままEnter): " API_KEY
        if [ -n "$API_KEY" ]; then
            echo "ANTHROPIC_API_KEY=$API_KEY" > .env
            echo "==> .env を作成しました"
        else
            echo "==> APIキー未設定のため終了します"
            exit 1
        fi
    fi
fi

# 4. Run the bot
echo "==> 本日のニュース投稿を生成中..."
python3 run_today.py

echo ""
echo "==> 完了。Finderで output/ フォルダが開きます。"
