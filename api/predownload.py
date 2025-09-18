# predownload.py
from transformers import AutoTokenizer, AutoModelForTokenClassification

# 1️⃣ Preload BERT NER
AutoTokenizer.from_pretrained("dslim/bert-base-NER")
AutoModelForTokenClassification.from_pretrained("dslim/bert-base-NER")

