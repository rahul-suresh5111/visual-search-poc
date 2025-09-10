import requests
from backend.config import Config

class DatabricksClient:
    def __init__(self):
        self.host = Config.DATABRICKS_HOST
        self.token = Config.DATABRICKS_TOKEN
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def run_job(self, job_id=None, notebook_params=None):
        job_id = job_id or Config.DATABRICKS_JOB_ID
        if not job_id or job_id == 0:
            raise ValueError("Databricks Job ID is not configured")

        url = f"{self.host}/api/2.1/jobs/run-now"
        payload = {"job_id": job_id}
        if notebook_params:
            payload["notebook_params"] = notebook_params

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("run_id")

    def get_run_status(self, run_id):
        url = f"{self.host}/api/2.1/jobs/runs/get"
        params = {"run_id": run_id}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_run_output(self, run_id):
        url = f"{self.host}/api/2.0/jobs/runs/get-output"
        params = {"run_id": run_id}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    