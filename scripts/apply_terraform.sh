#!/bin/bash
set -e

# 環境変数の設定
ENVIRONMENT="dev"
TERRAFORM_DIR="terraform/environments/${ENVIRONMENT}"

# 現在のディレクトリを保存
CURRENT_DIR=$(pwd)

# Terraformディレクトリに移動
cd ${TERRAFORM_DIR}

# Terraformの初期化
echo "Terraformを初期化します..."
terraform init

# Terraformのプラン
echo "Terraformのプランを表示します..."
terraform plan

# 確認
read -p "Terraformを適用しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    # Terraformの適用
    echo "Terraformを適用します..."
    terraform apply -auto-approve
    
    echo "Terraformの適用が完了しました。"
else
    echo "Terraformの適用を中止しました。"
fi

# 元のディレクトリに戻る
cd ${CURRENT_DIR} 