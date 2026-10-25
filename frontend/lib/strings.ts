import type { Lang } from "./types";

type Entry = Record<Lang, string>;

const S: Record<string, Entry> = {
  appName: { en: "HVA Assist", hi: "HVA सहायता", ta: "HVA உதவி" },
  tagline: {
    en: "Understand government schemes in your language",
    hi: "सरकारी योजनाएँ अपनी भाषा में समझें",
    ta: "அரசு திட்டங்களை உங்கள் மொழியில் புரிந்து கொள்ளுங்கள்",
  },
  nav_dashboard: { en: "Dashboard", hi: "डैशबोर्ड", ta: "முகப்பு" },
  nav_schemes: { en: "Schemes", hi: "योजनाएँ", ta: "திட்டங்கள்" },
  nav_assistant: { en: "Assistant", hi: "सहायक", ta: "உதவியாளர்" },
  nav_drafts: { en: "Drafts", hi: "मसौदे", ta: "வரைவுகள்" },
  nav_profile: { en: "Profile", hi: "प्रोफ़ाइल", ta: "சுயவிவரம்" },
  nav_privacy: { en: "Privacy", hi: "गोपनीयता", ta: "தனியுரிமை" },
  nav_admin: { en: "Administration", hi: "प्रशासन", ta: "நிர்வாகம்" },
  sign_in: { en: "Sign in", hi: "साइन इन", ta: "உள்நுழை" },
  sign_up: { en: "Create account", hi: "खाता बनाएँ", ta: "கணக்கு உருவாக்கு" },
  sign_out: { en: "Sign out", hi: "साइन आउट", ta: "வெளியேறு" },
  search: { en: "Search", hi: "खोजें", ta: "தேடு" },
  search_placeholder: {
    en: "e.g. farmer income support, scholarship, pension",
    hi: "जैसे किसान आय सहायता, छात्रवृत्ति, पेंशन",
    ta: "எ.கா. விவசாயி வருமான உதவி, கல்வி உதவித்தொகை, ஓய்வூதியம்",
  },
  filters: { en: "Filters", hi: "फ़िल्टर", ta: "வடிகட்டிகள்" },
  clear: { en: "Clear", hi: "साफ़ करें", ta: "அழி" },
  language: { en: "Language", hi: "भाषा", ta: "மொழி" },
  loading: { en: "Loading…", hi: "लोड हो रहा है…", ta: "ஏற்றப்படுகிறது…" },
  retry: { en: "Try again", hi: "फिर प्रयास करें", ta: "மீண்டும் முயற்சி" },
  save: { en: "Save", hi: "सहेजें", ta: "சேமி" },
  saving: { en: "Saving…", hi: "सहेजा जा रहा है…", ta: "சேமிக்கப்படுகிறது…" },
  cancel: { en: "Cancel", hi: "रद्द करें", ta: "ரத்து" },
  continue: { en: "Continue", hi: "आगे बढ़ें", ta: "தொடர்" },
  back: { en: "Back", hi: "वापस", ta: "பின்செல்" },
  optional: { en: "optional", hi: "वैकल्पिक", ta: "விருப்பம்" },
  required: { en: "required", hi: "आवश्यक", ta: "கட்டாயம்" },
  previous: { en: "Previous", hi: "पिछला", ta: "முந்தைய" },
  next: { en: "Next", hi: "अगला", ta: "அடுத்து" },
  page: { en: "Page", hi: "पृष्ठ", ta: "பக்கம்" },
  results: { en: "results", hi: "परिणाम", ta: "முடிவுகள்" },
  no_results: {
    en: "No schemes matched your search.",
    hi: "आपकी खोज से कोई योजना नहीं मिली।",
    ta: "உங்கள் தேட்டுக்கு எந்தத் திட்டமும் கிடைக்கவில்லை.",
  },
  view_details: { en: "View details", hi: "विवरण देखें", ta: "விவரங்கள்" },
  check_eligibility: { en: "Check eligibility", hi: "पात्रता जाँचें", ta: "தகுதியைச் சரிபார்" },
  prepare_draft: { en: "Prepare application draft", hi: "आवेदन मसौदा तैयार करें", ta: "விண்ணப்ப வரைவு தயாரிக்க" },
  documents_checklist: { en: "Document checklist", hi: "दस्तावेज़ सूची", ta: "ஆவணப் பட்டியல்" },
  official_page: { en: "Official page", hi: "आधिकारिक पृष्ठ", ta: "அதிகாரப்பூர்வ பக்கம்" },
  independent_notice: {
    en: "HVA is an independent assistance platform. It is not a government website and does not certify identity or guarantee benefits.",
    hi: "HVA एक स्वतंत्र सहायता मंच है। यह सरकारी वेबसाइट नहीं है और पहचान प्रमाणित या लाभ की गारंटी नहीं देता।",
    ta: "HVA ஒரு சுயாதீன உதவி தளம். இது அரசு இணையதளம் அல்ல; அடையாளத்தை உறுதிப்படுத்தவோ பயன்களுக்கு உத்தரவாதம் அளிக்கவோ இல்லை.",
  },
  disclaimer: { en: "Disclaimer", hi: "अस्वीकरण", ta: "பொறுப்புத்துறப்பு" },
  error_title: { en: "Something went wrong", hi: "कुछ गलत हो गया", ta: "ஏதோ தவறாகிவிட்டது" },
  offline_title: {
    en: "You are offline. Previously loaded information may be out of date.",
    hi: "आप ऑफ़लाइन हैं। पहले लोड की गई जानकारी पुरानी हो सकती है।",
    ta: "நீங்கள் இணையமின்றி உள்ளீர்கள். முன்பு ஏற்றிய தகவல் பழையதாக இருக்கலாம்.",
  },
  reviewed_source: { en: "Source", hi: "स्रोत", ta: "மூலம்" },
  translation_unavailable: {
    en: "A reviewed translation is not available; showing the English text.",
    hi: "समीक्षित अनुवाद उपलब्ध नहीं है; अंग्रेज़ी पाठ दिखाया जा रहा है।",
    ta: "மதிப்பாய்வு செய்யப்பட்ட மொழிபெயர்ப்பு இல்லை; ஆங்கில உரை காட்டப்படுகிறது.",
  },
  draft_saved: { en: "Draft saved", hi: "मसौदा सहेजा गया", ta: "வரைவு சேமிக்கப்பட்டது" },
  not_submitted: {
    en: "Nothing is submitted automatically. You review and file on the official portal.",
    hi: "कुछ भी स्वतः जमा नहीं होता। आप समीक्षा कर आधिकारिक पोर्टल पर आवेदन करते हैं।",
    ta: "எதுவும் தானாக சமர்ப்பிக்கப்படாது. நீங்கள் சரிபார்த்து அதிகாரப்பூர்வ இணையதளத்தில் விண்ணப்பிக்கிறீர்கள்.",
  },
};

export function tr(lang: Lang, key: keyof typeof S | string): string {
  const entry = S[key as string];
  if (!entry) return key;
  return entry[lang] ?? entry.en;
}

export const LANGUAGES: Array<{ code: Lang; label: string; english: string }> = [
  { code: "en", label: "English", english: "English" },
  { code: "hi", label: "हिन्दी", english: "Hindi" },
  { code: "ta", label: "தமிழ்", english: "Tamil" },
];
