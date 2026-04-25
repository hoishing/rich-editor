const MAX_RETRIES = 3;

class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async fetchUser(id) {
    const res = await fetch(`${this.baseUrl}/users/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }
}

const client = new ApiClient("https://api.example.com");
client.fetchUser(42).then((user) => console.log(user));
