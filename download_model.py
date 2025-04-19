from huggingface_hub import snapshot_download

# Define model ID and cache directory
model_id = "cardiffnlp/twitter-roberta-base-sentiment-latest"
cache_dir = r"C:\Users\Asus Laptop\Downloads\twitter_roberta_model"

# Download the model
snapshot_download(
    repo_id=model_id,
    cache_dir=cache_dir,
    use_symlinks=False  # ✅ No symlink issues on Windows
)
