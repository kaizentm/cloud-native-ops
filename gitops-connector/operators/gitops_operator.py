from abc import ABC, abstractmethod

class GitopsOperatorInterface(ABC):
    
    @abstractmethod
    def extract_commit_statuses(self, phase_data):
        pass
    
    @abstractmethod
    def is_finished(self, phase_data) -> bool:
        pass

    @abstractmethod
    def get_commit_id(self, phase_data) -> str:
        pass



