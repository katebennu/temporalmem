"""Download the cleaned LongMemEval dataset from HuggingFace into data/longmemeval/."""

from huggingface_hub import snapshot_download


def main() -> None:
    path = snapshot_download(
        repo_id="xiaowu0162/longmemeval-cleaned",
        repo_type="dataset",
        local_dir="data/longmemeval",
    )
    print(f"dataset downloaded to {path}")


if __name__ == "__main__":
    main()
