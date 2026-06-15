# security/inputs.py – using Groq's Llama 3.1 for classification
from typing import List, Dict, Tuple, Optional, Literal
from groq import Groq

_groq_client: Optional[Groq] = None

def set_groq_client(client: Groq) -> None:
    global _groq_client
    _groq_client = client

def classify_with_llama(text: str) -> Tuple[Literal["safe", "unsafe"], float]:
    """
    Use Groq's llama-3.1-8b-instant to classify text as safe or unsafe.
    """
    if _groq_client is None:
        raise RuntimeError("Groq client not set.")
    
    prompt = f"""You are a content safety classifier. 
Analyze the following text and respond with exactly one word: either "SAFE" or "UNSAFE". 
Do not output anything else.

Text: {text}"""
    
    try:
        response = _groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",  # available on Groq free tier
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10,
        )
        answer = response.choices[0].message.content.strip().upper()
        if "UNSAFE" in answer:
            return ("unsafe", 1.0)
        else:
            return ("safe", 0.0)
    except Exception as e:
        print(f"[Classifier] Error: {e} – failing open (safe).")
        return ("safe", 0.0)

def analyse_risk(text: str) -> Tuple[Literal["safe", "suspicious", "malicious"], float]:
    if not text or not isinstance(text, str):
        return ("safe", 0.0)
    
    verdict, confidence = classify_with_llama(text)
    if verdict == "unsafe":
        return ("malicious", confidence)
    else:
        return ("safe", 0.0)

def scan_input(news_list: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    safe = []
    suspicious = []
    for item in news_list:
        text = f"{item.get('title', '')} {item.get('summary', '')}".strip()
        if not text:
            safe.append(item.copy())
            continue
        
        risk, conf = analyse_risk(text)
        if risk == "malicious":
            print(f"[Input Guard] Malicious article blocked (confidence {conf:.2f})")
            continue
        elif risk == "suspicious":
            # (we don't use suspicious here, but keep for compatibility)
            suspicious.append(item.copy())
        else:
            safe.append(item.copy())
    
    return safe, suspicious