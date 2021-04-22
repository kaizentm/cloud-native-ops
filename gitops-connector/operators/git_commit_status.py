from dataclasses import dataclass

@dataclass
class GitCommitStatus:
    commit_id: str
    status_name: str
    state: str
    message: str