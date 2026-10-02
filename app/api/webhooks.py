from fastapi import APIRouter, HTTPException, Request

from app.gateway import SIGNATURE_HEADER
from app.services import payments
from app.services.orders import OrderNotFound

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/payment")
async def payment(request: Request) -> dict:
    # Verify over the raw bytes — re-serializing would change them and break HMAC.
    raw_body = await request.body()
    signature = request.headers.get(SIGNATURE_HEADER)
    try:
        await payments.process_webhook(raw_body, signature)
    except payments.BadSignature:
        raise HTTPException(status_code=401, detail="invalid signature")
    except payments.MalformedWebhook as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except OrderNotFound:
        raise HTTPException(status_code=404, detail="order not found")
    except payments.AmountMismatch:
        raise HTTPException(status_code=400, detail="amount mismatch")
    return {"status": "ok"}
