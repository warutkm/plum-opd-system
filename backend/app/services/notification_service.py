class NotificationService:
    def send_update(self, member_id: str, claim_id: str, status: str, message: str) -> None:
        """
        Send a notification to a member about their claim status.
        Currently a stub for future integration with email/SMS/Websockets.
        """
        print(f"[NOTIFICATION] To: {member_id} | Claim: {claim_id} | Status: {status} | Msg: {message}")
