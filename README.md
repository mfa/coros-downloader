# Coros API Client

A minimal Python CLI for downloading activity data from Coros Training Hub.
Based on the unofficial API used by [xballoy/coros-api](https://github.com/xballoy/coros-api).

## Features

- List recent activities in a table
- Download activities in multiple formats (GPX, FIT, TCX, KML, CSV)
- Interactive selection - no copy/pasting IDs
- Multi-region support (Europe, America, China)

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Create a `.env` file with your credentials:
```bash
cp .env.example .env
# Edit .env and add your COROS_EMAIL and COROS_PASSWORD
```

## Usage

### List Activities

```bash
uv run python coros.py list
uv run python coros.py list --limit 20
```

### Download Activities

```bash
uv run python coros.py download
uv run python coros.py download --format fit
uv run python coros.py download --format gpx --limit 20 --output ./downloads
```

**Supported formats:** `gpx`, `fit`, `tcx`, `kml`, `csv`

## Regional APIs

By default, the client uses the Europe API. If you're in a different region:

```python
# Edit coros.py and change BASE_URL to:
# America: https://teamapi.coros.com
# Europe: https://teameuapi.coros.com (default)
# China: https://teamcnapi.coros.com
```

## Important Notes

**Website Logout**: When you login via this script, Coros will automatically log you out of their web interface. This is a limitation of how Coros handles sessions - they only allow one active session at a time. Your mobile app will remain logged in.

- This uses the non-public Coros API which could change at any time
- For official API access, you need to apply for OAuth2 credentials from Coros
- The API has rate limiting - avoid making excessive requests

## License

MIT
