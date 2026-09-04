from modelscope.hub.file_download import model_file_download

# Pulls the Llama 3.2 1B GGUF directly from ModelScope
model_file_download(
    model_id='QuantFactory/Llama-3.2-1B-Instruct-GGUF',
    file_path='Llama-3.2-1B-Instruct.Q4_K_M.gguf',  # Notice the dot before Q4
    local_dir='.'
)
