from locust import HttpUser, task, between
import random

class CareerNavigatorUser(HttpUser):
    wait_time = between(1, 3)

    @task(4)
    def interview_flow(self):
        self.client.post("/interview/generate", json={
            "role": "software engineer",
            "level": "junior"
        })

        self.client.post("/interview/evaluate", json={
            "answer": "example answer"
        })

    @task(3)
    def analysis_flow(self):
        self.client.post("/analysis/start", json={
            "profile": "test profile data"
        })

    @task(2)
    def certificate_flow(self):
        self.client.post("/documents/upload", json={
            "file_type": "pdf",
            "content": "fake_base64_data"
        })

    @task(1)
    def auth_flow(self):
        self.client.post("/auth/login", json={
            "email": "test@test.com",
            "password": "test123"
        })