import os
import yaml
import logging
from pathlib import Path
import argparse
from google.cloud import storage
import tempfile
import subprocess
import shutil # 追加
from typing import List
# ロギング設定
logger = logging.getLogger(__name__)

def download_dataset_from_gcs(
    gcs_bucket_name: str,
    gcs_prefix: str,
    local_dir: str,
    exclude_patterns: List[str] = ['.DS_Store', 'labels.cache']
) -> bool:
    """
    GCSからデータセットをダウンロードします。
    
    Args:
        gcs_bucket_name: GCSバケット名
        gcs_prefix: GCS内のプレフィックス（house/等）
        local_dir: データセットを保存するローカルディレクトリ
        exclude_patterns: 除外するファイルパターンのリスト
        
    Returns:
        ダウンロード成功時はTrue、失敗時はFalse
    """
    try:
        # ローカルディレクトリが存在することを確認(無ければ作成)
        os.makedirs(local_dir, exist_ok=True)
        
        # Python APIのみを使用する
        logger.info(f"GCSからデータセットをダウンロード: gs://{gcs_bucket_name}/{gcs_prefix} -> {local_dir}")
        logger.info("[INFO] Python API (google-cloud-storage) を使用してデータセットをダウンロードします。")
        from src.cloud.storage import download_dataset
        if not download_dataset(
            bucket_name=gcs_bucket_name,
            source_prefix=gcs_prefix,
            destination_dir=local_dir,
            exclude_patterns=exclude_patterns
        ):
            logger.error("Python APIによるデータセットダウンロードに失敗しました。")
            return False
        else:
            logger.info("Python APIを使用したダウンロードが成功しました。")

        # ダウンロードが完了したらファイル一覧を表示
        try:
            local_files = os.listdir(local_dir)
            logger.info(f"ダウンロードしたディレクトリの内容: {local_dir}")
            logger.info(f"ファイル数: {len(local_files)}")
            logger.info(f"ファイル一覧 (最初の10件): {local_files[:10] if len(local_files) > 10 else local_files}")
        except Exception as e:
            logger.warning(f"ローカルディレクトリの確認中にエラー: {e}")
        
        return True  # Python APIが成功した場合は True
        
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
    ローカルパスのみに対応。GCSへのアップロードは行いません。

    Args:
        yaml_path: data.yamlファイルのパス
        train_dir: トレーニングデータディレクトリのパス(/app/house/train)
        val_dir: 検証データディレクトリのパス(/app/house/val)

    Returns:
        更新成功時はTrue、失敗時はFalse
    """
    try:
       # data.yamlをロード
        with open(yaml_path, 'r') as f:
            data_config = yaml.safe_load(f)

        # データパスを更新 (images, labels サブディレクトリを直接指定)
        data_config['train'] = train_dir
        data_config['val'] = val_dir
        

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
    YOLOセグメンテーションモデルをトレーニングします。
    
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
            train_dir = "/app/house/train"
            # train_dir が存在し、空でない場合は削除 (Vertex AI 環境を想定)
            if os.path.exists(train_dir) and os.listdir(train_dir):
                logger.warning(f"{train_dir} は空ではありません。削除します。")
                shutil.rmtree(train_dir)  # shutil を使用して再帰的に削除
            
            if not download_dataset_from_gcs(
                gcs_bucket_name=args.bucket_name,
                gcs_prefix="house/train",  # GCS上のtrainディレクトリ
                local_dir=train_dir  # ローカルのtrainディレクトリ
            ):
                logger.error("トレーニングデータのダウンロードに失敗しました")
                return 1
                
            # 検証データのダウンロード
            val_dir = "/app/house/val"
            # val_dir が存在し、空でない場合は削除
            if os.path.exists(val_dir) and os.listdir(val_dir):
                logger.warning(f"{val_dir} は空ではありません。削除します。")
                shutil.rmtree(val_dir)
            
            if not download_dataset_from_gcs(
                gcs_bucket_name=args.bucket_name,
                gcs_prefix="house/val",  # GCS上のvalディレクトリ
                local_dir=val_dir  # ローカルのvalディレクトリ
            ):
                logger.error("検証データのダウンロードに失敗しました")
                return 1
                
            logger.info("GCSからのデータセットダウンロードが完了しました")
        
        # data.yamlのパス
        data_yaml_path = "/app/config/data.yaml"
        
        # データ設定ファイルの更新
        if not update_data_yaml(data_yaml_path, '/app/house/train/images', '/app/house/val/images'):
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
            'data': data_yaml_path,
            'epochs': args.epochs,
            'batch': args.batch_size,
            'imgsz': args.imgsz,
            'optimizer': args.optimizer,
            'lr0': args.lr0,
            'iou': args.iou_threshold,
            'conf': args.conf_threshold,
            'rect':args.rect,
            'cos_lr':args.cos_lr,
            'mosaic':args.mosaic,
            'degrees':args.degrees,
            'scale':args.scale,
            'single_cls': getattr(args, 'single_cls', False),
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
            print(f"トレーニングが完了しました。最良のモデル: {best_model_path}")  # 標準出力にも表示
        
        # upload_modelは削除。save_dirをアップロードする。
        # Upload the entire save_dir to Cloud Storage
        if args.upload_bucket:
            from src.cloud.storage import upload_directory_to_gcs as upload_directory # 依存関係の問題を避けるため、ここでのみインポートする
            upload_directory(
                args.upload_bucket,
                str(model.trainer.save_dir),  # ローカルの保存先ディレクトリ
                str(Path(args.save_dir).relative_to('/app')) # GCS上のパス（/appからの相対パス）
            )
        return 0
        
    except Exception as e:
        logger.error(f"トレーニングエラー: {e}", exc_info=True)
        return 1


# コマンドライン実行用
if __name__ == "__main__":
    # 引数パーサーの設定
    parser = argparse.ArgumentParser(description="YOLOv8セグメンテーションモデルのトレーニング")
    
    parser.add_argument("--model", type=str, default="yolo11l-seg.pt",
                      help="ベースYOLOv8モデル")
    parser.add_argument("--epochs", type=int, default=100,
                      help="トレーニングエポック数")
    parser.add_argument("--batch_size", type=int, default=16,
                      help="バッチサイズ")
    parser.add_argument("--imgsz", type=int, default=640,
                      help="入力画像サイズ")
    parser.add_argument("--data_yaml", type=str, default="config/data.yaml",
                      help="data.yamlファイルのパス")
    parser.add_argument("--train_dir", type=str, default="house/train",
                      help="トレーニングデータディレクトリのパス")
    parser.add_argument("--val_dir", type=str, default="house/val",
                      help="検証データディレクトリのパス")
    
    args = parser.parse_args()
    
    # トレーニングの実行
    exit_code = train_model(args)
    import sys
    sys.exit(exit_code)