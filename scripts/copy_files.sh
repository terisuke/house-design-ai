set -e

mkdir -p /app/config /app/house_design_app /app/.streamlit /app/src

touch /app/config/service_account.json
touch /app/house_design_app/logo.png
touch /app/.streamlit/secrets.toml

if [ -f "/tmp/build/config/service_account.json" ]; then
  cp /tmp/build/config/service_account.json /app/config/service_account.json
  cp /tmp/build/config/service_account.json /app/.streamlit/secrets.toml
  echo "サービスアカウントキーをコピーしました"
fi

if [ -f "/tmp/build/config/data.yaml" ]; then
  cp /tmp/build/config/data.yaml /app/config/data.yaml
fi

if [ -f "/tmp/build/public/img/logo.png" ]; then
  cp /tmp/build/public/img/logo.png /app/house_design_app/logo.png
  echo "ロゴファイルをコピーしました"
fi

if [ -d "/tmp/build/src" ]; then
  cp -r /tmp/build/src/* /app/src/
fi

echo "File setup completed successfully"
