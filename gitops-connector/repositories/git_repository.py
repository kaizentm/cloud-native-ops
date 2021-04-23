from abc import ABC, abstractmethod

class GitRepositoryInterface(ABC):
    
    @abstractmethod
    def post_commit_status(self, commit_status):
        pass



