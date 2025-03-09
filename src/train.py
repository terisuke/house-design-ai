"""
YOLOv8セグメンテーションモデルのトレーニングモジュール。
ローカル環境でのトレーニングを担当します。
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
import argparse
from google.cloud import storage
import tempfile
import subprocess
import shutil

# ロギング設定
logger = logging.getLogger(__name__)


def download_dataset_from_gcs(
    gcs_bucket_name: str,
    gcs_prefix: str,
    local_dir: str,
) -> bool:
    """
    GCSからデータセットをダウンロードします。
    
    Args:
        gcs_bucket_name: GCSバケット名
        gcs_prefix: GCS内のプレフィックス（datasets/house/等）
        local_dir: データセットを保存するローカルディレクトリ
        
    Returns:
        ダウンロード成功時はTrue、失敗時はFalse
    """
    try:
        # ローカルディレクトリが存在することを確認
        os.makedirs(local_dir, exist_ok=True)
        
        # gsutilを使用してデータをダウンロード（再帰的に）
        logger.info(f"GCSからデータセットをダウンロード: gs://{gcs_bucket_name}/{gcs_prefix} -> {local_dir}")
        
        # 方法1: gsutilコマンドを使用（より高速で信頼性が高い）
        gsutil_success = False
        try:
            # gsutilが存在するか確認
            check_gsutil = subprocess.run("which gsutil", shell=True, capture_output=True, text=True)
            if check_gsutil.returncode == 0:
                logger.info(f"gsutilパス: {check_gsutil.stdout.strip()}")
                gsutil_cmd = f"gsutil -m cp -r gs://{gcs_bucket_name}/{gcs_prefix}/* {local_dir}"
                logger.info(f"実行コマンド: {gsutil_cmd}")
                subprocess.run(gsutil_cmd, shell=True, check=True)
                logger.info(f"gsutilによるダウンロード完了")
                gsutil_success = True
            else:
                logger.warning(f"gsutilコマンドが見つかりません。Python APIを使用します。")
        except subprocess.CalledProcessError as e:
            logger.warning(f"gsutilコマンドが失敗しました: {e}. Python APIを使用して再試行します。")
        
        # gsutilが失敗した場合のみPython APIを使用
        if not gsutil_success:
            logger.info("Python APIを使用してGCSからデータをダウンロードします")
            # 方法2: Python APIを使用（バックアップ方法）
            client = storage.Client()
            bucket = client.bucket(gcs_bucket_name)
            
            # ダウンロード対象を指定
            target_prefix = f"{gcs_prefix}/"
            blobs = list(bucket.list_blobs(prefix=target_prefix))
            
            if not blobs:
                logger.warning(f"指定されたパスにファイルが見つかりません: gs://{gcs_bucket_name}/{target_prefix}")
                # ディレクトリ構造を確認
                all_blobs = list(bucket.list_blobs(prefix=gcs_prefix.split('/')[0]))
                logger.info(f"バケット内のファイル一覧 (最初の10件): {[b.name for b in all_blobs[:10]]}")
                return False
            
            logger.info(f"ダウンロード対象ファイル数: {len(blobs)}")
            
            download_count = 0
            for blob in blobs:
                # プレフィックス自体はディレクトリではないためスキップ
                if blob.name == target_prefix:
                    continue
                    
                # ローカルファイルパスの作成
                relative_path = blob.name[len(target_prefix):]
                if not relative_path:  # 空文字列の場合はスキップ
                    continue
                    
                local_file_path = os.path.join(local_dir, relative_path)
                
                # 必要なディレクトリを作成
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                
                # ファイルのダウンロード
                blob.download_to_filename(local_file_path)
                download_count += 1
                
                # 進捗表示（たくさんのファイルがある場合）
                if download_count % 10 == 0:
                    logger.info(f"{download_count}ファイルをダウンロードしました")
            
            if download_count == 0:
                logger.warning(f"ダウンロードされたファイルはありません: gs://{gcs_bucket_name}/{target_prefix}")
                return False
                
            logger.info(f"合計{download_count}ファイルをダウンロードしました: gs://{gcs_bucket_name}/{target_prefix} -> {local_dir}")
        
        # ダウンロードが完了したらファイル一覧を表示
        try:
            local_files = os.listdir(local_dir)
            logger.info(f"ダウンロードしたディレクトリの内容: {local_dir}")
            logger.info(f"ファイル数: {len(local_files)}")
            logger.info(f"ファイル一覧 (最初の10件): {local_files[:10] if len(local_files) > 10 else local_files}")
        except Exception as e:
            logger.warning(f"ローカルディレクトリの確認中にエラー: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"データセットダウンロードエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def update_data_yaml(
    yaml_path: str,
    train_dir: str,
    val_dir: str
) -> bool:
    """
    data.yamlファイルを更新してトレーニング・検証データのパスを設定します。
    GCSパスとローカルパスの両方に対応します。
    
    Args:
        yaml_path: data.yamlファイルのパス
        train_dir: トレーニングデータディレクトリのパス
        val_dir: 検証データディレクトリのパス
        
    Returns:
        更新成功時はTrue、失敗時はFalse
    """
    try:
        # GCSパスかローカルパスかを判断
        if yaml_path.startswith("gs://"):
            # GCSパスの場合
            logger.info(f"GCSパスが検出されました: {yaml_path}")
            
            # GCSパスを分解
            bucket_name = yaml_path.split("/")[2]
            blob_path = "/".join(yaml_path.split("/")[3:])
            
            # 一時ファイルを作成
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as temp_file:
                temp_path = temp_file.name
                logger.info(f"一時ファイルを作成しました: {temp_path}")
                
                # GCSクライアントを初期化
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                blob = bucket.blob(blob_path)
                
                # 既存のYAMLをダウンロード (存在する場合)
                if blob.exists():
                    blob_content = blob.download_as_string()
                    with open(temp_path, 'wb') as f:
                        f.write(blob_content)
                    
                    # YAMLをロード
                    with open(temp_path, 'r') as f:
                        data_config = yaml.safe_load(f)
                else:
                    # 新規作成
                    data_config = {}
                
                # データパスを更新
                data_config['train'] = train_dir
                data_config['val'] = val_dir
                
                # 明示的にラベルディレクトリも設定
                if train_dir.endswith('/images'):
                    train_labels = train_dir.replace('/images', '/labels')
                    data_config['train_labels'] = train_labels
                
                if val_dir.endswith('/images'):
                    val_labels = val_dir.replace('/images', '/labels')
                    data_config['val_labels'] = val_labels
                
                # クラス情報があることを確認
                if 'nc' not in data_config:
                    data_config['nc'] = 5  # デフォルト値
                
                if 'names' not in data_config:
                    data_config['names'] = ['Direction', 'Direction2', 'House', 'Road', 'Space']
                
                # 更新したYAMLを一時ファイルに書き込み
                with open(temp_path, 'w') as f:
                    yaml.dump(data_config, f)
                
                # 一時ファイルをGCSにアップロード
                with open(temp_path, 'rb') as f:
                    blob.upload_from_file(f)
                
                logger.info(f"data.yamlを更新してGCSにアップロードしました: {yaml_path}")
                
                # 一時ファイルを削除
                os.unlink(temp_path)
                
            return True
        else:
            # ローカルパスの場合は従来の処理
            # YAMLファイルを読み込み
            try:
                with open(yaml_path, 'r') as f:
                    data_config = yaml.safe_load(f)
            except FileNotFoundError:
                # ファイルが存在しない場合は新規作成
                data_config = {}
            
            # データパスを更新
            data_config['train'] = train_dir
            data_config['val'] = val_dir
            
            # 明示的にラベルディレクトリも設定
            if train_dir.endswith('/images'):
                train_labels = train_dir.replace('/images', '/labels')
                data_config['train_labels'] = train_labels
            
            if val_dir.endswith('/images'):
                val_labels = val_dir.replace('/images', '/labels')
                data_config['val_labels'] = val_labels
            
            # クラス情報があることを確認
            if 'nc' not in data_config:
                data_config['nc'] = 5  # デフォルト値
            
            if 'names' not in data_config:
                data_config['names'] = ['Direction', 'Direction2', 'House', 'Road', 'Space']
            
            # 更新したYAMLを書き込み
            with open(yaml_path, 'w') as f:
                yaml.dump(data_config, f)
            
            logger.info(f"data.yamlを更新しました: train={train_dir}, val={val_dir}")
            return True
        
    except Exception as e:
        logger.error(f"data.yaml更新エラー: {e}")
        return False


def train_model(args: argparse.Namespace) -> int:
    """
    YOLOv8セグメンテーションモデルをトレーニングします。
    
    Args:
        args: コマンドライン引数
        
    Returns:
        成功時は0、失敗時は1
    """
    try:
        # 環境変数とGCP認証情報を確認
        logger.info("環境変数とGCP認証情報を確認")
        cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        logger.info(f"GOOGLE_APPLICATION_CREDENTIALS: {cred_path}")
        if cred_path and os.path.exists(cred_path):
            logger.info(f"認証情報ファイルが存在します: {cred_path}")
        else:
            logger.warning(f"認証情報ファイルが存在しないか、環境変数が設定されていません")
        
        # GCSからデータセットをダウンロード
        if hasattr(args, 'bucket_name') and args.bucket_name:
            logger.info(f"GCSからデータセットをダウンロードします: {args.bucket_name}")
            
            # トレーニングデータのダウンロード
            if not download_dataset_from_gcs(
                gcs_bucket_name=args.bucket_name,
                gcs_prefix="datasets/house/train",
                local_dir="/app/datasets/house/train"
            ):
                logger.error("トレーニングデータのダウンロードに失敗しました")
                return 1
                
            # 検証データのダウンロード
            if not download_dataset_from_gcs(
                gcs_bucket_name=args.bucket_name,
                gcs_prefix="datasets/house/val",
                local_dir="/app/datasets/house/val"
            ):
                logger.error("検証データのダウンロードに失敗しました")
                return 1
                
            logger.info("GCSからのデータセットダウンロードが完了しました")
        
        # データ設定ファイルの更新
        if not update_data_yaml(args.data_yaml, args.train_dir, args.val_dir):
            logger.error("data.yamlの更新に失敗しました")
            return 1
        
        # モデルのインポート
        try:
            from ultralytics import YOLO
        except ImportError:
            logger.error("ultralyticsパッケージがインストールされていません")
            return 1
        
        # モデルのロード
        logger.info(f"モデルをロード中: {args.model}")
        model = YOLO(args.model)
        
        # トレーニングパラメータの設定
        train_params = {
            'data': args.data_yaml,
            'epochs': args.epochs,
            'batch': args.batch_size,
            'imgsz': args.imgsz,
            'exist_ok': True,  # 既存のトレーニング結果を上書き
        }
        
        # トレーニングの実行
        logger.info(f"トレーニングを開始: {args.epochs}エポック, バッチサイズ={args.batch_size}")
        results = model.train(**train_params)
        
        # トレーニング結果のロギング
        best_fitness = results.fitness
        logger.info(f"トレーニング完了: best fitness={best_fitness}")
        
        # 最良のモデルのパスを表示
        best_model_path = os.path.join(model.trainer.save_dir, "weights", "best.pt")
        if os.path.exists(best_model_path):
            logger.info(f"最良のモデルを保存: {best_model_path}")
            print(f"トレーニングが完了しました。最良のモデル: {best_model_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"トレーニングエラー: {e}", exc_info=True)
        return 1


# コマンドライン実行用
if __name__ == "__main__":
    # 引数パーサーの設定
    parser = argparse.ArgumentParser(description="YOLOv8セグメンテーションモデルのトレーニング")
    
    parser.add_argument("--model", type=str, default="yolov8m-seg.pt",
                      help="ベースYOLOv8モデル")
    parser.add_argument("--epochs", type=int, default=100,
                      help="トレーニングエポック数")
    parser.add_argument("--batch_size", type=int, default=16,
                      help="バッチサイズ")
    parser.add_argument("--imgsz", type=int, default=640,
                      help="入力画像サイズ")
    parser.add_argument("--data_yaml", type=str, default="config/data.yaml",
                      help="data.yamlファイルのパス")
    parser.add_argument("--train_dir", type=str, default="datasets/house/train",
                      help="トレーニングデータディレクトリのパス")
    parser.add_argument("--val_dir", type=str, default="datasets/house/val",
                      help="検証データディレクトリのパス")
    
    args = parser.parse_args()
    
    # トレーニングの実行
    exit_code = train_model(args)
    import sys
    sys.exit(exit_code)