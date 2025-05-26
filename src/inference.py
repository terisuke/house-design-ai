"""¨Öâ¸åüë"""

import argparse
import logging
from pathlib import Path
from typing import Optional

from ultralytics import YOLO

logger = logging.getLogger(__name__)


def run_inference(args: argparse.Namespace) -> int:
    """¨Ö’ŸLY‹
    
    Args:
        args: ³ÞóÉé¤óp
        
    Returns:
        B†³üÉ
    """
    try:
        # âÇë’íüÉ
        model = YOLO(args.model)
        
        # ;ÏÑ¹’Ö—
        image_path = Path(args.image)
        if not image_path.exists():
            logger.error(f";ÏÕ¡¤ëL‹dKŠ~[“: {image_path}")
            return 1
        
        # ¨Ö’ŸL
        results = model.predict(
            source=str(image_path),
            save=args.save,
            save_txt=args.save_txt,
            save_conf=args.save_conf,
            save_crop=args.save_crop,
            hide_labels=args.hide_labels,
            hide_conf=args.hide_conf,
            conf=args.conf,
            iou=args.iou,
            max_det=args.max_det,
            device=args.device,
            visualize=args.visualize,
            augment=args.augment,
            agnostic_nms=args.agnostic_nms,
            classes=args.classes,
            retina_masks=args.retina_masks,
            boxes=not args.no_boxes,
            show=args.show,
            line_width=args.line_width,
            imgsz=args.imgsz,
            project=args.project,
            name=args.name,
            exist_ok=args.exist_ok,
        )
        
        # Pœ’h:
        for result in results:
            if hasattr(result, "boxes") and result.boxes is not None:
                logger.info(f"úUŒ_ªÖ¸§¯Èp: {len(result.boxes)}")
            if hasattr(result, "masks") and result.masks is not None:
                logger.info(f"»°áóÆü·çóÞ¹¯p: {len(result.masks)}")
        
        logger.info("¨ÖLŒ†W~W_")
        return 0
        
    except Exception as e:
        logger.error(f"¨Ö-k¨éüLzW~W_: {e}")
        return 1