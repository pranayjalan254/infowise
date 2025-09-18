# predownload.py
from transformers import AutoTokenizer, AutoModelForTokenClassification
from ollama import Ollama

# 1️⃣ Preload BERT NER
AutoTokenizer.from_pretrained("dslim/bert-base-NER")
AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")

# 2️⃣ Preload Ollama phi3:latest
ollama = Ollama()
ollama.pull("phi3:latest")
