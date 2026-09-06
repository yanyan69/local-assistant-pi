import os
from modelscope.hub.file_download import model_file_download

# Resolve the root directory (one level up from utilities/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pulls the Llama 3.2 1B GGUF directly from ModelScope into the root directory
model_file_download(
    model_id='QuantFactory/Llama-3.2-1B-Instruct-GGUF',
    file_path='Llama-3.2-1B-Instruct.Q4_K_M.gguf',
    local_dir=BASE_DIR
)