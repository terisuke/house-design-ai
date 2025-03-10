#!/usr/bin/env python3
"""
YOLOモデルファイルをGCSバケットにアップロードするスクリプト
このスクリプトは、ultralyticsのYOLOモデルをダウンロードし、指定したGCSバケットにアップロードします。
"""
import argparse
import logging
import os
import sys
from pathlib import Path
import tempfile
import urllib.request
from google.cloud import storage

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent  # scripts ディレクトリの1つ上
sys.path.insert(0, str(project_root))

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("upload-model")

def download_yolo_model(model_name: str, output_path: str) -> bool:
    """
    ultralyticsのYOLOモデルをダウンロードします。
    
    Args:
        model_name: モデル名（例：yolo11m-seg.pt）
        output_path: 出力ファイルパス
        
    Returns:
        ダウンロード成功時はTrue、失敗時はFalse
    """
    try:
        # モデルのURLを構築
        model_url = f"https://github.com/ultralytics/assets/releases/download/v8.3.0/{model_name}"
        logger.info(f"モデルをダウンロード中: {model_url} -> {output_path}")
        
        # ディレクトリが存在することを確認
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # モデルをダウンロード
        urllib.request.urlretrieve(model_url, output_path)
        
        # ダウンロードの確認
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)  # MBに変換
            logger.info(f"モデルのダウンロードが完了しました: {output_path} ({file_size:.2f}MB)")
            return True
        else:
            logger.error(f"モデルのダウンロードに失敗しました")
            return False
    except Exception as e:
        logger.error(f"モデルのダウンロード中にエラーが発生しました: {e}")
        return False

def upload_to_gcs(source_file: str, bucket_name: str, destination_blob_name: str) -> bool:
    """
    ファイルをGCSバケットにアップロードします。
    
    Args:
        source_file: アップロードするローカルファイルのパス
        bucket_name: GCSバケット名
        destination_blob_name: アップロード先のGCS内でのパス
        
    Returns:
        アップロード成功時はTrue、失敗時はFalse
    """
    try:
        # GCS クライアントを初期化
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        # ファイルをアップロード
        logger.info(f"ファイルをアップロード中: {source_file} -> gs://{bucket_name}/{destination_blob_name}")
        blob.upload_from_filename(source_file)
        
        logger.info(f"ファイルが正常にアップロードされました")
        return True
    except Exception as e:
        logger.error(f"ファイルのアップロード中にエラーが発生しました: {e}")
        return False

def main():
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="YOLOモデルをGCSバケットにアップロードします")
    parser.add_argument("--model", type=str, default="yolo11m-seg.pt",
                       help="アップロードするYOLOモデル名")
    parser.add_argument("--bucket", type=str, required=True,
                       help="アップロード先のGCSバケット名")
    parser.add_argument("--prefix", type=str, default="models",
                       help="GCSバケット内のプレフィックス（デフォルト: models）")
    args = parser.parse_args()
    
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        # モデルファイルのパスを設定
        model_path = os.path.join(temp_dir, args.model)
        
        # モデルをダウンロード
        if not download_yolo_model(args.model, model_path):
            logger.error("モデルのダウンロードに失敗しました。終了します。")
            return 1
        
        # GCSバケットにアップロード
        destination_blob_name = f"{args.prefix}/{args.model}"
        if not upload_to_gcs(model_path, args.bucket, destination_blob_name):
            logger.error("モデルのアップロードに失敗しました。終了します。")
            return 1
        
        logger.info(f"モデル {args.model} が正常にアップロードされました: gs://{args.bucket}/{destination_blob_name}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 