from pathlib import Path


def test_expected_repo_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    expected_files = [
        "README.md",
        "sticknav.py",
        "pyproject.toml",
        "requirements.txt",
        "environment.yml",
    ]

    for relative_path in expected_files:
        assert (root / relative_path).exists(), f"Missing expected repository file: {relative_path}"
