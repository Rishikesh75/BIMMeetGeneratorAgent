FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface \
    BIM_BASE_MODEL=HuggingFaceTB/SmolLM2-360M-Instruct \
    BIM_ADAPTER_ID=Rishi74518/smollm2-360m-bim-lora

COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 user \
    && mkdir -p /home/user/.cache/huggingface /app/output \
    && chown -R user:user /app /home/user

USER user

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
