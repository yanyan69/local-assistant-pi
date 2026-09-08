import os
from modelscope.hub.file_download import model_file_download
from core.app_config import DATA_DIR

# Resolve the root directory (one level up from utilities/)
# Pulls the Llama 3.2 1B GGUF directly from ModelScope into the data directory
model_file_download(
    model_id='QuantFactory/Llama-3.2-1B-Instruct-GGUF',
    file_path='Llama-3.2-1B-Instruct.Q4_K_M.gguf',
    local_dir=str(DATA_DIR)
)