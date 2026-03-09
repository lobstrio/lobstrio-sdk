# lobstrio

Python SDK for the [Lobstr.io](https://lobstr.io) API.

## Installation

```bash
pip install lobstrio
```

## Quick Start

```python
from lobstrio import LobstrClient

client = LobstrClient(token="your-api-token")

# Get account info
user = client.me()
print(user.email)

# List crawlers
for crawler in client.crawlers.list():
    print(crawler.name)
```
