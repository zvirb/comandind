"""Service for handling user feedback on AI responses."""
import logging
from shared.utils.database_setup import get_db
from shared.database.models import MessageFeedback

logger = logging.getLogger(__name__)

class FeedbackService:
    def handle_feedback(self, session_id: str, message_id: str, feedback: str):
        """Handles user feedback on a message."""
        try:
            with next(get_db()) as db:
                feedback_entry = MessageFeedback(
                    session_id=session_id,
                    message_id=message_id,
                    feedback=feedback,
                )
                db.add(feedback_entry)
                db.commit()
                logger.info(f"Feedback recorded for message {message_id}: {feedback}")
        except Exception as e:
            logger.error(f"Error recording feedback: {e}", exc_info=True)

feedback_service = FeedbackService()
