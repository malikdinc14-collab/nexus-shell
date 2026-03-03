import os
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path


class WorkspaceGuard:
    def __init__(self, project_root):
        self.root = Path(project_root).resolve()
        self.transaction_dir = Path.home() / ".parallax" / "transactions"
        self.transaction_dir.mkdir(parents=True, exist_ok=True)
        self.flight_recorder_dir = self.root / "docs" / "workflow" / "flight_recorder"
        self.flight_recorder_dir.mkdir(parents=True, exist_ok=True)

    def get_file_hash(self, path):
        abs_path = self.root / path
        if not abs_path.exists():
            return None
        with open(abs_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def inspect(self, path):
        """READ authority: Return file content and metadata."""
        abs_path = self.root / path
        if not abs_path.exists():
            return {"error": "File not found"}

        with open(abs_path, "r") as f:
            content = f.read()

        return {
            "path": str(path),
            "hash": self.get_file_hash(path),
            "content": content,
            "mtime": abs_path.stat().st_mtime,
        }

    def search(self, query):
        """READ authority: Execute symbol/reference search via ripgrep."""
        try:
            result = subprocess.check_output(
                ["rg", "--json", query, str(self.root)], stderr=subprocess.STDOUT
            ).decode()
            return result
        except subprocess.CalledProcessError as e:
            return e.output.decode()

    def stage_patch(self, intent, changes):
        """STAGED authority: Create a new transaction."""
        tid = datetime.now().strftime("%Y%m%d_%H%M%S")
        t_path = self.transaction_dir / tid
        t_path.mkdir()

        transaction = {
            "id": tid,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "status": "staged",
            "changes": [],
        }

        for change in changes:
            path = change["path"]
            diff = change["diff"]
            current_hash = self.get_file_hash(path)

            # Save diff to file
            diff_file = t_path / f"{Path(path).name}.patch"
            with open(diff_file, "w") as f:
                f.write(diff)

            transaction["changes"].append(
                {
                    "path": str(path),
                    "base_hash": current_hash,
                    "patch_file": str(diff_file),
                }
            )

        with open(t_path / "metadata.json", "w") as f:
            json.dump(transaction, f, indent=2)

        # Trigger background verification
        self.verify(tid)

        return tid

    def verify(self, tid):
        """RUN authority: Detect and run project tests."""
        # Detect project type
        if (self.root / "package.json").exists():
            cmd = "npm test"
        elif (self.root / "pytest.ini").exists() or (self.root / "tests").exists():
            cmd = "pytest"
        else:
            cmd = "echo 'No test suite detected'"

        log_file = self.transaction_dir / tid / "verification.log"
        with open(log_file, "w") as f:
            subprocess.run(cmd, shell=True, cwd=self.root, stdout=f, stderr=f)

    def commit(self, tid):
        """WRITE authority: Apply staged patches atomically."""
        t_path = self.transaction_dir / tid
        with open(t_path / "metadata.json", "r") as f:
            metadata = json.load(f)

        if metadata["status"] != "staged":
            return {"error": "Transaction not in staged state"}

        # 1. Conflict Check (Stale Base Protection)
        for change in metadata["changes"]:
            current_hash = self.get_file_hash(change["path"])
            if current_hash != change["base_hash"]:
                metadata["status"] = "stale_base_conflict"
                with open(t_path / "metadata.json", "w") as f:
                    json.dump(metadata, f, indent=2)
                return {"error": f"Conflict: {change['path']} has changed on disk."}

        # 2. Apply Patches
        for change in metadata["changes"]:
            subprocess.run(
                ["patch", str(self.root / change["path"]), change["patch_file"]],
                check=True,
            )

        metadata["status"] = "committed"
        with open(t_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # 3. Flight Recorder (Provenance)
        recorder_path = self.flight_recorder_dir / f"{tid}.json"
        with open(recorder_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return {"status": "success"}
