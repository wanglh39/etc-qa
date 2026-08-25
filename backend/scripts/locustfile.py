from locust import HttpUser, task, between


class EtcQaUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        response = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "123456"},
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = ""
            self.headers = {}

    @task(3)
    def health_check(self):
        self.client.get("/api/health")

    @task(2)
    def get_stats(self):
        self.client.get("/api/stats", headers=self.headers)

    @task(2)
    def list_qa(self):
        self.client.get("/api/qa/list?page=1&page_size=10", headers=self.headers)

    @task(1)
    def query_qa(self):
        self.client.post(
            "/api/query",
            json={"question": "ETC怎么办理"},
            headers=self.headers,
        )

    @task(1)
    def get_categories(self):
        self.client.get("/api/categories", headers=self.headers)