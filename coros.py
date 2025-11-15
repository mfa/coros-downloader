#!/usr/bin/env python3
"""Minimal Coros API client based on xballoy/coros-api."""

import hashlib
import os
from datetime import datetime
from pathlib import Path

import httpx
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# Load environment variables
load_dotenv()

console = Console()
app = typer.Typer()

# Sport type mapping from Coros API
SPORT_TYPES = {
    100: "Run",
    101: "Indoor Run",
    102: "Trail Run",
    103: "Track Run",
    104: "Hike",
    105: "Mtn Climb",
    106: "Climb",
    200: "Road Bike",
    201: "Indoor Bike",
    202: "E-Bike",
    203: "Gravel Bike",
    204: "Mountain Bike",
    205: "E-MTB",
    299: "Helmet Riding",
    300: "Pool Swim",
    301: "Open Water",
    400: "Gym Cardio",
    401: "GPS Cardio",
    402: "Strength",
    500: "Ski",
    501: "Snowboard",
    502: "XC Ski",
    503: "Ski Touring",
    700: "Rowing",
    701: "Indoor Rower",
    702: "Whitewater",
    704: "Flatwater",
    705: "Windsurfing",
    706: "Speedsurfing",
    800: "Indoor Climb",
    801: "Bouldering",
    900: "Walk",
    901: "Jump Rope",
    902: "Floor Climb",
    10000: "Triathlon",
    10001: "Multisport",
    10002: "Ski Touring",
    10003: "Outdoor Climb",
}


class CorosAPI:
    """Simple Coros API client."""

    # Different API URLs for different regions
    # America: https://teamapi.coros.com
    # Europe: https://teameuapi.coros.com
    # China: https://teamcnapi.coros.com
    BASE_URL = "https://teameuapi.coros.com"

    def __init__(self, email: str, password: str, base_url: str = None):
        """Initialize with email and password.

        Args:
            email: Coros account email
            password: Coros account password
            base_url: Optional API base URL (defaults to Europe)
        """
        self.client = httpx.Client(base_url=base_url or self.BASE_URL)
        self.email = email
        self.password = password
        self.access_token = None

    def login(self):
        """Login and get access token."""
        pwd_hash = hashlib.md5(self.password.encode()).hexdigest()
        response = self.client.post(
            "/account/login",
            json={
                "account": self.email,
                "accountType": 2,
                "pwd": pwd_hash,
            },
        )
        response.raise_for_status()
        data = response.json()

        if "data" not in data or "accessToken" not in data["data"]:
            raise ValueError(f"Login failed: {data.get('message', 'Unknown error')}")

        self.access_token = data["data"]["accessToken"]
        self.client.headers["accessToken"] = self.access_token
        return data

    def get_activities(self, size=20, page_number=1):
        """Get list of activities."""
        if not self.access_token:
            raise ValueError("Must login first")

        response = self.client.get(
            "/activity/query",
            params={
                "size": size,
                "pageNumber": page_number,
                "modeList": "",
            },
        )
        response.raise_for_status()
        return response.json()

    def download_activity(self, label_id: str, sport_type: int, file_type: str = "1"):
        """Download activity file.

        Args:
            label_id: Activity label ID from get_activities()
            sport_type: Sport type from get_activities()
            file_type: File format - "1"=gpx, "2"=kml, "3"=tcx, "4"=fit, "0"=csv

        Returns:
            Tuple of (file_content, file_extension)
        """
        if not self.access_token:
            raise ValueError("Must login first")

        # Get download URL (Note: this is a POST request!)
        response = self.client.post(
            "/activity/detail/download",
            params={
                "labelId": label_id,
                "sportType": sport_type,
                "fileType": file_type,
            },
        )
        response.raise_for_status()
        data = response.json()

        if "data" not in data or "fileUrl" not in data["data"]:
            raise ValueError(f"Download failed: {data.get('message', 'Unknown error')}")

        # Download the actual file from the returned URL
        file_url = data["data"]["fileUrl"]
        file_response = self.client.get(file_url)
        file_response.raise_for_status()

        # Determine file extension from file_type
        extensions = {"0": "csv", "1": "gpx", "2": "kml", "3": "tcx", "4": "fit"}
        ext = extensions.get(file_type, "bin")

        return file_response.content, ext

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def get_api():
    """Get configured CorosAPI instance."""
    email = os.getenv("COROS_EMAIL")
    password = os.getenv("COROS_PASSWORD")

    if not email or not password:
        console.print(
            "[red]Error: COROS_EMAIL and COROS_PASSWORD must be set in .env file[/red]"
        )
        raise typer.Exit(1)

    return CorosAPI(email, password)


@app.command()
def list(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of activities to show")
):
    """List recent activities."""
    with get_api() as api:
        console.print("[cyan]Logging in...[/cyan]")
        api.login()

        console.print(f"[cyan]Fetching {limit} most recent activities...[/cyan]\n")
        result = api.get_activities(size=limit)

        if "data" not in result or "dataList" not in result["data"]:
            console.print("[yellow]No activities found[/yellow]")
            return

        activities = result["data"]["dataList"]

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Date", width=19)
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("ID", style="dim")

        for i, activity in enumerate(activities, 1):
            # Convert date field (YYYYMMDD format) to readable date
            date_num = activity.get("date", 0)
            if date_num:
                date_str = (
                    f"{str(date_num)[:4]}-{str(date_num)[4:6]}-{str(date_num)[6:8]}"
                )
            else:
                date_str = "Unknown"

            sport_type = activity.get("sportType", 0)
            sport_name = SPORT_TYPES.get(sport_type, f"Type {sport_type}")

            table.add_row(
                str(i),
                date_str,
                activity.get("name", "Unnamed"),
                sport_name,
                activity.get("labelId", ""),
            )

        console.print(table)
        console.print(f"\n[green]Total: {len(activities)} activities[/green]")


@app.command()
def download(
    format: str = typer.Option(
        "gpx", "--format", "-f", help="File format: gpx, fit, tcx, kml, csv"
    ),
    limit: int = typer.Option(
        10, "--limit", "-n", help="Number of activities to show for selection"
    ),
    output_dir: Path = typer.Option(".", "--output", "-o", help="Output directory"),
):
    """Download an activity file interactively."""
    # Map format to file_type
    format_map = {"csv": "0", "gpx": "1", "kml": "2", "tcx": "3", "fit": "4"}
    file_type = format_map.get(format.lower())

    if not file_type:
        console.print(
            f"[red]Error: Invalid format '{format}'. Choose from: gpx, fit, tcx, kml, csv[/red]"
        )
        raise typer.Exit(1)

    with get_api() as api:
        console.print("[cyan]Logging in...[/cyan]")
        api.login()

        console.print(f"[cyan]Fetching {limit} most recent activities...[/cyan]\n")
        result = api.get_activities(size=limit)

        if "data" not in result or "dataList" not in result["data"]:
            console.print("[yellow]No activities found[/yellow]")
            return

        activities = result["data"]["dataList"]

        # Display activities with numbers
        console.print("[bold]Select an activity to download:[/bold]\n")
        for i, activity in enumerate(activities, 1):
            # Format date and time
            date_num = activity.get("date", 0)
            start_time = activity.get("startTime", 0)

            if date_num and start_time:
                date_str = (
                    f"{str(date_num)[:4]}-{str(date_num)[4:6]}-{str(date_num)[6:8]}"
                )
                time_str = datetime.fromtimestamp(start_time).strftime("%H:%M")
                datetime_str = f"{date_str} {time_str}"
            elif date_num:
                datetime_str = (
                    f"{str(date_num)[:4]}-{str(date_num)[4:6]}-{str(date_num)[6:8]}"
                )
            else:
                datetime_str = "Unknown"

            console.print(
                f"  [cyan]{i:2d}.[/cyan] {datetime_str} - {activity.get('name', 'Unnamed')}"
            )

        # Get user selection
        console.print()
        selection = typer.prompt("Enter activity number", type=int)

        if selection < 1 or selection > len(activities):
            console.print(
                f"[red]Error: Invalid selection. Choose 1-{len(activities)}[/red]"
            )
            raise typer.Exit(1)

        # Download selected activity
        activity = activities[selection - 1]
        label_id = activity["labelId"]
        sport_type = activity["sportType"]
        name = activity.get("name", "activity").replace(" ", "_")

        console.print(
            f"\n[cyan]Downloading {activity.get('name', 'activity')} as {format.upper()}...[/cyan]"
        )

        content, ext = api.download_activity(label_id, sport_type, file_type)

        # Save to file
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{name}_{label_id}.{ext}"
        output_file.write_bytes(content)

        console.print(f"[green]✓ Saved to {output_file}[/green]")


if __name__ == "__main__":
    app()
