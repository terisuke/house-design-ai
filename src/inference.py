"""推論モジュール"""

import argparse
import logging
from pathlib import Path
from typing import Optional

from ultralytics import YOLO

logger = logging.getLogger(__name__)


def run_inference(args: argparse.Namespace) -> int:
    """YOLOモデルを使用して推論を実行
    
    Args:
        args: コマンドライン引数
        
    Returns:
        終了コード（成功: 0、失敗: 1）
    """
    try:
        # モデルをロード
        model = YOLO(args.model_path)
        
        # 画像パスの検証
        image_path = Path(args.image_path)
        if not image_path.exists():
            logger.error(f"画像ファイルが見つかりません: {image_path}")
            return 1
        
        # 推論を実行
        results = model.predict(
            source=str(image_path),
            save=True,
            project=args.output_dir,
        )
        
        # 結果を表示
        for result in results:
            if hasattr(result, "boxes") and result.boxes is not None:
                logger.info(f"検出されたオブジェクト数: {len(result.boxes)}")
            if hasattr(result, "masks") and result.masks is not None:
                logger.info(f"検出されたマスク数: {len(result.masks)}")
        
        logger.info("推論が正常に完了しました")
        return 0
        
    except Exception as e:
        logger.error(f"推論中にエラーが発生しました: {e}")
        return 1