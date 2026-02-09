from ledger.services import post_move


def ingest_balance_tx(bt):
    currency = bt["currency"].upper()
    bt_id = bt["id"]

    amount = bt["amount"]
    fee = bt.get("fee", 0)
    net = bt["net"]

    bt_type = bt["type"]

    # ---- Charge ----
    if bt_type == "charge":
        post_move(
            reference=f"stripe:{bt_id}:revenue",
            currency=currency,
            from_account_code="external",
            to_account_code="revenue",
            amount_minor=amount,
        )

        if fee:
            post_move(
                reference=f"stripe:{bt_id}:fee",
                currency=currency,
                from_account_code="revenue",
                to_account_code="fees",
                amount_minor=fee,
            )

        post_move(
            reference=f"stripe:{bt_id}:clearing",
            currency=currency,
            from_account_code="external",
            to_account_code="stripe_clearing",
            amount_minor=net,
        )

    # ---- Payout ----
    elif bt_type == "payout":
        post_move(
            reference=f"stripe:{bt_id}:payout",
            currency=currency,
            from_account_code="stripe_clearing",
            to_account_code="bank",
            amount_minor=abs(net),
        )

    # ---- Refund ----
    elif bt_type == "refund":
        post_move(
            reference=f"stripe:{bt_id}:refund",
            currency=currency,
            from_account_code="revenue",
            to_account_code="external",
            amount_minor=abs(amount),
        )

        if fee:
            post_move(
                reference=f"stripe:{bt_id}:fee_refund",
                currency=currency,
                from_account_code="fees",
                to_account_code="revenue",
                amount_minor=abs(fee),
            )

        post_move(
            reference=f"stripe:{bt_id}:clearing_refund",
            currency=currency,
            from_account_code="stripe_clearing",
            to_account_code="external",
            amount_minor=abs(net),
        )
