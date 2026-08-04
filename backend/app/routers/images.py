import logging

from fastapi import APIRouter, HTTPException, Response

from app.services.images import InvalidPdataId, InvalidVariant, fetch_image_bytes

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.get("/images/{pdata_id}")
async def get_image(pdata_id: str, variant: str = "thumb") -> Response:
    try:
        content, content_type = await fetch_image_bytes(pdata_id, variant)
    except (InvalidPdataId, InvalidVariant) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.warning("NAS1 이미지 가져오기 실패: pdata_id=%s variant=%s error=%s", pdata_id, variant, e)
        raise HTTPException(status_code=502, detail="NAS 이미지 가져오기 실패")

    return Response(content=content, media_type=content_type)
