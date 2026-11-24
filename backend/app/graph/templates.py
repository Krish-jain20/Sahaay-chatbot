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
        "en": "Some fees or times are not on the official pages, so please verify them locally.",
        "hi": "कुछ फ़ीस या समय आधिकारिक पेज पर नहीं हैं, कृपया स्थानीय रूप से पुष्टि करें।",
        "hn": "Kuch fees ya time official pages par nahi hain, please locally verify karein.",
    },
    "refusal.no_source": {
        "en": "I don't have verified information on that yet. Right now I can help with three Delhi services: income certificate, the SC/ST/OBC merit scholarship and old-age pension.",
        "hi": "इसकी सत्यापित जानकारी अभी मेरे पास नहीं है। अभी मैं दिल्ली की तीन सेवाओं में मदद कर सकता हूँ: आय प्रमाण पत्र, SC/ST/OBC मेरिट छात्रवृत्ति और वृद्धावस्था पेंशन।",
        "hn": "Iski verified jaankari abhi mere paas nahi hai. Abhi main Delhi ki teen services mein madad kar sakta hoon: income certificate, SC/ST/OBC merit scholarship aur old-age pension.",
    },
    "guard.blocked": {
        "en": "I can't give that answer safely. Please check the official page for this service.",
        "hi": "मैं यह उत्तर सुरक्षित रूप से नहीं दे सकता। कृपया इस सेवा का आधिकारिक पेज देखें।",
        "hn": "Main yeh jawaab safely nahi de sakta. Please is service ka official page dekhein.",
    },
    "error.busy": {
        "en": "I'm getting too many requests right now. Please try again in a minute.",
        "hi": "अभी बहुत ज़्यादा अनुरोध आ रहे हैं। कृपया एक मिनट बाद फिर कोशिश करें।",
        "hn": "Abhi bahut zyada requests aa rahi hain. Please ek minute baad try karein.",
    },
    "prereq.note": {
        "en": "You may need this first: {names}.",
        "hi": "पहले इसकी ज़रूरत हो सकती है: {names}।",
        "hn": "Pehle iski zaroorat ho sakti hai: {names}.",
    },
    "chip.confirm_said": {
        "en": "Yes, that's right: {facts}",
        "hi": "हाँ, यह सही है: {facts}",
        "hn": "Haan, yeh sahi hai: {facts}",
    },
    "opt.state.delhi": {
        "en": "I live in Delhi",
        "hi": "मैं दिल्ली में रहता/रहती हूँ",
        "hn": "Main Delhi mein rehta/rehti hoon",
    },
    "opt.state.other": {
        "en": "I live outside Delhi",
        "hi": "मैं दिल्ली से बाहर रहता/रहती हूँ",
        "hn": "Main Delhi se bahar rehta/rehti hoon",
    },
    "opt.cat.sc": {"en": "SC", "hi": "SC", "hn": "SC"},
    "opt.cat.st": {"en": "ST", "hi": "ST", "hn": "ST"},
    "opt.cat.obc": {"en": "OBC", "hi": "OBC", "hn": "OBC"},
    "opt.cat.general": {"en": "General / other", "hi": "सामान्य / अन्य", "hn": "General / other"},
    "opt.occ.student": {
        "en": "I'm a college student",
        "hi": "मैं कॉलेज में पढ़ता/पढ़ती हूँ",
        "hn": "Main college mein padhta/padhti hoon",
    },
    "opt.occ.other": {"en": "I'm not a student", "hi": "मैं छात्र नहीं हूँ", "hn": "Main student nahi hoon"},
    "opt.age.60": {"en": "Age 60 to 69", "hi": "उम्र 60 से 69", "hn": "Umar 60 se 69"},
    "opt.age.70": {"en": "Age 70 or more", "hi": "उम्र 70 या ज़्यादा", "hn": "Umar 70 ya zyada"},
    "opt.age.under": {"en": "Under 60", "hi": "60 से कम", "hn": "60 se kam"},
    "opt.res.5": {"en": "In Delhi 5+ years", "hi": "दिल्ली में 5+ साल से", "hn": "Delhi mein 5+ saal se"},
    "opt.res.less": {"en": "Less than 5 years", "hi": "5 साल से कम", "hn": "5 saal se kam"},
    "opt.inc.1": {"en": "Income below ₹1 lakh", "hi": "आय ₹1 लाख से कम", "hn": "Income ₹1 lakh se kam"},
    "opt.inc.3": {"en": "₹1 to 3 lakh", "hi": "₹1 से 3 लाख", "hn": "₹1 se 3 lakh"},
    "opt.inc.more": {"en": "Above ₹3 lakh", "hi": "₹3 लाख से ज़्यादा", "hn": "₹3 lakh se zyada"},
    "opt.marks.60": {
        "en": "60% or more last year",
        "hi": "पिछले साल 60% या ज़्यादा",
        "hn": "Pichhle saal 60% ya zyada",
    },
    "opt.marks.less": {"en": "Below 60%", "hi": "60% से कम", "hn": "60% se kam"},
    "opt.bank.yes": {
        "en": "Yes, Aadhaar-linked bank account",
        "hi": "हाँ, आधार से जुड़ा बैंक खाता है",
        "hn": "Haan, Aadhaar se juda bank account hai",
    },
    "opt.bank.no": {"en": "No linked account", "hi": "जुड़ा खाता नहीं है", "hn": "Linked account nahi hai"},
}


def t(key: str, lang: Lang, **kwargs: object) -> str:
    entry = T[key]
    return (entry.get(lang) or entry["en"]).format(**kwargs)
