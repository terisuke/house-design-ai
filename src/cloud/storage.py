"""
Google Cloud Storage との連携モジュール。
データセット、モデル、結果の管理に関する機能を提供します。
"""
import os
import tempfile
import logging
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import glob

# ロギング設定
logger = logging.getLogger(__name__)


def initialize_gcs_client():
    """
    Google Cloud Storage クライアントを初期化します。
    
    Returns:
        初期化されたStorageClientオブジェクト、失敗時はNone
    """
    try:
        from google.cloud import storage
        
        # Streamlit環境で実行されているか確認
        is_streamlit = False
        try:
            import streamlit as st
            is_streamlit = True
        except ImportError:
            pass
        
        # 認証方法の優先順位:
        # 1. Streamlit secretsの使用（Streamlit環境の場合）
        # 2. 指定されたサービスアカウントファイル
        # 3. 環境変数 GOOGLE_APPLICATION_CREDENTIALS
        # 4. デフォルトの認証
        
        # 1. Streamlit secretsが利用可能かチェック
        if is_streamlit:
            try:
                from google.oauth2 import service_account
                
                # st.secretsからGCP認証情報を読み込む
                if "gcp_service_account" in st.secrets:
                    logger.info("Streamlit secretsからGCP認証情報を使用します")
                    credentials = service_account.Credentials.from_service_account_info(
                        st.secrets["gcp_service_account"]
                    )
                    client = storage.Client(credentials=credentials)
                    return client
            except Exception as e:
                logger.warning(f"Streamlit secretsからの認証に失敗しました: {e}")
                # 他の認証方法にフォールバック
        
        # 2. 指定されたサービスアカウントファイルを使用
        service_account_path = os.path.join("config", "service_account.json")
        
        if os.path.exists(service_account_path):
            # 指定されたパスのサービスアカウントキーを使用
            client = storage.Client.from_service_account_json(service_account_path)
            logger.info(f"サービスアカウントファイルからGCSクライアントを初期化: {service_account_path}")
            return client
        else:
            # デフォルト認証を使用
            try:
                client = storage.Client()
                logger.info("デフォルト認証でGCSクライアントを初期化")
                return client
            except Exception as e:
                logger.error(f"デフォルト認証でのGCS初期化エラー: {e}")
                return None
                
    except ImportError:
        logger.error("google-cloud-storageがインストールされていません")
        return None
    except Exception as e:
        logger.error(f"GCSクライアント初期化エラー: {e}")
        return None


def download_model_from_gcs(bucket_name: str, blob_name: str) -> Optional[str]:
    """
    Google Cloud Storage からモデルファイルをダウンロードします。
    
    Args:
        bucket_name: GCSバケット名
        blob_name: モデルファイルのパス
        
    Returns:
        ダウンロードされたモデルのローカルパス、失敗時はNone
    """
    try:
        client = initialize_gcs_client()
        if not client:
            logger.error("GCSクライアントの初期化に失敗しました")
            return None
        
        # バケットとBlobの取得
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # 一時ファイルにダウンロード
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
            logger.info(f"モデルをダウンロード中: gs://{bucket_name}/{blob_name} → {tmp.name}")
            blob.download_to_filename(tmp.name)
            return tmp.name
            
    except Exception as e:
        logger.error(f"モデルダウンロードエラー: {e}")
        return None


def download_dataset(
    bucket_name: str,
    source_prefix: str,
    destination_dir: str,
    exclude_patterns: List[str] = ['.DS_Store', 'labels.cache']
) -> bool:
    """
    Google Cloud Storage からデータセットをダウンロードし、ディレクトリ構造を維持します。
    
    Args:
        bucket_name: GCSバケット名
        source_prefix: GCS内のデータセットのプレフィックス（パス）
        destination_dir: ダウンロード先のローカルディレクトリ
        exclude_patterns: 除外するファイルパターンのリスト
        
    Returns:
        ダウンロード成功時はTrue、失敗時はFalse
    """
    try:
        client = initialize_gcs_client()
        if not client:
            logger.error("GCSクライアントの初期化に失敗しました")
            return False
        
        # バケットの取得
        bucket = client.bucket(bucket_name)
        
        # プレフィックスの正規化
        if not source_prefix.endswith('/'):
            source_prefix += '/'
        
        # Blobのリストを取得し、除外パターンに一致するものを除外
        blobs = list(bucket.list_blobs(prefix=source_prefix))
        filtered_blobs = []
        
        for blob in blobs:
            should_exclude = False
            for pattern in exclude_patterns:
                if pattern in blob.name:
                    should_exclude = True
                    break
            
            if not should_exclude and not blob.name.endswith('/'):
                filtered_blobs.append(blob)
        
        if not filtered_blobs:
            logger.warning(f"ダウンロード対象のファイルが見つかりません: gs://{bucket_name}/{source_prefix}")
            return False
        
        # 保存先ディレクトリの作成
        os.makedirs(destination_dir, exist_ok=True)
        
        # ファイルのダウンロード
        for blob in filtered_blobs:
            # 相対パスの計算
            relative_path = blob.name.replace(source_prefix, '', 1)
            destination_file = os.path.join(destination_dir, relative_path)
            
            # 必要なサブディレクトリの作成
            os.makedirs(os.path.dirname(destination_file), exist_ok=True)
            
            # ファイルのダウンロード
            logger.info(f"ダウンロード中: {blob.name} → {destination_file}")
            blob.download_to_filename(destination_file)
        
        logger.info(f"データセットのダウンロードが完了しました: {len(filtered_blobs)}ファイル")
        return True
        
    except Exception as e:
        logger.error(f"データセットダウンロードエラー: {e}")
        return False


def upload_to_gcs(
    bucket_name: str,
    source_path: str,
    destination_blob_name: str
) -> bool:
    """
    ファイルをGoogle Cloud Storageにアップロードします。
    
    Args:
        bucket_name: GCSバケット名
        source_path: アップロードするローカルファイルのパス
        destination_blob_name: GCS内での保存先パス
        
    Returns:
        アップロード成功時はTrue、失敗時はFalse
    """
    try:
        client = initialize_gcs_client()
        if not client:
            logger.error("GCSクライアントの初期化に失敗しました")
            return False
        
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        # ファイルのアップロード
        logger.info(f"アップロード中: {source_path} → gs://{bucket_name}/{destination_blob_name}")
        blob.upload_from_filename(source_path)
        logger.info(f"アップロード完了: gs://{bucket_name}/{destination_blob_name}")
        return True
        
    except Exception as e:
        logger.error(f"アップロードエラー: {e}")
        return False


def upload_directory_to_gcs(
    bucket_name: str,
    source_directory: str,
    destination_prefix: str,
    recursive: bool = True
) -> Dict[str, int]:
    """
    ディレクトリ全体をGoogle Cloud Storageにアップロードします。
    
    Args:
        bucket_name: GCSバケット名
        source_directory: アップロードするローカルディレクトリのパス
        destination_prefix: GCS内での保存先プレフィックス
        recursive: サブディレクトリも含めてアップロードするかどうか
        
    Returns:
        アップロード結果を示す辞書 {'success': 成功数, 'error': 失敗数}
    """
    try:
        client = initialize_gcs_client()
        if not client:
            logger.error("GCSクライアントの初期化に失敗しました")
            return {"success": 0, "error": 0}
        
        bucket = client.bucket(bucket_name)
        
        # アップロード先プレフィックスの正規化
        if not destination_prefix.endswith('/'):
            destination_prefix += '/'
        
        # ファイルのリストを取得
        pattern = os.path.join(source_directory, '**' if recursive else '*')
        file_paths = [f for f in glob.glob(pattern, recursive=recursive) if os.path.isfile(f)]
        
        if not file_paths:
            logger.warning(f"アップロード対象のファイルが見つかりません: {source_directory}")
            return {"success": 0, "error": 0}
        
        # カウンター初期化
        success_count = 0
        error_count = 0
        
        # ファイルのアップロード
        for file_path in file_paths:
            try:
                # GCS内での相対パスを計算
                relative_path = os.path.relpath(file_path, source_directory)
                blob_name = os.path.join(destination_prefix, relative_path)
                
                # Windows環境でのパスセパレータをGCSに適したものに変換
                blob_name = blob_name.replace('\\', '/')
                
                # ファイルのアップロード
                blob = bucket.blob(blob_name)
                logger.info(f"アップロード中: {file_path} → gs://{bucket_name}/{blob_name}")
                blob.upload_from_filename(file_path)
                success_count += 1
                
            except Exception as e:
                logger.error(f"ファイルのアップロードに失敗しました: {file_path} - {e}")
                error_count += 1
        
        logger.info(f"ディレクトリのアップロードが完了しました: 成功={success_count}, 失敗={error_count}")
        return {"success": success_count, "error": error_count}
        
    except Exception as e:
        logger.error(f"ディレクトリアップロードエラー: {e}")
        return {"success": 0, "error": 1}