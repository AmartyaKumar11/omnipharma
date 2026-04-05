import os
import json
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import httpx
from pydantic import BaseModel, ValidationError

from sqlalchemy.orm import Session
from sqlalchemy import func, select, desc

from app.models.stock import Inventory
from app.models.product import Product
from app.models.store import Store
from app.models.order import OrderItem, Order

logger = logging.getLogger("ai_audit_logger")
logging.basicConfig(level=logging.INFO, filename="ai_audit.log", filemode="a", format="%(asctime)s - %(message)s")

from dotenv import load_dotenv
load_dotenv()

# Key loading sequence
MOONSHOT_API_KEY = os.environ.get("MOONSHOT_API_KEY") 
KIMI_API_KEY = os.environ.get("KIMI_API_KEY", MOONSHOT_API_KEY)
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "").lower()
NVIDIA_LLM_MODEL = os.environ.get("NVIDIA_LLM_MODEL", "meta/llama-3.1-70b-instruct")

# Provider resolving logic
if LLM_PROVIDER == "moonshot":
    ACTIVE_LLM_ENDPOINT = "https://api.moonshot.cn/v1/chat/completions"
    ACTIVE_LLM_MODEL = "moonshot-v1-8k"
    ACTIVE_API_KEY = KIMI_API_KEY
elif LLM_PROVIDER == "nvidia":
    ACTIVE_LLM_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
    ACTIVE_LLM_MODEL = NVIDIA_LLM_MODEL
    ACTIVE_API_KEY = NVIDIA_API_KEY
else:
    # Auto-detect behavior based on raw prefixed
    detected_key = KIMI_API_KEY or NVIDIA_API_KEY or ""
    if detected_key.startswith("nvapi-"):
        ACTIVE_LLM_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
        ACTIVE_LLM_MODEL = NVIDIA_LLM_MODEL
        ACTIVE_API_KEY = detected_key
    else:
        ACTIVE_LLM_ENDPOINT = "https://api.moonshot.cn/v1/chat/completions"
        ACTIVE_LLM_MODEL = "moonshot-v1-8k"
        ACTIVE_API_KEY = detected_key

OPERATIONS = [
    "LOW_STOCK",
    "TOP_PRODUCTS",
    "SALES_SUMMARY",
    "STORE_COMPARISON",
    "ASSOCIATION_ANALYSIS",
    "FORECAST",
    "EXPIRY_ALERTS",
    "FALLBACK"
]

class IntentResponse(BaseModel):
    operation: str
    filters: Dict[str, Any]

class FormattedResponse(BaseModel):
    type: str
    title: str
    columns: Optional[List[str]] = None
    data: Optional[List[Dict[str, Any]]] = None
    summary: Optional[str] = None
    chart: Optional[Dict[str, List[Any]]] = None

def fast_match(query: str) -> Optional[Dict[str, Any]]:
    q = query.lower()
    if "low stock" in q or "running low" in q:
        return {"operation": "LOW_STOCK", "filters": {}}
    if "top selling" in q or "top products" in q:
        return {"operation": "TOP_PRODUCTS", "filters": {}}
    if "expiring" in q or "expiry" in q:
        return {"operation": "EXPIRY_ALERTS", "filters": {}}
    if "bought together" in q or "association" in q:
        return {"operation": "ASSOCIATION_ANALYSIS", "filters": {}}
    if "sales summary" in q or "sales" in q:
        return {"operation": "SALES_SUMMARY", "filters": {}}
    if "top performing store" in q or "store comparison" in q:
        return {"operation": "STORE_COMPARISON", "filters": {}}
    return None

async def call_llm(prompt: str) -> str:
    if not ACTIVE_API_KEY:
        raise ValueError("No valid AI API KEY configured in environment")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                ACTIVE_LLM_ENDPOINT,
                headers={"Authorization": f"Bearer {ACTIVE_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": ACTIVE_LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2048
                }
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.exception("LLM API failure:")
        return "{}"

async def parse_query_llm(query: str) -> Dict[str, Any]:
    prompt = f"""
    Convert user query into JSON.
    Allowed operations: {OPERATIONS}
    Return ONLY valid JSON matching this schema:
    {{
      "operation": "...",
      "filters": {{}}
    }}
    Query: {query}
    """
    raw = await call_llm(prompt)
    try:
        cleaned = raw.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        parsed = json.loads(cleaned)
        validated = IntentResponse(**parsed)
        return validated.model_dump()
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Intent Validation failed: {e}")
        return {"operation": "FALLBACK", "filters": {}}

def validate(intent: Dict[str, Any]):
    if intent.get("operation") not in OPERATIONS:
        intent["operation"] = "FALLBACK"

def apply_scope(intent: Dict[str, Any], user):
    if user.role != "ADMIN":
        if "filters" not in intent or not intent["filters"]:
            intent["filters"] = {}
        # Secure enforce JWT store isolation 
        intent["filters"]["store_id"] = str(user.store_id) if user.store_id else None

# -------------- DB TOOLS --------------

def get_low_stock(db: Session, store_id=None, **kwargs):
    q = select(Inventory).where(Inventory.quantity <= Inventory.reorder_threshold)
    if store_id:
        q = q.where(Inventory.store_id == store_id)
    invs = db.scalars(q.limit(10)).all()
    res = []
    for inv in invs:
        p = db.scalar(select(Product).where(Product.id == inv.product_id))
        s = db.scalar(select(Store).where(Store.id == inv.store_id))
        res.append({"product": p.name if p else "Unknown", "quantity": inv.quantity, "store": s.name if s else ""})
    return res

def get_top_products(db: Session, store_id=None, **kwargs):
    q = select(OrderItem.product_id, func.sum(OrderItem.quantity).label('qty_sold'))
    if store_id:
        q = q.join(Order).where(Order.store_id == str(store_id))
    q = q.group_by(OrderItem.product_id).order_by(desc('qty_sold')).limit(10)
    results = db.execute(q).all()
    out = []
    for r in results:
        p = db.scalar(select(Product).where(Product.id == r[0]))
        out.append({"product": p.name if p else str(r[0]), "quantity_sold": r[1]})
    return out

def get_sales_summary(db: Session, store_id=None, **kwargs):
    q = select(func.sum(Order.total_amount).label('total'))
    if store_id:
        q = q.where(Order.store_id == str(store_id))
    total = db.scalar(q) or 0
    return [{"total_sales": float(total)}]

def get_store_performance(db: Session, **kwargs): 
    # Global implicitly grouping 
    q = select(Store.name, func.sum(Order.total_amount).label('total')).join(Order).group_by(Store.name).order_by(desc('total')).limit(10)
    return [{"store": r[0], "total_revenue": float(r[1])} for r in db.execute(q).all()]

def get_association_analysis(db: Session, **kwargs):
    return [{"message": "Bought together simulation: Paracetamol + Vitamin C"}]

def get_forecast(db: Session, **kwargs):
    return [{"message": "Forecast simulation: Expected 20% spike in allergy medicine"}]

def get_expiry_alerts(db: Session, store_id=None, **kwargs):
    return [{"message": "Expiring alerts simulation active"}]

def fallback_data():
    return [{"message": "I couldn't understand that query or it operates on classified multi-tenant scopes you don't possess."}]

TOOLS = {
    "LOW_STOCK": get_low_stock,
    "TOP_PRODUCTS": get_top_products,
    "SALES_SUMMARY": get_sales_summary,
    "STORE_COMPARISON": get_store_performance,
    "ASSOCIATION_ANALYSIS": get_association_analysis,
    "FORECAST": get_forecast,
    "EXPIRY_ALERTS": get_expiry_alerts
}

def execute_intent(intent: Dict[str, Any], db: Session):
    op = intent["operation"]
    if op in TOOLS:
        try:
            return TOOLS[op](db=db, **intent.get("filters", {}))
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return fallback_data()
    return fallback_data()

def compress(data: List[Any]) -> List[Any]:
    if isinstance(data, list):
        return data[:10]
    return data

async def format_response(query: str, data: Any) -> Dict[str, Any]:
    prompt = f"""
    Convert into structured JSON. Format:
    {{
      "type": "table | card | chart",
      "title": "...",
      "columns": [],
      "data": [],
      "summary": "...",
      "chart": {{
        "x": [],
        "y": []
      }}
    }}
    Rules:
    - ALWAYS return valid JSON
    - table -> use data array mapping key-value dicts
    - card -> use summary field
    - chart -> trends in chart field
    - NEVER return plain text
    Query: {query}
    Data: {data}
    """
    raw = await call_llm(prompt)
    logger.info(f"RAW LLM FORMAT: {raw}")
    try:
        cleaned = raw.replace('```json', '').replace('```', '').strip()
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        parsed = json.loads(cleaned)
        validated = FormattedResponse(**parsed)
        return validated.model_dump()
    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Format Validation failed: {e}")
        return {
            "type": "card",
            "title": "Error generating response",
            "summary": "Could not format the response properly."
        }

async def ai_pipeline(query: str, user, db: Session) -> Dict[str, Any]:
    logger.info(f"USER: {user.username} | OP: TRIGGER | TS: {datetime.now().isoformat()} | QUERY: {query}")
    intent = fast_match(query)
    if not intent:
        intent = await parse_query_llm(query)
    validate(intent)
    logger.info(f"USER: {user.username} | OP: {intent['operation']} | TS: {datetime.now().isoformat()}")
    apply_scope(intent, user)
    if intent["operation"] == "FALLBACK":
        data = fallback_data()
    else:
        data = execute_intent(intent, db)
    data = compress(data)
    response = await format_response(query, data)
    return response
