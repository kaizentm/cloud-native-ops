from orchestrators.cicd_orchestrator import CicdOrchestratorInterface 
from repositories.git_repository import GitRepositoryInterface
from clients.azdo_client import AzdoClient


class AzdoCicdOrchestrator(CicdOrchestratorInterface):

    def __init__(self, git_repository: GitRepositoryInterface):    
        super().__init__(git_repository)
        self.azdo_client = AzdoClient()
        self.headers = self.azdo_client.get_rest_api_headers()

    def notify_on_deployment_completion(self, commit_id, is_successful):
        pr_num = self.git_repository.get_pr_num(commit_id)        
        if pr_num:
            self._update_pr_task(state, pr_num)

    # Update the Azure Pipeline task waiting for the PR to complete.
    # is_alive: If true, the PR is active and absence of task data is an error.
    def _update_pr_task(self, is_successful, pr_num, is_alive=True):
        pr_task = self._get_pr_task_data(pr_num, is_alive)
        if not pr_task:
            if is_alive:
                logging.error(f'PR {pr_num} has no metadata! Cannot complete task callback.')
            return False
        logging.info(f'PR {pr_num}: Rollout {state}, attempting task completion callback...')

        if is_successful:
            state = 'succeeded'
        else:
            state = 'failed'


        # The build task may have been cancelled, timed out, etc.
        # Working with the plan in this state can cause 500 errors.
        # Finish gracefully so ArgoCD doesn't keep calling us.
        if self._plan_already_completed(pr_task):
            return False

        planurl = pr_task['planurl']
        projectid = pr_task['projectid']
        planid = pr_task['planid']
        url = f'{planurl}{projectid}/_apis/distributedtask/hubs/build/plans/{planid}/events?api-version=2.0-preview.1'
        data = {
            'name': "TaskCompleted",
            'taskId': pr_task['taskid'],
            'jobid': pr_task['jobid'],
            'result': state
        }
        response = requests.post(url=url, headers=self.headers, json=data)
        # Throw appropriate exception if request failed
        response.raise_for_status()

        logging.info(f'PR {pr_num}: Successfully completed task {pr_task["taskid"]}')
        return True

    # is_alive: Metadata cache misses are OK if the PR is abandoned.
    def _get_pr_task_data(self, pr_num, is_alive=True):
        # Lock the cache due to temporal store.
        with pr_cache_lock:
            if pr_num in pr_task_data_cache:
                logging.info(f'PR {pr_num}: Metadata read cache hit')
                # We only expect to have one callback, so remove the cache entry.
                return pr_task_data_cache.pop(pr_num)

        if is_alive:
            logging.warning(f'PR {pr_num}: Metadata cache miss')
        return self.git_repository.get_pr_metadata(pr_num)

    # Given a PR task, check if it's parent plan has already completed.
    # Note: Completed does not necessarily mean it succeeded.
    def _plan_already_completed(self, pr_task):
        planurl = pr_task['planurl']
        projectid = pr_task['projectid']
        planid = pr_task['planid']
        url = f'{planurl}{projectid}/_apis/distributedtask/hubs/build/plans/{planid}'

        response = requests.get(url=url, headers=self.headers)
        # Throw appropriate exception if request failed
        response.raise_for_status()

        plan_info = response.json()
        return plan_info['state'] == 'completed'
