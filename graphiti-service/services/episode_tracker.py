from graphiti_service.repositories.episode_repo import get_episode_by_conversation


class EpisodeTracker:
    @staticmethod
    def has_done_episode(conversation_id: str) -> bool:
        eps = get_episode_by_conversation(conversation_id)
        return any(e.status == "done" for e in eps)
