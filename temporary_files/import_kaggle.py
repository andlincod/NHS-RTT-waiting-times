import kagglehub

path = kagglehub.dataset_download(
    "hammad9191/nhs-consultant-led-rtt-waiting-times20212025",
    output_dir="data/raw",
    force_download=True  # or an absolute path
)

print("Path to dataset files:", path)