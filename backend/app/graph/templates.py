"""Answer text templates (en / hi / hn). Filled only with verified data."""

from __future__ import annotations

from app.data.models import Lang

T: dict[str, dict[Lang, str]] = {
    "status.understand": {
        "en": "Understanding your question",
        "hi": "आपका सवाल समझ रहे हैं",
        "hn": "Aapka sawaal samajh rahe hain",
    },
    "status.search": {
        "en": "Searching verified services",
        "hi": "सत्यापित सेवाएँ खोज रहे हैं",
        "hn": "Verified services dhoondh rahe hain",
    },
    "status.eligibility": {
        "en": "Checking eligibility",
        "hi": "पात्रता जाँच रहे हैं",
        "hn": "Eligibility check kar rahe hain",
    },
    "answer.found": {
        "en": "Here is what I found for {name}. {summary}",
        "hi": "{name} के बारे में यह जानकारी मिली। {summary}",
        "hn": "{name} ke baare mein yeh mila. {summary}",
    },
    "verdict.likely": {
        "en": "Based on what you confirmed, you meet the listed conditions. This is not an approval.",
        "hi": "आपकी पुष्टि की गई जानकारी के अनुसार आप बताई गई शर्तें पूरी करते हैं। यह मंज़ूरी नहीं है।",
        "hn": "Aapne jo confirm kiya uske hisaab se aap listed conditions poori karte hain. Yeh approval nahi hai.",
    },
    "verdict.not_eligible": {
        "en": "Based on what you confirmed, one of the conditions is not met. See the card for the reason.",
        "hi": "आपकी पुष्टि की गई जानकारी के अनुसार एक शर्त पूरी नहीं होती। कारण कार्ड में देखें।",
        "hn": "Aapne jo confirm kiya uske hisaab se ek condition poori nahi hoti. Reason card mein dekhein.",
    },
    "verdict.incomplete": {
        "en": "I need a few details from you before I can check eligibility.",
        "hi": "पात्रता जाँचने से पहले मुझे आपसे कुछ जानकारी चाहिए।",
        "hn": "Eligibility check karne se pehle mujhe aapse kuch details chahiye.",
    },
    "verify_locally_note": {
        "en": "Fees and processing time are not verified yet, so please verify them locally.",
        "hi": "फ़ीस और समय अभी सत्यापित नहीं हैं, कृपया स्थानीय रूप से पुष्टि करें।",
        "hn": "Fees aur processing time abhi verified nahi hain, please locally verify karein.",
    },
    "refusal.no_source": {
        "en": "I don't have verified information on that yet. Right now I can help with the Delhi income certificate.",
        "hi": "इसकी सत्यापित जानकारी अभी मेरे पास नहीं है। अभी मैं दिल्ली आय प्रमाण पत्र में मदद कर सकता हूँ।",
        "hn": "Iski verified jaankari abhi mere paas nahi hai. Abhi main Delhi income certificate mein madad kar sakta hoon.",
    },
    "chip.confirm.state_of_residence": {
        "en": "Yes, I live in {value}",
        "hi": "हाँ, मैं {value} में रहता/रहती हूँ",
        "hn": "Haan, main {value} mein rehta/rehti hoon",
    },
    "chip.ask.state_of_residence": {
        "en": "I live in Delhi",
        "hi": "मैं दिल्ली में रहता/रहती हूँ",
        "hn": "Main Delhi mein rehta/rehti hoon",
    },
    "chip.ask.state_other": {
        "en": "I live outside Delhi",
        "hi": "मैं दिल्ली से बाहर रहता/रहती हूँ",
        "hn": "Main Delhi se bahar rehta/rehti hoon",
    },
}


def t(key: str, lang: Lang, **kwargs: object) -> str:
    entry = T[key]
    return (entry.get(lang) or entry["en"]).format(**kwargs)
