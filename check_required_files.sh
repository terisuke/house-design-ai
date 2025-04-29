set -e

IS_CLOUD_BUILD=${IS_CLOUD_BUILD:-"false"}

REQUIRED_FILES=(
  "config/service_account.json"
  "public/img/logo.png"
)

if [ "$IS_CLOUD_BUILD" = "true" ]; then
  echo "Cloud Build環境で実行されています。ファイル検証をスキップします。"
  echo "デプロイ後にCloud Runのデフォルト認証を使用します。"
  exit 0
fi

for file in "${REQUIRED_FILES[@]}"; do
  if [ ! -f "$file" ]; then
    echo "警告: ファイル '$file' が見つかりません。"
    echo "ローカル環境では必要ですが、Cloud Runデプロイではデフォルト認証にフォールバックします。"
  else
    echo "必須ファイル '$file' が見つかりました。"
  fi
done

if [ -f "config/service_account.json" ]; then
  file_size=$(wc -c < "config/service_account.json" | tr -d ' ')
  if [ "$file_size" -lt 50 ]; then
    echo "警告: サービスアカウントファイル 'config/service_account.json' が小さすぎます（${file_size}バイト）。"
    echo "有効なサービスアカウントJSONファイルではない可能性があります。"
  fi
  
  if ! grep -q "client_email" "config/service_account.json" || ! grep -q "private_key" "config/service_account.json"; then
    echo "警告: サービスアカウントファイル 'config/service_account.json' に必要なフィールドが含まれていません。"
    echo "有効なサービスアカウントJSONファイルを使用してください。"
  fi
fi

echo "ファイル検証が完了しました。ビルドを続行します。"
