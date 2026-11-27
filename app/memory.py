import threading
import uuid

MAX_HISTORY_TURNS = 5


class ConversationStore:
    """In-memory conversation memory: (question, answer) pairs per conversation.

    Sliding window: keeps only the last MAX_HISTORY_TURNS turns, so context cost
    stays constant no matter how long the chat runs.

    NOTE: a process-local dict. Container restarts wipe it, and it is NOT shared
    across workers. Production would put this in Redis or Postgres — see README.
    """

    def __init__(self):
        self._conversations: dict[str, list[dict]] = {}
        self._lock = threading.Lock()   # FastAPI runs sync endpoints in a threadpool

    def create(self) -> str:
        cid = uuid.uuid4().hex
        with self._lock:
            self._conversations[cid] = []
        return cid

    def exists(self, cid: str) -> bool:
        return cid in self._conversations

    def history(self, cid: str) -> list[dict]:
        with self._lock:
            return list(self._conversations.get(cid, []))

    def append_turn(self, cid: str, question: str, answer: str) -> int:
        """Store one (question, answer) pair; returns the turn count after trimming."""
        with self._lock:
            conv = self._conversations.setdefault(cid, [])
            conv.append({"role": "user", "content": question})
            conv.append({"role": "assistant", "content": answer})
            max_messages = MAX_HISTORY_TURNS * 2
            if len(conv) > max_messages:
                conv[:] = conv[-max_messages:]   # in-place trim: sliding window
            return len(conv) // 2

    def delete(self, cid: str) -> None:
        with self._lock:
            self._conversations.pop(cid, None)


store = ConversationStore()