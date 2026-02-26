"""HuggingFace Dataset manager for the SQLite database.

Used by CI/CD pipeline to:
1. Create the Dataset repo if it doesn't exist.
2. Seed the database locally.
3. Upload the seeded DB to the Dataset repo.

Also provides download functionality for runtime use.
"""

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import RepositoryNotFoundError

DEFAULT_REPO_ID = "aniketp2009gmail/enterprise-ai-assistant-db"
DEFAULT_DB_PATH = "database/ecommerce.db"


def ensure_dataset_repo(repo_id: str, token: str) -> bool:
    """Create the HF Dataset repo if it does not exist.

    Returns True if repo exists or was created, False on error.
    """
    api = HfApi(token=token)
    try:
        api.repo_info(repo_id=repo_id, repo_type="dataset")
        print(f"Dataset repo '{repo_id}' already exists.")
        return True
    except RepositoryNotFoundError:
        print(f"Creating dataset repo '{repo_id}'...")
        api.create_repo(
            repo_id=repo_id,
            repo_type="dataset",
            private=False,
        )
        print(f"Dataset repo '{repo_id}' created.")
        return True
    except Exception as e:
        print(f"ERROR: Could not verify/create dataset repo: {e}")
        return False


def seed_and_upload(repo_id: str, token: str, db_path: str = DEFAULT_DB_PATH):
    """Seed a fresh database and upload it to the HF Dataset."""
    db_file = Path(db_path)

    # Remove existing DB to ensure a clean seed
    if db_file.exists():
        db_file.unlink()

    # Seed the database
    from database.seed_data import seed_database

    print(f"Seeding database at {db_path}...")
    seed_database(db_path)

    if not db_file.exists():
        print(f"ERROR: Seed did not create database at {db_path}")
        sys.exit(1)

    print(f"Database seeded: {db_file.stat().st_size / 1024:.1f} KB")

    # Upload to HF
    api = HfApi(token=token)
    print(f"Uploading {db_path} to {repo_id}...")
    api.upload_file(
        path_or_fileobj=str(db_file),
        path_in_repo="ecommerce.db",
        repo_id=repo_id,
        repo_type="dataset",
        commit_message="Update seeded ecommerce database",
    )
    print("Upload complete.")


def download_db(repo_id: str, token: str, target_path: str) -> bool:
    """Download the database from HF Dataset to target_path.

    Returns True on success, False on failure.
    """
    try:
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        hf_hub_download(
            repo_id=repo_id,
            filename="ecommerce.db",
            repo_type="dataset",
            token=token,
            local_dir=str(target.parent),
            local_dir_use_symlinks=False,
        )
        print(f"Database downloaded to {target_path}")
        return True
    except Exception as e:
        print(f"WARNING: Download failed: {e}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage HF Dataset for the ecommerce DB"
    )
    parser.add_argument(
        "action", choices=["seed-and-upload", "download", "ensure-repo"]
    )
    parser.add_argument(
        "--repo-id",
        default=os.getenv("HF_DATASET_REPO", DEFAULT_REPO_ID),
    )
    parser.add_argument("--token", default=os.getenv("HF_TOKEN"))
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH)

    args = parser.parse_args()

    if not args.token:
        print("ERROR: HF_TOKEN is required (set via --token or HF_TOKEN env var)")
        sys.exit(1)

    if args.action == "ensure-repo":
        success = ensure_dataset_repo(args.repo_id, args.token)
        sys.exit(0 if success else 1)
    elif args.action == "seed-and-upload":
        ensure_dataset_repo(args.repo_id, args.token)
        seed_and_upload(args.repo_id, args.token, args.db_path)
    elif args.action == "download":
        success = download_db(args.repo_id, args.token, args.db_path)
        sys.exit(0 if success else 1)
