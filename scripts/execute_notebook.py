"""Execute the portfolio notebook using the current Python environment."""

from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Run every cell and replace the notebook only after successful execution."""
    path = ROOT / "notebooks" / "hotel_revenue_analysis.ipynb"
    notebook = nbformat.read(path, as_version=4)
    client = NotebookClient(
        notebook, timeout=180, kernel_name="python3",
        resources={"metadata": {"path": str(ROOT)}}, record_timing=False,
    )
    client.execute()
    nbformat.write(notebook, path)
    print("Notebook executed successfully and saved with outputs.")


if __name__ == "__main__":
    main()
