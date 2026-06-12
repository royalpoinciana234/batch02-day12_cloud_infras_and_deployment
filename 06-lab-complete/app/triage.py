import logging
import json
from app import openrouter_client as llm
from app import prompts
from app.longchau_search import search_products
from app.safety_gate import is_high_risk, is_injection

logger = logging.getLogger(__name__)


def log_handoff(message: str, history: list[dict], summary: str, pharmacist: str, safety_triggered: bool):
    logger.info(json.dumps({
        "event": "handoff",
        "message": message[:200],
        "summary": summary,
        "pharmacist": pharmacist,
        "safety_triggered": safety_triggered
    }))




def _format_product_links(products: list[dict]) -> str:
    if not products:
        return ""
    lines = ["\n\n---\n🛒 **Sản phẩm tại Long Châu:**"]
    for p in products:
        lines.append(f"• [{p['name']}]({p['url']}) — {p['price']}")
    return "\n".join(lines)


async def triage(message: str, history: list[dict]) -> dict:
    model_name = llm.get_model_name()

    # 0. Injection detected: don't block — let LLM handle via _ANTI_INJECTION in system prompts.
    # The system prompt already instructs the model to ignore off-topic parts and only answer
    # the pharmacy-relevant portion. Blocking here would also reject legitimate drug questions
    # that happen to contain injection patterns (e.g. "bromhexin info AND write python code").
    injection_detected = is_injection(message)
    _ = injection_detected  # reserved for future logging/metrics

    # 1. Safety gate — always runs first, overrides classifier
    if is_high_risk(message):
        try:
            summary_messages = [
                {"role": "system", "content": prompts.HANDOFF_SUMMARY_SYSTEM},
                *history,
                {"role": "user", "content": message},
            ]
            handoff_summary = await llm.chat(summary_messages)
        except Exception:
            handoff_summary = f"Khách hỏi: {message[:200]}. Cần tư vấn chuyên sâu."

        log_handoff(message, history, handoff_summary, pharmacist="", safety_triggered=True)
        return {
            "route": "advisory_handoff",
            "reply": "⚠️ Câu hỏi của bạn liên quan đến tình trạng sức khoẻ cụ thể và cần được tư vấn bởi chuyên gia.\n\nĐang chuyển cho **dược sĩ** hỗ trợ bạn ngay.",
            "handoff_summary": handoff_summary,
            "safety_gate_triggered": True,
            "model": model_name,
        }

    # 2. Classify
    try:
        classify_messages = [
            {"role": "system", "content": prompts.CLASSIFIER_SYSTEM},
            *history,
            {"role": "user", "content": message},
        ]
        classification = await llm.chat_json(classify_messages)
        question_type = classification.get("type", "advisory")
        needs_context = classification.get("needs_context", True)
        drug_keyword = classification.get("drug_keyword") or None
        is_dangerous = classification.get("is_dangerous", False)
        show_products = classification.get("show_products", True)
    except Exception:
        # Fail safe: unknown → advisory
        question_type = "advisory"
        needs_context = True
        drug_keyword = None
        is_dangerous = False
        show_products = True

    # 2b. Out of scope — refuse without LLM answer
    if question_type == "out_of_scope":
        if is_dangerous:
            reply = (
                "⚠️ Câu hỏi này nằm ngoài phạm vi tư vấn dược phẩm và có thể liên quan đến tình huống khẩn cấp.\n\n"
                "Vui lòng liên hệ ngay:\n"
                "• **Cấp cứu:** 115\n"
                "• **Trung tâm y tế hoặc bệnh viện gần nhất**\n\n"
                "Tôi không thể cung cấp thông tin này."
            )
        else:
            reply = "Xin lỗi, câu hỏi này nằm ngoài phạm vi tư vấn dược phẩm của tôi. Tôi chỉ hỗ trợ các câu hỏi liên quan đến thuốc và sức khoẻ."
        return {
            "route": "out_of_scope",
            "reply": reply,
            "handoff_summary": None,
            "safety_gate_triggered": False,
            "model": model_name,
        }

    # 3a. Factual → answer + product links in parallel (only when a drug keyword exists)
    if question_type == "factual":
        import asyncio

        answer_messages = [
            {"role": "system", "content": prompts.FACTUAL_ANSWER_SYSTEM},
            *history,
            {"role": "user", "content": message},
        ]

        if drug_keyword and show_products:
            results = await asyncio.gather(
                llm.chat(answer_messages),
                search_products(drug_keyword, max_results=3),
                return_exceptions=True,
            )
            reply = results[0] if not isinstance(results[0], Exception) else None
            products = results[1] if not isinstance(results[1], Exception) else []
            if reply is None:
                # LLM failed but search may have succeeded — show products with fallback text
                reply = "Xin lỗi, không thể tải thông tin lúc này. Vui lòng thử lại hoặc hỏi dược sĩ trực tiếp."
        else:
            try:
                reply = await llm.chat(answer_messages)
            except Exception:
                reply = "Xin lỗi, không thể tải thông tin lúc này. Vui lòng thử lại hoặc hỏi dược sĩ trực tiếp."
            products = []

        product_md = _format_product_links(products)
        return {
            "route": "factual",
            # reply_md: for text-based UIs (Streamlit) that render markdown
            # reply: clean text for widget (uses structured `products` field)
            "reply": reply,
            "reply_md": reply + product_md,
            "products": products,
            "handoff_summary": None,
            "safety_gate_triggered": False,
            "model": model_name,
        }

    # 3b. Advisory + needs context → ask follow-up
    if needs_context:
        try:
            gather_messages = [
                {"role": "system", "content": prompts.GATHER_CONTEXT_SYSTEM},
                *history,
                {"role": "user", "content": message},
            ]
            reply = await llm.chat(gather_messages)
        except Exception:
            reply = "Để tư vấn chính xác hơn, bạn có thể cho tôi biết bạn đang điều trị bệnh gì và có đang dùng thuốc nào khác không?"

        return {
            "route": "advisory_gather",
            "reply": reply,
            "handoff_summary": None,
            "safety_gate_triggered": False,
            "model": model_name,
        }

    # 3c. Advisory + enough context → handoff summary
    try:
        summary_messages = [
            {"role": "system", "content": prompts.HANDOFF_SUMMARY_SYSTEM},
            *history,
            {"role": "user", "content": message},
        ]
        handoff_summary = await llm.chat(summary_messages)
    except Exception:
        handoff_summary = f"Khách hỏi: {message[:200]}. Cần tư vấn chuyên sâu."

    log_handoff(message, history, handoff_summary, pharmacist="", safety_triggered=False)
    return {
        "route": "advisory_handoff",
        "reply": "Cảm ơn bạn đã cung cấp thông tin. Đang chuyển cho **dược sĩ** tư vấn chi tiết cho bạn.",
        "handoff_summary": handoff_summary,
        "safety_gate_triggered": False,
        "model": model_name,
    }
