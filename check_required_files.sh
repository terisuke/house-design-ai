set -e

REQUIRED_FILES=(
  "config/service_account.json"
  "public/img/logo.png"
)

for file in "${REQUIRED_FILES[@]}"; do
  if [ ! -f "$file" ]; then
    echo "エラー: 必須ファイル '$file' が見つかりません。"
    echo "このファイルはDockerイメージのビルドに必要です。"
    echo "ファイルを正しい場所に配置してから再度ビルドしてください。"
    exit 1
  else
    echo "必須ファイル '$file' が見つかりました。"
  fi
done

if [ -f "config/service_account.json" ]; then
  file_size=$(wc -c < "config/service_account.json" | tr -d ' ')
  if [ "$file_size" -lt 50 ]; then
    echo "エラー: サービスアカウントファイル 'config/service_account.json' が小さすぎます（${file_size}バイト）。"
    echo "有効なサービスアカウントJSONファイルではない可能性があります。"
    exit 1
  fi
  
  if ! grep -q "client_email" "config/service_account.json" || ! grep -q "private_key" "config/service_account.json"; then
    echo "エラー: サービスアカウントファイル 'config/service_account.json' に必要なフィールドが含まれていません。"
    echo "有効なサービスアカウントJSONファイルを使用してください。"
    exit 1
  fi
fi

echo "すべての必須ファイルが正常に検出されました。ビルドを続行します。"
