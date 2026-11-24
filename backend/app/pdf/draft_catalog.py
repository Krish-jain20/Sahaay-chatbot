"""Catalog of draft types: fields, wording and grouping. Pure data, no I/O.

Each draft type is a list of fields plus the sentences that frame them. The same catalog drives the
cards on the Drafts page (`GET /drafts/catalog`), validation, the review step and the PDF, so the
frontend never keeps its own copy of the fields.

Rules kept here:
- No fee, deadline, address or section number is filled in for the user. Where a draft names an
  official portal it is only the host, and every host must be in data/allowlist.json (tested).
- Wording says what the user asks for, never what the outcome will be.
- Hinglish (`hn`) cards use Latin-script text. The letter itself is written in English or Hindi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

FieldType = Literal["text", "multiline", "date", "checkbox", "choice"]
Style = Literal["letter", "rti", "portal"]


@dataclass(frozen=True)
class L:
    """A string in English, Hindi and (optionally) Hinglish. Missing Hinglish falls back to English."""

    en: str
    hi: str
    hn: str | None = None

    def get(self, lang: str) -> str:
        if lang == "hi":
            return self.hi
        if lang == "hn":
            return self.hn or self.en
        return self.en


@dataclass(frozen=True)
class FieldDef:
    key: str
    type: FieldType
    label: L
    hint: L | None = None
    options: tuple[tuple[str, L], ...] = ()


@dataclass(frozen=True)
class FieldRef:
    key: str
    required: bool = False

    @property
    def spec(self) -> FieldDef:
        return FIELDS[self.key]


@dataclass(frozen=True)
class DraftKind:
    id: str
    group: str
    icon: str
    style: Style
    title: L
    blurb: L  # one line on the card: when to use it
    subject: L  # subject line of the letter (the title when same)
    fields: tuple[FieldRef, ...]
    to_key: str | None = None  # which field holds the addressee
    intro: L | None = None
    closing: L | None = None
    enclose: L | None = None  # "keep ready to attach" line, shown in review and in the PDF
    portal_host: str | None = None  # official portal host to mention, must be in the allowlist
    tags: tuple[str, ...] = ()  # extra search words (English)
    pdf_name: str = ""
    extras: dict[str, str] = field(default_factory=dict)

    @property
    def required_keys(self) -> list[str]:
        return [f.key for f in self.fields if f.required]


GROUPS: tuple[tuple[str, L], ...] = (
    ("services", L("Delayed or refused service", "सेवा में देरी या इनकार", "Service mein deri ya inkaar")),
    ("rti", L("Right to Information", "सूचना का अधिकार", "Right to Information (RTI)")),
    ("grievance", L("Grievance portals", "शिकायत पोर्टल", "Grievance portal")),
    ("bills", L("Bills and consumers", "बिल और उपभोक्ता", "Bill aur consumer")),
    ("safety", L("Police and fraud", "पुलिस और धोखाधड़ी", "Police aur fraud")),
    ("city", L("City, school and rations", "शहर, स्कूल और राशन", "Sheher, school aur ration")),
)


def _o(key: str, en: str, hi: str) -> tuple[str, L]:
    return key, L(en, hi)


FIELDS: dict[str, FieldDef] = {
    f.key: f
    for f in [
        FieldDef("full_name", "text", L("Your name", "आपका नाम")),
        FieldDef("address", "multiline", L("Your address", "आपका पता")),
        FieldDef(
            "contact",
            "text",
            L("Phone or email", "फ़ोन या ईमेल"),
            L("Only the last 4 digits of a phone number are kept.", "फ़ोन नंबर के केवल अंतिम 4 अंक रखे जाते हैं।"),
        ),
        FieldDef("addressed_to", "text", L("Addressed to (officer or office)", "किसे संबोधित (अधिकारी या कार्यालय)")),
        FieldDef("service_name", "text", L("Service", "सेवा")),
        FieldDef("application_ref", "text", L("Application reference number", "आवेदन संदर्भ संख्या")),
        FieldDef("applied_on", "date", L("Applied on (date)", "आवेदन की तारीख")),
        FieldDef("issue", "multiline", L("What happened", "क्या हुआ")),
        FieldDef("requested_action", "multiline", L("What you are asking for", "आपका अनुरोध")),
        # RTI
        FieldDef("authority", "text", L("Public authority (office you are asking)", "लोक प्राधिकरण (जिस कार्यालय से पूछ रहे हैं)")),
        FieldDef("info_sought", "multiline", L("Information you want", "आप कौन-सी जानकारी चाहते हैं")),
        FieldDef("period", "text", L("Period", "अवधि")),
        FieldDef("bpl", "checkbox", L("I am a Below Poverty Line applicant", "मैं गरीबी रेखा से नीचे (BPL) आवेदक हूँ")),
        FieldDef("department", "text", L("Ministry or department", "मंत्रालय या विभाग")),
        FieldDef("grievance", "multiline", L("Your grievance", "आपकी शिकायत")),
        # RTI first appeal
        FieldDef("rti_filed_on", "date", L("Date you filed the RTI application", "आरटीआई आवेदन की तारीख")),
        FieldDef("rti_ref", "text", L("RTI registration number (if any)", "आरटीआई पंजीकरण संख्या (यदि हो)")),
        FieldDef("pio_office", "text", L("Office of the PIO who answered (or did not)", "जन सूचना अधिकारी का कार्यालय")),
        FieldDef(
            "appeal_ground",
            "choice",
            L("Why are you appealing", "आप अपील क्यों कर रहे हैं"),
            options=(
                _o("no_reply", "I got no reply", "कोई जवाब नहीं मिला"),
                _o("refused", "The information was refused", "जानकारी देने से मना किया गया"),
                _o("incomplete", "The reply was incomplete or wrong", "जवाब अधूरा या गलत था"),
            ),
        ),
        # Certificates, scholarship, pension
        FieldDef(
            "certificate_type",
            "choice",
            L("Certificate", "प्रमाणपत्र"),
            options=(
                _o("income", "Income certificate", "आय प्रमाणपत्र"),
                _o("caste", "Caste certificate (SC / ST / OBC)", "जाति प्रमाणपत्र (SC / ST / OBC)"),
                _o("domicile", "Domicile or residence certificate", "अधिवास या निवास प्रमाणपत्र"),
                _o("other", "Other certificate", "अन्य प्रमाणपत्र"),
            ),
        ),
        FieldDef("scheme_name", "text", L("Scholarship name", "छात्रवृत्ति का नाम")),
        FieldDef("institution", "text", L("School, college or institute", "स्कूल, कॉलेज या संस्थान")),
        FieldDef("academic_year", "text", L("Academic year (for example 2025-26)", "शैक्षणिक वर्ष (जैसे 2025-26)")),
        FieldDef("pension_scheme", "text", L("Pension scheme", "पेंशन योजना")),
        FieldDef("pension_ref", "text", L("Pension reference (last 4 shown)", "पेंशन संदर्भ (अंतिम 4 अंक)")),
        FieldDef("last_received", "date", L("Last month paid (any date in it)", "आखिरी बार पेंशन मिलने की तारीख")),
        # Ration
        FieldDef(
            "ration_issue",
            "choice",
            L("What is the problem", "समस्या क्या है"),
            options=(
                _o("new_card", "New ration card not issued", "नया राशन कार्ड नहीं बना"),
                _o("name_missing", "A family member's name is missing", "परिवार के सदस्य का नाम नहीं जुड़ा"),
                _o("not_received", "Rations are not being given", "राशन नहीं मिल रहा"),
                _o("correction", "A detail on the card is wrong", "कार्ड में कोई जानकारी गलत है"),
            ),
        ),
        FieldDef("ration_card_no", "text", L("Ration card number (if you have one)", "राशन कार्ड नंबर (यदि हो)")),
        FieldDef("fps_name", "text", L("Fair price shop name or area", "उचित मूल्य दुकान का नाम या इलाका")),
        # Bills
        FieldDef("utility_company", "text", L("Company or office that sent the bill", "बिल भेजने वाली कंपनी या कार्यालय")),
        FieldDef("consumer_no", "text", L("Consumer or CA number (last 4 shown)", "उपभोक्ता या CA नंबर (अंतिम 4 अंक)")),
        FieldDef("bill_date", "date", L("Bill date", "बिल की तारीख")),
        FieldDef("disputed_amount", "text", L("Amount you dispute", "विवादित राशि")),
        FieldDef(
            "bill_issue",
            "choice",
            L("What is wrong with the bill", "बिल में क्या गलत है"),
            options=(
                _o("too_high", "The amount is far higher than usual", "राशि सामान्य से बहुत अधिक है"),
                _o("meter", "Meter is faulty or reading is wrong", "मीटर खराब है या रीडिंग गलत है"),
                _o("not_received", "I did not get a bill", "बिल नहीं मिला"),
                _o("disconnection", "Wrongly threatened with disconnection", "गलत तरीके से कनेक्शन काटने की चेतावनी"),
            ),
        ),
        FieldDef("seller", "text", L("Seller, company or platform", "विक्रेता, कंपनी या प्लेटफ़ॉर्म")),
        FieldDef("order_ref", "text", L("Order or invoice number", "ऑर्डर या बिल संख्या")),
        FieldDef("purchase_date", "date", L("Date of purchase", "खरीद की तारीख")),
        FieldDef("amount_paid", "text", L("Amount paid", "चुकाई गई राशि")),
        FieldDef("contacted_before", "checkbox", L("I already wrote to them and got no fix", "मैं पहले लिख चुका/चुकी हूँ और समाधान नहीं मिला")),
        # Police and fraud
        FieldDef("police_station", "text", L("Police station", "थाना")),
        FieldDef(
            "police_request",
            "choice",
            L("What do you need", "आपको क्या चाहिए"),
            options=(
                _o("register", "Register my complaint (FIR)", "मेरी शिकायत दर्ज करें (FIR)"),
                _o("copy", "A copy of my FIR", "मेरी FIR की प्रति"),
                _o("action", "Action on my earlier complaint", "पहले की शिकायत पर कार्रवाई"),
            ),
        ),
        FieldDef("incident_date", "date", L("Date it happened", "घटना की तारीख")),
        FieldDef("incident_place", "text", L("Place it happened", "घटना का स्थान")),
        FieldDef("earlier_ref", "text", L("Earlier complaint or FIR number (if any)", "पहले की शिकायत या FIR संख्या (यदि हो)")),
        FieldDef("bank_name", "text", L("Your bank or wallet", "आपका बैंक या वॉलेट")),
        FieldDef("amount_lost", "text", L("Amount lost", "गँवाई गई राशि")),
        FieldDef("txn_ref", "text", L("Transaction or UTR reference (last 4 shown)", "लेन-देन या UTR संदर्भ (अंतिम 4 अंक)")),
        FieldDef("reported_portal", "checkbox", L("I have already reported it on the cyber crime portal or helpline", "मैंने साइबर क्राइम पोर्टल या हेल्पलाइन पर रिपोर्ट कर दी है")),
        # City, school
        FieldDef(
            "city_issue",
            "choice",
            L("Type of problem", "समस्या का प्रकार"),
            options=(
                _o("garbage", "Garbage not picked up", "कचरा नहीं उठाया जा रहा"),
                _o("drain", "Blocked drain or waterlogging", "नाली जाम या जलभराव"),
                _o("road", "Broken road or pothole", "टूटी सड़क या गड्ढा"),
                _o("light", "Street light not working", "स्ट्रीट लाइट खराब"),
                _o("other", "Other civic problem", "अन्य नागरिक समस्या"),
            ),
        ),
        FieldDef("location", "text", L("Exact location (street, landmark, area)", "सही जगह (गली, लैंडमार्क, इलाका)")),
        FieldDef("since", "date", L("Problem present since", "समस्या कब से है")),
        FieldDef("child_name", "text", L("Child's name", "बच्चे का नाम")),
        FieldDef("class_sought", "text", L("Class sought", "किस कक्षा में प्रवेश")),
        FieldDef("school_name", "text", L("School", "स्कूल")),
        FieldDef(
            "school_issue",
            "choice",
            L("What happened", "क्या हुआ"),
            options=(
                _o("refused", "School refused admission", "स्कूल ने प्रवेश से मना किया"),
                _o("documents", "School asked for documents not required", "स्कूल ने गैर-ज़रूरी कागज़ माँगे"),
                _o("no_response", "No response to my application", "आवेदन का कोई जवाब नहीं"),
            ),
        ),
    ]
}


def _r(*keys: str) -> tuple[FieldRef, ...]:
    """'key' is optional, 'key!' is required."""
    return tuple(FieldRef(k.rstrip("!"), k.endswith("!")) for k in keys)


KINDS: tuple[DraftKind, ...] = (
    # ---- Delayed or refused service -------------------------------------------------------
    DraftKind(
        "complaint", "services", "pen", "letter",
        L("Complaint about a delayed or refused service", "सेवा में देरी या इनकार की शिकायत", "Deri ya inkaar ki shikayat"),
        L("Any service that is late, refused or stuck without a reason.", "कोई भी सेवा जो देर से, रुकी हुई या बिना कारण मना की गई हो।", "Koi bhi service jo late ya bina wajah ruki ho."),
        L("Complaint about a delay or refusal of a service", "सेवा में देरी या इनकार के बारे में शिकायत"),
        _r("full_name!", "address", "contact", "addressed_to!", "service_name!", "application_ref", "applied_on", "issue!", "requested_action!"),
        "addressed_to",
        L("I am writing about the service named below.", "मैं नीचे बताई गई सेवा के संबंध में लिख रहा/रही हूँ।"),
        enclose=L("Copy of your application and its acknowledgement.", "आवेदन और उसकी पावती की प्रति।"),
        tags=("delay", "refused", "general"),
    ),
    DraftKind(
        "certificate_delay", "services", "file", "letter",
        L("Certificate not issued", "प्रमाणपत्र जारी नहीं हुआ", "Certificate nahi mila"),
        L("Income, caste or domicile certificate pending or rejected.", "आय, जाति या अधिवास प्रमाणपत्र लंबित या अस्वीकृत।", "Income, caste ya domicile certificate pending ya reject."),
        L("Complaint: certificate not issued or rejected without reason", "शिकायत: प्रमाणपत्र जारी नहीं हुआ या बिना कारण अस्वीकृत"),
        _r("full_name!", "address", "contact", "addressed_to!", "certificate_type!", "application_ref", "applied_on", "issue!", "requested_action!"),
        "addressed_to",
        L("I applied for the certificate named below and I am writing because it has not been issued.", "मैंने नीचे बताए प्रमाणपत्र के लिए आवेदन किया था और वह अब तक जारी नहीं हुआ, इसलिए लिख रहा/रही हूँ।"),
        L("I request you to look into my application and tell me in writing the reason if it cannot be issued.", "कृपया मेरे आवेदन को देखें और यदि जारी नहीं हो सकता तो कारण लिखित में बताएँ।"),
        L("Acknowledgement slip or receipt, and the documents you uploaded.", "पावती पर्ची या रसीद और अपलोड किए कागज़।"),
        "edistrict.delhi.gov.in",
        ("income", "caste", "domicile", "e-district", "sdm"),
    ),
    DraftKind(
        "scholarship_delay", "services", "cap", "letter",
        L("Scholarship not received", "छात्रवृत्ति नहीं मिली", "Scholarship nahi mili"),
        L("Scholarship application stuck, not paid, or rejected.", "छात्रवृत्ति का आवेदन अटका, भुगतान नहीं हुआ या अस्वीकृत।", "Scholarship application atki, paisa nahi aaya ya reject."),
        L("Complaint: scholarship not sanctioned or not paid", "शिकायत: छात्रवृत्ति स्वीकृत या भुगतान नहीं हुई"),
        _r("full_name!", "address", "contact", "addressed_to!", "scheme_name!", "academic_year", "institution", "application_ref", "applied_on", "issue!", "requested_action!"),
        "addressed_to",
        L("I applied for the scholarship named below and have not received a decision or payment.", "मैंने नीचे बताई छात्रवृत्ति के लिए आवेदन किया था और मुझे निर्णय या भुगतान नहीं मिला।"),
        L("I request you to check the status on your side and inform me in writing of the next step.", "कृपया अपनी ओर से स्थिति जाँचें और अगला कदम लिखित में बताएँ।"),
        L("Application acknowledgement, bank passbook first page (last 4 digits only) and income certificate.", "आवेदन की पावती, बैंक पासबुक का पहला पन्ना (केवल अंतिम 4 अंक) और आय प्रमाणपत्र।"),
        "scstwelfare.delhi.gov.in",
        ("scholarship", "student", "stipend", "merit"),
    ),
    DraftKind(
        "pension_delay", "services", "users", "letter",
        L("Pension not paid", "पेंशन नहीं मिली", "Pension nahi mili"),
        L("Old-age, widow or disability pension stopped or never started.", "वृद्धावस्था, विधवा या दिव्यांग पेंशन बंद या शुरू नहीं हुई।", "Old-age, widow ya disability pension band ya shuru nahi hui."),
        L("Complaint: pension not paid or stopped", "शिकायत: पेंशन का भुगतान नहीं हुआ या बंद हो गई"),
        _r("full_name!", "address", "contact", "addressed_to!", "pension_scheme!", "pension_ref", "applied_on", "last_received", "issue!", "requested_action!"),
        "addressed_to",
        L("I am a beneficiary or applicant of the pension named below and I am writing about non-payment.", "मैं नीचे बताई पेंशन का लाभार्थी या आवेदक हूँ और भुगतान न होने के बारे में लिख रहा/रही हूँ।"),
        L("I request you to restart or release the payment, or tell me in writing what is needed from me.", "कृपया भुगतान शुरू या जारी करें, या लिखित में बताएँ कि मुझे क्या करना है।"),
        L("Pension order or ID, Aadhaar-linked bank details (last 4 digits only).", "पेंशन आदेश या आईडी, आधार से जुड़े बैंक विवरण (केवल अंतिम 4 अंक)।"),
        "socialwelfare.delhi.gov.in",
        ("old age", "widow", "disability", "social welfare"),
    ),
    DraftKind(
        "ration_issue", "services", "bag", "letter",
        L("Ration card problem", "राशन कार्ड की समस्या", "Ration card ki problem"),
        L("New card pending, a name missing, wrong details or no rations.", "नया कार्ड लंबित, नाम छूटा, गलत जानकारी या राशन नहीं मिल रहा।", "Naya card pending, naam missing, galat details ya ration nahi mil raha."),
        L("Complaint about a ration card or ration supply", "राशन कार्ड या राशन आपूर्ति के बारे में शिकायत"),
        _r("full_name!", "address!", "contact", "addressed_to!", "ration_issue!", "ration_card_no", "fps_name", "applied_on", "issue!", "requested_action!"),
        "addressed_to",
        L("I am writing about a ration card problem described below.", "मैं नीचे बताई राशन कार्ड की समस्या के बारे में लिख रहा/रही हूँ।"),
        L("I request you to look into this and resolve it, and to tell me in writing if anything more is needed.", "कृपया इसे देखकर हल करें, और कुछ और चाहिए तो लिखित में बताएँ।"),
        L("Copy of the ration card (if any) and family ID proof with numbers hidden.", "राशन कार्ड की प्रति (यदि हो) और परिवार का पहचान प्रमाण, नंबर छिपाकर।"),
        "fsd.delhi.gov.in",
        ("food", "nfsa", "fair price shop", "ration"),
    ),
    # ---- Right to Information -------------------------------------------------------------
    DraftKind(
        "rti", "rti", "scale", "rti",
        L("RTI application", "आरटीआई आवेदन", "RTI application"),
        L("Ask an office for records, reasons or the status of your file.", "किसी कार्यालय से रिकॉर्ड, कारण या फ़ाइल की स्थिति माँगें।", "Kisi office se record, wajah ya file ki sthiti maangein."),
        L("Application under the Right to Information Act, 2005", "सूचना का अधिकार अधिनियम, 2005 के अंतर्गत आवेदन"),
        _r("full_name!", "address!", "authority!", "info_sought!", "period", "bpl"),
        "authority",
        portal_host="rtionline.delhi.gov.in",
        tags=("information", "records", "file status"),
    ),
    DraftKind(
        "rti_first_appeal", "rti", "scale", "letter",
        L("RTI first appeal", "आरटीआई प्रथम अपील", "RTI pehli appeal"),
        L("No reply, a refusal or an incomplete answer to your RTI.", "आरटीआई का जवाब नहीं मिला, इनकार हुआ या अधूरा जवाब मिला।", "RTI ka jawab nahi mila, inkaar hua ya adhura jawab mila."),
        L("First appeal under Section 19(1) of the Right to Information Act, 2005", "सूचना का अधिकार अधिनियम, 2005 की धारा 19(1) के अंतर्गत प्रथम अपील"),
        _r("full_name!", "address!", "addressed_to!", "pio_office!", "rti_filed_on!", "rti_ref", "appeal_ground!", "issue!", "requested_action!"),
        "addressed_to",
        L("I filed an RTI application as described below and I am not satisfied with the response. I appeal to you as the First Appellate Authority.", "मैंने नीचे बताए अनुसार आरटीआई आवेदन दिया था और जवाब से संतुष्ट नहीं हूँ। मैं प्रथम अपीलीय प्राधिकारी के रूप में आपसे अपील करता/करती हूँ।"),
        enclose=L("Copy of your RTI application, proof of posting or submission, and the reply (if any).", "आरटीआई आवेदन की प्रति, भेजने का प्रमाण और जवाब (यदि मिला)।"),
        portal_host="rtionline.delhi.gov.in",
        tags=("appeal", "pio", "no reply"),
    ),
    # ---- Grievance portals ----------------------------------------------------------------
    DraftKind(
        "cpgrams", "grievance", "send", "portal",
        L("Grievance for CPGRAMS", "CPGRAMS के लिए शिकायत", "CPGRAMS ke liye shikayat"),
        L("Write it once here, then paste it into the central grievance portal.", "यहाँ एक बार लिखें, फिर केंद्रीय शिकायत पोर्टल में चिपकाएँ।", "Yahan ek baar likhein, phir central portal mein paste karein."),
        L("Public grievance (draft for the CPGRAMS portal)", "जन शिकायत (CPGRAMS पोर्टल के लिए मसौदा)"),
        _r("full_name!", "contact", "department!", "grievance!", "requested_action!"),
        portal_host="pgportal.gov.in",
        tags=("central", "portal", "pgportal"),
    ),
    DraftKind(
        "delhi_pgc", "grievance", "send", "letter",
        L("Complaint to Delhi grievance body", "दिल्ली शिकायत निकाय को शिकायत", "Delhi grievance body ko shikayat"),
        L("A Delhi government office has not answered your earlier complaint.", "दिल्ली सरकार के कार्यालय ने आपकी पहले की शिकायत का जवाब नहीं दिया।", "Delhi sarkar ke office ne pehli shikayat ka jawab nahi diya."),
        L("Complaint about non-redressal of an earlier grievance", "पहले की शिकायत का निवारण न होने की शिकायत"),
        _r("full_name!", "address!", "contact", "addressed_to!", "department!", "earlier_ref", "applied_on", "issue!", "requested_action!"),
        "addressed_to",
        L("I complained earlier to the office named below and the problem is not resolved.", "मैंने पहले नीचे बताए कार्यालय में शिकायत की थी और समस्या हल नहीं हुई।"),
        enclose=L("Copy of the earlier complaint and any reply.", "पहली शिकायत और जवाब (यदि कोई) की प्रति।"),
        portal_host="pgc.delhi.gov.in",
        tags=("delhi", "pgc", "no action"),
    ),
    # ---- Bills and consumers --------------------------------------------------------------
    DraftKind(
        "electricity_bill", "bills", "bolt", "letter",
        L("Electricity bill dispute", "बिजली बिल विवाद", "Bijli bill ka vivaad"),
        L("Bill too high, meter faulty, or wrong disconnection notice.", "बिल बहुत ज़्यादा, मीटर खराब या गलत कटौती का नोटिस।", "Bill bahut zyada, meter kharab ya galat kaatne ka notice."),
        L("Dispute of an electricity bill", "बिजली बिल पर आपत्ति"),
        _r("full_name!", "address!", "contact", "utility_company!", "consumer_no!", "bill_date", "bill_issue!", "disputed_amount", "issue!", "requested_action!"),
        "utility_company",
        L("I dispute the electricity bill described below.", "मैं नीचे बताए बिजली बिल पर आपत्ति दर्ज करता/करती हूँ।"),
        L("I request a check of the meter and the bill, and a corrected bill in writing.", "कृपया मीटर और बिल की जाँच करें और सही किया हुआ बिल लिखित में दें।"),
        L("The bill, last few bills for comparison and any meter photo.", "यह बिल, तुलना के लिए पिछले कुछ बिल और मीटर की फ़ोटो (यदि हो)।"),
        tags=("power", "meter", "discom", "bses", "tata power"),
    ),
    DraftKind(
        "water_bill", "bills", "drop", "letter",
        L("Water bill dispute", "पानी बिल विवाद", "Paani bill ka vivaad"),
        L("Inflated or wrong water bill, or no bill at all.", "बढ़ा-चढ़ा या गलत पानी का बिल, या बिल ही नहीं आया।", "Zyada ya galat paani ka bill, ya bill hi nahi aaya."),
        L("Dispute of a water bill", "पानी बिल पर आपत्ति"),
        _r("full_name!", "address!", "contact", "utility_company!", "consumer_no!", "bill_date", "bill_issue!", "disputed_amount", "issue!", "requested_action!"),
        "utility_company",
        L("I dispute the water bill described below.", "मैं नीचे बताए पानी के बिल पर आपत्ति दर्ज करता/करती हूँ।"),
        L("I request a check of the meter reading and the bill, and a corrected bill in writing.", "कृपया मीटर रीडिंग और बिल की जाँच करें और सही किया हुआ बिल लिखित में दें।"),
        L("The bill, earlier bills for comparison and any meter photo.", "यह बिल, तुलना के लिए पुराने बिल और मीटर की फ़ोटो (यदि हो)।"),
        tags=("jal board", "djb", "meter"),
    ),
    DraftKind(
        "consumer_notice", "bills", "receipt", "letter",
        L("Consumer complaint to a seller", "विक्रेता को उपभोक्ता शिकायत", "Seller ko consumer shikayat"),
        L("Faulty goods, bad service or a refund you were refused.", "खराब सामान, खराब सेवा या रिफ़ंड से इनकार।", "Kharab saamaan, kharab service ya refund se inkaar."),
        L("Consumer complaint: request for repair, replacement or refund", "उपभोक्ता शिकायत: मरम्मत, बदलाव या रिफ़ंड का अनुरोध"),
        _r("full_name!", "address!", "contact", "seller!", "order_ref", "purchase_date", "amount_paid", "contacted_before", "issue!", "requested_action!"),
        "seller",
        L("I bought the goods or service described below and I am writing to ask you to put things right.", "मैंने नीचे बताया सामान या सेवा ली थी और उसे ठीक करने का अनुरोध करने के लिए लिख रहा/रही हूँ।"),
        L("If this is not resolved I may take the matter to the consumer commission or the national consumer helpline.", "यदि यह हल नहीं हुआ तो मैं उपभोक्ता आयोग या राष्ट्रीय उपभोक्ता हेल्पलाइन के पास जा सकता/सकती हूँ।"),
        L("Invoice or order confirmation, photos of the fault, earlier messages with the seller.", "बिल या ऑर्डर की पुष्टि, खराबी की फ़ोटो, विक्रेता से पुराने संदेश।"),
        tags=("refund", "warranty", "online order", "shop"),
    ),
    # ---- Police and fraud -----------------------------------------------------------------
    DraftKind(
        "police_complaint", "safety", "shield", "letter",
        L("Complaint to the police", "पुलिस को शिकायत", "Police ko shikayat"),
        L("Ask the SHO to register your complaint, give a copy of the FIR or act on it.", "थाना प्रभारी से शिकायत दर्ज करने, FIR की प्रति देने या कार्रवाई करने को कहें।", "SHO se complaint darj karne, FIR ki copy dene ya action lene ko kahein."),
        L("Complaint to the Station House Officer", "थाना प्रभारी को शिकायत"),
        _r("full_name!", "address!", "contact", "police_station!", "police_request!", "incident_date", "incident_place", "earlier_ref", "issue!", "requested_action!"),
        "police_station",
        L("I am writing to the police about the matter described below.", "मैं नीचे बताई घटना के बारे में पुलिस को लिख रहा/रही हूँ।"),
        L("I request you to take the action I ask for and give me a written acknowledgement.", "कृपया मेरे अनुरोध पर कार्रवाई करें और मुझे लिखित पावती दें।"),
        L("Any photos, messages or documents about the incident. Keep the originals with you.", "घटना से जुड़ी फ़ोटो, संदेश या कागज़। असली कागज़ अपने पास रखें।"),
        tags=("fir", "sho", "theft", "lost", "harassment"),
    ),
    DraftKind(
        "cyber_fraud", "safety", "lock", "letter",
        L("Online fraud: letter to your bank", "ऑनलाइन धोखाधड़ी: बैंक को पत्र", "Online fraud: bank ko letter"),
        L("Money lost to a scam call, link or fake payment.", "स्कैम कॉल, लिंक या नकली भुगतान में पैसे गए।", "Scam call, link ya fake payment mein paise gaye."),
        L("Report of an unauthorised online transaction and request to act", "अनधिकृत ऑनलाइन लेन-देन की सूचना और कार्रवाई का अनुरोध"),
        _r("full_name!", "address", "contact", "bank_name!", "incident_date!", "amount_lost!", "txn_ref", "reported_portal", "issue!", "requested_action!"),
        "bank_name",
        L("I am reporting an online transaction I did not authorise or that was made through fraud.", "मैं एक ऐसे ऑनलाइन लेन-देन की सूचना दे रहा/रही हूँ जिसकी मैंने अनुमति नहीं दी या जो धोखे से हुआ।"),
        L("I request you to investigate, block further debits if needed, and tell me in writing what you will do.", "कृपया जाँच करें, ज़रूरत हो तो आगे की कटौती रोकें और लिखित में बताएँ कि आप क्या करेंगे।"),
        L("Screenshots of the messages and transaction (hide full card or account numbers), and the complaint acknowledgement.", "संदेशों और लेन-देन के स्क्रीनशॉट (कार्ड या खाता नंबर छिपाकर) और शिकायत की पावती।"),
        "cybercrime.gov.in",
        ("scam", "upi", "otp", "1930"),
    ),
    # ---- City, school and rations ---------------------------------------------------------
    DraftKind(
        "civic_complaint", "city", "building", "letter",
        L("Garbage, drain or road complaint", "कचरा, नाली या सड़क की शिकायत", "Kachra, naali ya sadak ki shikayat"),
        L("A local problem the municipal corporation should fix.", "ऐसी स्थानीय समस्या जिसे नगर निगम को ठीक करना है।", "Aisi local problem jo MCD ko theek karni hai."),
        L("Complaint about a civic problem", "नागरिक समस्या की शिकायत"),
        _r("full_name!", "address", "contact", "addressed_to!", "city_issue!", "location!", "since", "issue!", "requested_action!"),
        "addressed_to",
        L("I am reporting the civic problem described below.", "मैं नीचे बताई नागरिक समस्या की सूचना दे रहा/रही हूँ।"),
        L("I request you to fix this and tell me in writing when it has been done.", "कृपया इसे ठीक करें और होने पर लिखित में बताएँ।"),
        L("Photos of the problem with the date visible, if you have them.", "समस्या की फ़ोटो, यदि हों, जिसमें तारीख दिखे।"),
        "mcdonline.nic.in",
        ("mcd", "municipal", "sanitation", "pothole"),
    ),
    DraftKind(
        "school_admission", "city", "cap", "letter",
        L("School admission problem", "स्कूल प्रवेश की समस्या", "School admission ki problem"),
        L("A school refused or ignored an admission, including under EWS or free seats.", "स्कूल ने प्रवेश से मना किया या अनदेखा किया, EWS या मुफ़्त सीट सहित।", "School ne admission se mana kiya ya ignore kiya, EWS ya free seat bhi."),
        L("Complaint about a school admission", "स्कूल प्रवेश के बारे में शिकायत"),
        _r("full_name!", "address!", "contact", "addressed_to!", "child_name!", "class_sought!", "school_name!", "school_issue!", "applied_on", "issue!", "requested_action!"),
        "addressed_to",
        L("I am writing about the admission of my child described below.", "मैं नीचे बताए अपने बच्चे के प्रवेश के बारे में लिख रहा/रही हूँ।"),
        L("I request you to look into this and tell me in writing what decision has been taken and why.", "कृपया इसे देखें और लिखित में बताएँ कि क्या निर्णय हुआ और क्यों।"),
        L("Application form, the school's reply (if any) and the child's birth proof.", "आवेदन पत्र, स्कूल का जवाब (यदि कोई) और बच्चे का जन्म प्रमाण।"),
        tags=("ews", "education", "rte", "directorate of education"),
    ),
)

BY_ID: dict[str, DraftKind] = {k.id: k for k in KINDS}
KIND_IDS: tuple[str, ...] = tuple(BY_ID)
