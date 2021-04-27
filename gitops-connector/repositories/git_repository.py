from abc import ABC, abstractmethod

class GitRepositoryInterface(ABC):
    
    @abstractmethod
    def post_commit_status(self, commit_status):
        pass

    @abstractmethod
    def get_pr_num(self, commit_id) -> str:
        pass

    @abstractmethod
    def get_pr_metadata(self, commit_id):
        pass