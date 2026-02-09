import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from ledger.services import post_move


@csrf_exempt
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse("Missing STRIPE_WEBHOOK_SECRET", status=500)
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return HttpResponse("Invalid payload", status=400)
    except stripe.SignatureVerificationError:
        return HttpResponse("Invalid signature", status=400)

    event_type = event["type"]
    event_id = event["id"]

    if event_type == "payment_intent.succeeded":
        obj = event["data"]["object"]

        amount = int(obj["amount_received"] or obj["amount"])
        currency = str(obj["currency"]).upper()

        post_move(
            reference=event_id,
            currency=currency,
            from_account_code="stripe_clearing",
            to_account_code="revenue",
            amount_minor=amount,
        )
    return HttpResponse(status=200)
