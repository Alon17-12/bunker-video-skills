"""The session folder: one fixed layout every agent and team member can find things in."""
import json, time
from pathlib import Path

LAYOUT = ["חומרי גלם/מצלמה 1", "חומרי גלם/מצלמה 2", "חומרי גלם/מקור",
          "תמלול", "פרק", "רילס", "תיקונים", "מסירה", ".tmp"]
STAGES = ["ingest", "transcript", "episode", "picks", "reels", "team", "deliver", "client"]


def create_session(root: Path, client: str, date: str) -> Path:
    s = Path(root) / f"{client} · {date}"
    for rel in LAYOUT:
        (s / rel).mkdir(parents=True, exist_ok=True)
    for f in ("יומן.md", "תיקונים/צוות.md", "תיקונים/לקוח.md"):
        (s / f).touch(exist_ok=True)
    return s


class Journal:
    def __init__(self, session: Path):
        self.path = Path(session) / "יומן.md"

    def log(self, stage: str, msg: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"- {time.strftime('%H:%M')} [{stage}] {msg}\n")


class State:
    def __init__(self, session: Path):
        self.path = Path(session) / ".state.json"
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {}

    def get(self, stage: str) -> str:
        return self.data.get(stage, "pending")

    def set(self, stage: str, status: str) -> None:
        assert status in ("pending", "running", "done", "failed"), status
        self.data[stage] = status
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1))
        tmp.replace(self.path)

    def next_pending(self, order: list[str]) -> str | None:
        return next((st for st in order if self.get(st) != "done"), None)
