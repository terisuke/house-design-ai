import argparse
import logging
import os
import shutil  # 追加
import sys
from typing import List

import yaml

# ロギング設定
logger = logging.getLogger(__name__)


def download_dataset_from_gcs(
    gcs_bucket_name: str,
    gcs_prefix: str,
    local_dir: str,
    exclude_patterns: List[str] = [".DS_Store", "labels.cache"],
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
        logger.info(
            f"GCSからデータセットをダウンロード: gs://{gcs_bucket_name}/{gcs_prefix} -> {local_dir}"
        )
        logger.info(
            "[INFO] Python API (google-cloud-storage) を使用してデータセットをダウンロードします。"
        )
        from src.cloud.storage import download_dataset

        if not download_dataset(
            bucket_name=gcs_bucket_name,
            source_prefix=gcs_prefix,
            destination_dir=local_dir,
            exclude_patterns=exclude_patterns,
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
            logger.info(
                f"ファイル一覧 (最初の10件): {local_files[:10] if len(local_files) > 10 else local_files}"
            )
        except Exception as e:
            logger.warning(f"ローカルディレクトリの確認中にエラー: {e}")

        return True  # Python APIが成功した場合は True

    except Exception as e:
        logger.error(f"データセットダウンロードエラー: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def update_data_yaml(yaml_path: str, train_dir: str, val_dir: str) -> bool:
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
        with open(yaml_path, "r") as f:
            data_config = yaml.safe_load(f)

        # データパスを更新 (images, labels サブディレクトリを直接指定)
        data_config["train"] = train_dir
        data_config["val"] = val_dir

        # クラス情報があることを確認
        if "nc" not in data_config:
            data_config["nc"] = 27  # デフォルト値

        if "names" not in data_config:
            data_config["names"] = ['1F', '2F', 'CL1', 'CL2', 'CL3', 'CL4', 'CO', 'D', 'DN', 'DR', 'E', 'H', 'House', 'K', 'L', 'North', 'R1', 'R2', 'R3', 'R4', 'Road', 'ST', 'South', 'Space', 'UB', 'UP', 'WC']
        # 更新したYAMLを書き込み
        with open(yaml_path, "w") as f:
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
        import sys  # Ensure sys is imported within the function scope
        
        # ログレベルを詳細に設定
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        
        # 実行環境の確認
        logger.info("=== Training Script Started ===")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Python path: {sys.path}")
        logger.info(f"Arguments: {args}")
        # 環境変数とGCP認証情報を確認
        logger.info("環境変数とGCP認証情報を確認")
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        logger.info(f"GOOGLE_APPLICATION_CREDENTIALS: {cred_path}")
        if cred_path and os.path.exists(cred_path):
            logger.info(f"認証情報ファイルが存在します: {cred_path}")
        else:
            logger.warning(
                "認証情報ファイルが存在しないか、環境変数が設定されていません"
            )

        # GCSからデータセットをダウンロード
        if hasattr(args, "bucket_name") and args.bucket_name:
            logger.info(f"GCSからデータセットをダウンロードします: {args.bucket_name}")

            # トレーニングデータのダウンロード
            # 絶対パスに変換
            if not os.path.isabs(args.train_dir):
                train_dir = os.path.abspath(args.train_dir)
            else:
                train_dir = args.train_dir
                
            # train_dir が存在し、空でない場合は削除 (Vertex AI 環境を想定)
            if os.path.exists(train_dir) and os.listdir(train_dir):
                logger.warning(f"{train_dir} は空ではありません。削除します。")
                shutil.rmtree(train_dir)  # shutil を使用して再帰的に削除

            if not download_dataset_from_gcs(
                gcs_bucket_name=args.bucket_name,
                gcs_prefix="house/train",  # GCS上のtrainディレクトリ
                local_dir=train_dir,  # ローカルのtrainディレクトリ
            ):
                logger.error("トレーニングデータのダウンロードに失敗しました")
                return 1

            # 検証データのダウンロード
            # 絶対パスに変換
            if not os.path.isabs(args.val_dir):
                val_dir = os.path.abspath(args.val_dir)
            else:
                val_dir = args.val_dir
                
            # val_dir が存在し、空でない場合は削除
            if os.path.exists(val_dir) and os.listdir(val_dir):
                logger.warning(f"{val_dir} は空ではありません。削除します。")
                shutil.rmtree(val_dir)

            if not download_dataset_from_gcs(
                gcs_bucket_name=args.bucket_name,
                gcs_prefix="house/val",  # GCS上のvalディレクトリ
                local_dir=val_dir,  # ローカルのvalディレクトリ
            ):
                logger.error("検証データのダウンロードに失敗しました")
                return 1

            logger.info("GCSからのデータセットダウンロードが完了しました")

        # data.yamlのパス
        data_yaml_path = args.data_yaml

        # データ設定ファイルの更新
        # パスの正規化 - コンテナ内での絶対パスを使用
        logger.info(f"Current working directory: {os.getcwd()}")
        
        # args.train_dir と args.val_dir が既に絶対パスの場合はそのまま使用
        # そうでない場合は絶対パスに変換
        if not os.path.isabs(args.train_dir):
            train_dir_abs = os.path.abspath(args.train_dir)
        else:
            train_dir_abs = args.train_dir
            
        if not os.path.isabs(args.val_dir):
            val_dir_abs = os.path.abspath(args.val_dir)
        else:
            val_dir_abs = args.val_dir
            
        train_images_path = os.path.join(train_dir_abs, "images")
        val_images_path = os.path.join(val_dir_abs, "images")
        
        logger.info(f"データパスを設定: train={train_images_path}, val={val_images_path}")
        
        if not update_data_yaml(
            data_yaml_path, train_images_path, val_images_path
        ):
            logger.error("data.yamlの更新に失敗しました")
            return 1

        # モデルのインポート
        try:
            from ultralytics import YOLO
        except ImportError as e:
            logger.error(f"ultralyticsパッケージのインポートエラー: {e}")
            logger.error(f"Python version: {sys.version}")
            logger.error(f"Python path: {sys.path}")
            try:
                import ultralytics
                logger.error(f"ultralytics module found at: {ultralytics.__file__}")
            except:
                logger.error("ultralytics module not found in sys.modules")
            return 1

        # GPU availability check
        import torch
        if torch.cuda.is_available():
            logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
            logger.info(f"CUDA version: {torch.version.cuda}")
            logger.info(f"Number of GPUs: {torch.cuda.device_count()}")
            device = 0
        else:
            logger.warning("No GPU detected, will use CPU for training")
            device = 'cpu'
        
        # モデルのロード
        logger.info(f"モデルをロード中: {args.model}")
        
        # GCSパスの場合はダウンロード
        if args.model.startswith("gs://"):
            from src.cloud.storage import download_file
            local_model_path = "/tmp/model.pt"
            logger.info(f"GCSからモデルをダウンロード: {args.model} -> {local_model_path}")
            
            # GCS URLをパース
            gcs_parts = args.model.replace("gs://", "").split("/", 1)
            bucket_name = gcs_parts[0]
            blob_name = gcs_parts[1] if len(gcs_parts) > 1 else ""
            
            if download_file(bucket_name, blob_name, local_model_path):
                model = YOLO(local_model_path)
            else:
                logger.error(f"GCSからのモデルダウンロードに失敗: {args.model}")
                return 1
        else:
            model = YOLO(args.model)

        # トレーニングパラメータの設定
        train_params = {
            "data": data_yaml_path,
            "epochs": args.epochs,
            "batch": args.batch_size,
            "imgsz": args.imgsz,
            "optimizer": args.optimizer,
            "lr0": args.lr0,
            "iou": args.iou_threshold,
            "conf": args.conf_threshold,
            "rect": args.rect,
            "cos_lr": args.cos_lr,
            "mosaic": args.mosaic,
            "degrees": args.degrees,
            "scale": args.scale,
            "single_cls": getattr(args, "single_cls", False),
            "exist_ok": True,  # 既存のトレーニング結果を上書き
            "device": device,  # 検出されたデバイスを使用
        }

        # トレーニングの実行
        logger.info(
            f"トレーニングを開始: {args.epochs}エポック, バッチサイズ={args.batch_size}"
        )
        results = model.train(**train_params)

        # トレーニング結果のロギング
        best_fitness = results.fitness
        logger.info(f"トレーニング完了: best fitness={best_fitness}")

        # 最良のモデルのパスを表示
        best_model_path = os.path.join(model.trainer.save_dir, "weights", "best.pt")
        if os.path.exists(best_model_path):
            logger.info(f"最良のモデルを保存: {best_model_path}")
            print(
                f"トレーニングが完了しました。最良のモデル: {best_model_path}"
            )  # 標準出力にも表示

        # upload_modelは削除。save_dirをアップロードする。
        # Upload the entire save_dir to Cloud Storage
        if args.upload_bucket:
            from src.cloud.storage import (
                upload_directory_to_gcs as upload_directory,
            )  # 依存関係の問題を避けるため、ここでのみインポートする

            upload_directory(
                args.upload_bucket,
                str(model.trainer.save_dir),  # ローカルの保存先ディレクトリ
                args.save_dir,  # GCS上のパス (/appからの相対パスはrun_vertex_job.pyで計算済み)
            )
        return 0

    except Exception as e:
        logger.error(f"トレーニングエラー: {e}", exc_info=True)
        return 1


# コマンドライン実行用
if __name__ == "__main__":
    # 引数パーサーの設定
    parser = argparse.ArgumentParser(
        description="YOLOv11セグメンテーションモデルのトレーニング"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="yolo11n-seg.pt",
        help="ベースYOLOv11モデル",
    )
    parser.add_argument(
        "--epochs", type=int, default=100, help="トレーニングエポック数"
    )
    parser.add_argument("--batch_size", type=int, default=16, help="バッチサイズ")
    parser.add_argument("--imgsz", type=int, default=640, help="入力画像サイズ")
    parser.add_argument(
        "--data_yaml",
        type=str,
        default="/app/config/data.yaml",
        help="data.yamlファイルのパス",
    )
    parser.add_argument(
        "--train_dir",
        type=str,
        default="/app/house/train",
        help="トレーニングデータディレクトリのパス",
    )
    parser.add_argument(
        "--val_dir", type=str, default="/app/house/val", help="検証データディレクトリのパス"
    )
    parser.add_argument(
        "--optimizer", type=str, default="AdamW", help="オプティマイザー"
    )
    parser.add_argument(
        "--lr0", type=float, default=0.01, help="初期学習率"
    )
    parser.add_argument(
        "--iou_threshold", type=float, default=0.7, help="IoU閾値"
    )
    parser.add_argument(
        "--conf_threshold", type=float, default=0.25, help="信頼度閾値"
    )
    parser.add_argument(
        "--rect", action="store_true", help="矩形トレーニングを使用するかどうか"
    )
    parser.add_argument(
        "--cos_lr", action="store_true", help="コサイン学習率スケジューラーを使用するかどうか"
    )
    parser.add_argument(
        "--mosaic", type=float, default=1.0, help="モザイク確率"
    )
    parser.add_argument(
        "--degrees", type=float, default=0.0, help="回転角度（度）"
    )
    parser.add_argument(
        "--scale", type=float, default=0.5, help="スケール範囲"
    )
    parser.add_argument(
        "--upload_bucket", type=str, default=None, help="結果をアップロードするGCSバケット名"
    )
    parser.add_argument(
        "--save_dir", type=str, default="runs/train", help="GCS上の保存ディレクトリパス"
    )

    args = parser.parse_args()

    # トレーニングの実行
    exit_code = train_model(args)
    sys.exit(exit_code)
