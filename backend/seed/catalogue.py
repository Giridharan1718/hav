"""Curated development catalogue.

Content is transcribed from the official scheme pages listed per record on 2026-10-22.
Every record is seeded as ``source_checked`` (the link was fetched successfully) or
``pending_review`` (the link could not be checked), never as ``verified``: human
content-reviewer sign-off is required before production use. Hindi and Tamil entries
are development translations marked ``draft`` and are explicitly unreviewed.
"""

from __future__ import annotations

SOURCE_CHECKED = "source_checked"
PENDING_REVIEW = "pending_review"

REVIEW_NOTE_VERIFIED_LINK = (
    "Automated source-link check passed; scheme text transcribed by the development team. "
    "A human reviewer must confirm every criterion before this is treated as verified."
)
REVIEW_NOTE_PENDING_LINK = (
    "The official link could not be fetched from the build environment; content is transcribed "
    "from public documentation. Flagged unavailable and awaiting reviewer verification."
)

SCHEMES: list[dict] = [
    {
        "slug": "pm-kisan",
        "name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "department": "Ministry of Agriculture and Farmers Welfare",
        "scope": "central",
        "state_name": None,
        "category": "Agriculture",
        "beneficiary_groups": ["farmer", "rural"],
        "official_url": "https://pmkisan.gov.in/",
        "application_url": "https://pmkisan.gov.in/",
        "application_mode": "online, CSC or state agriculture office",
        "benefit": (
            "Income support of ₹6,000 per year to eligible landholding farmer families, paid in "
            "three instalments of ₹2,000, subject to verification and scheme rules."
        ),
        "eligibility": (
            "Landholding farmer families, subject to exclusions notified for the scheme, including "
            "institutional landholders and income-tax payers. Aadhaar-based e-KYC and land records "
            "are used to verify eligibility."
        ),
        "documents": [
            {"key": "aadhaar", "name": "Aadhaar card", "note": "Used for e-KYC.", "required": True},
            {"key": "land_records", "name": "Land ownership records", "note": "As applicable in your state.", "required": True},
            {"key": "bank_account", "name": "Bank account details", "note": "For instalment transfer.", "required": True},
        ],
        "steps": [
            "Open the PM-KISAN portal and check your registration or beneficiary status.",
            "Complete Aadhaar-based e-KYC.",
            "Register through the portal, a Common Service Centre, or your state agriculture office.",
            "Track instalment status on the portal.",
        ],
        "rules": [
            {
                "key": "min_age", "field": "age", "operator": "gte", "value": 18,
                "description": "The applicant must be an adult (18 years or older).",
            },
            {
                "key": "occupation_farmer", "field": "occupation", "operator": "in",
                "value": ["farmer"], "description": "The scheme is for landholding farmer families.",
            },
            {
                "key": "landholding_present", "field": "landholding_acres", "operator": "gte",
                "value": 0.01, "description": "The family must hold agricultural land.",
            },
            {
                "key": "not_income_tax_payer", "field": "is_income_tax_payer", "operator": "is_false",
                "value": True, "description": "Income-tax payers are excluded by the scheme rules.",
            },
        ],
        "translations": {
            "hi": {
                "benefit": (
                    "पात्र भूमिधारी किसान परिवारों को प्रति वर्ष ₹6,000 की आय सहायता, ₹2,000 की तीन "
                    "किस्तों में, सत्यापन और योजना नियमों के अधीन।"
                ),
                "eligibility": (
                    "भूमिधारी किसान परिवार, योजना में अधिसूचित अपवर्जनों के अधीन, जिनमें संस्थागत "
                    "भूमिधारक और आयकर दाता शामिल हैं। पात्रता सत्यापन के लिए आधार आधारित e-KYC और "
                    "भूमि अभिलेखों का उपयोग होता है।"
                ),
                "documents": ["आधार कार्ड", "भूमि स्वामित्व अभिलेख", "बैंक खाता विवरण"],
                "steps": [
                    "PM-KISAN पोर्टल पर अपनी पंजीकरण या लाभार्थी स्थिति देखें।",
                    "आधार आधारित e-KYC पूरा करें।",
                    "पोर्टल, सामान्य सेवा केंद्र या राज्य कृषि कार्यालय से पंजीकरण करें।",
                    "पोर्टल पर किस्त की स्थिति देखें।",
                ],
            },
            "ta": {
                "benefit": (
                    "தகுதியுள்ள நிலம் வைத்திருக்கும் விவசாயக் குடும்பங்களுக்கு ஆண்டுக்கு ₹6,000 "
                    "வருமான உதவி, ₹2,000 வீதம் மூன்று தவணைகளில், சரிபார்ப்பு மற்றும் திட்ட "
                    "விதிமுறைகளுக்கு உட்பட்டு."
                ),
                "eligibility": (
                    "நிலம் வைத்திருக்கும் விவசாயக் குடும்பங்கள்; திட்டத்தில் அறிவிக்கப்பட்ட "
                    "விலக்குகளுக்கு உட்பட்டவை, அவற்றில் நிறுவன நில உரிமையாளர்கள் மற்றும் "
                    "வருமான வரி செலுத்துவோர் அடங்குவர். ஆதார் அடிப்படையிலான e-KYC மற்றும் நில "
                    "பதிவுகள் மூலம் தகுதி சரிபார்க்கப்படுகிறது."
                ),
                "documents": ["ஆதார் அட்டை", "நில உரிமைப் பதிவுகள்", "வங்கிக் கணக்கு விவரங்கள்"],
                "steps": [
                    "PM-KISAN இணையதளத்தில் உங்கள் பதிவு அல்லது பயனாளர் நிலையைப் பார்க்கவும்.",
                    "ஆதார் அடிப்படையிலான e-KYC முடிக்கவும்.",
                    "இணையதளம், பொது சேவை மையம் அல்லது மாநில வேளாண்மை அலுவலகம் மூலம் பதிவு செய்யவும்.",
                    "தவணை நிலையை இணையதளத்தில் கண்காணிக்கவும்.",
                ],
            },
        },
    },
    {
        "slug": "ayushman-bharat-pmjay",
        "name": "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (PM-JAY)",
        "department": "National Health Authority",
        "scope": "central",
        "state_name": None,
        "category": "Health",
        "beneficiary_groups": ["low_income", "rural", "urban"],
        "official_url": "https://pmjay.gov.in/",
        "application_url": "https://pmjay.gov.in/",
        "application_mode": "online entitlement check followed by e-KYC at a CSC or hospital",
        "benefit": (
            "Health cover of ₹5 lakh per family per year for secondary and tertiary hospitalisation, "
            "cashless at empanelled hospitals, subject to scheme conditions."
        ),
        "eligibility": (
            "Families identified through the SECC deprivation and occupational criteria and notified "
            "occupational groups, as recorded in the official entitlement list. Eligibility is decided "
            "from the entitlement list, not from self-reported answers, so this platform cannot evaluate "
            "it from a questionnaire."
        ),
        "documents": [
            {"key": "id_proof", "name": "Identity document such as Aadhaar", "note": "For e-KYC.", "required": True},
            {"key": "ration_card", "name": "Ration card or family entitlement document", "note": "As applicable.", "required": True},
        ],
        "steps": [
            "Check whether your family appears in the PM-JAY beneficiary list on the official portal.",
            "Visit a Common Service Centre or an empanelled hospital and complete e-KYC.",
            "Obtain or update your Ayushman card as instructed.",
            "Show the card at an empanelled hospital for cashless treatment.",
        ],
        "rules": [
            {
                "key": "secc_entitlement", "field": "is_bpl", "operator": "requires_entitlement_list",
                "value": True, "validation_status": "unsupported",
                "description": (
                    "Eligibility is defined by the official SECC-based entitlement list. Self-reported "
                    "information cannot determine it, so this check reports that evaluation is unavailable."
                ),
            }
        ],
        "translations": {},
    },
    {
        "slug": "post-matric-scholarship-sc",
        "name": "Post-Matric Scholarship for Scheduled Caste Students",
        "department": "Ministry of Social Justice and Empowerment",
        "scope": "central",
        "state_name": None,
        "category": "Education",
        "beneficiary_groups": ["student", "sc"],
        "official_url": "https://socialjustice.gov.in/",
        "application_url": "https://scholarships.gov.in/",
        "application_mode": "online through the National Scholarship Portal",
        "benefit": (
            "Financial assistance towards tuition fees, maintenance allowance and other notified "
            "allowances for eligible Scheduled Caste students studying after Class 10, with amounts "
            "fixed for each academic year."
        ),
        "eligibility": (
            "Scheduled Caste students at the post-matriculation level whose family income is within the "
            "limit notified for the scheme, applying through the National Scholarship Portal within the "
            "notified dates. Institute verification and document checks apply."
        ),
        "documents": [
            {"key": "caste_certificate", "name": "Scheduled Caste certificate", "required": True},
            {"key": "income_certificate", "name": "Family income certificate", "required": True},
            {"key": "marksheet", "name": "Previous qualifying marksheet", "required": True},
            {"key": "bank_account", "name": "Bank account in the student's name", "required": True},
            {"key": "institute_verification", "name": "Institute verification", "note": "Completed online by the institution.", "required": True},
        ],
        "steps": [
            "Register on the National Scholarship Portal.",
            "Complete the application and upload the required documents.",
            "Submit before the notified deadline and complete institute verification.",
            "Track the application status on the portal.",
        ],
        "rules": [
            {
                "key": "category_sc", "field": "social_category", "operator": "in", "value": ["sc"],
                "description": "The scholarship is for Scheduled Caste students.",
            },
            {
                "key": "income_limit", "field": "annual_income_inr", "operator": "lte", "value": 250000,
                "description": "Family income must be within the limit notified for the scheme.",
            },
            {
                "key": "is_studying", "field": "is_student", "operator": "is_true", "value": True,
                "description": "The applicant must be currently studying.",
            },
            {
                "key": "post_matric_level", "field": "education_level", "operator": "in",
                "value": ["class_11", "class_12", "undergraduate", "postgraduate"],
                "description": "Study must be at the post-matriculation level.",
            },
        ],
        "translations": {
            "hi": {
                "benefit": (
                    "कक्षा 10 के बाद अध्ययन करने वाले पात्र अनुसूचित जाति के छात्रों के लिए ट्यूशन शुल्क, "
                    "रखरखाव भत्ता और अन्य अधिसूचित भत्तों के रूप में वित्तीय सहायता, जिसकी राशि प्रत्येक "
                    "शैक्षणिक वर्ष के लिए निर्धारित होती है।"
                ),
                "eligibility": (
                    "मैट्रिकोत्तर स्तर पर अध्ययन करने वाले अनुसूचित जाति के छात्र, जिनके परिवार की आय "
                    "योजना के लिए अधिसूचित सीमा के भीतर है और जो अधिसूचित तिथियों के भीतर राष्ट्रीय "
                    "छात्रवृत्ति पोर्टल से आवेदन करते हैं। संस्थान सत्यापन और दस्तावेज़ जाँच लागू है।"
                ),
                "documents": [
                    "अनुसूचित जाति प्रमाण पत्र",
                    "पारिवारिक आय प्रमाण पत्र",
                    "पिछली योग्यता की मार्कशीट",
                    "छात्र के नाम का बैंक खाता",
                    "संस्थान सत्यापन",
                ],
                "steps": [
                    "राष्ट्रीय छात्रवृत्ति पोर्टल पर पंजीकरण करें।",
                    "आवेदन पूरा करें और आवश्यक दस्तावेज़ अपलोड करें।",
                    "अधिसूचित अंतिम तिथि से पहले आवेदन जमा करें और संस्थान सत्यापन पूरा कराएँ।",
                    "पोर्टल पर आवेदन की स्थिति देखें।",
                ],
            },
            "ta": {
                "benefit": (
                    "10ஆம் வகுப்புக்குப் பிறகு படிக்கும் தகுதியுள்ள பட்டியல் சாதி மாணவர்களுக்கு "
                    "கல்விக் கட்டணம், பராமரிப்புப் படி மற்றும் பிற அறிவிக்கப்பட்ட படிகளுக்கான "
                    "நிதி உதவி; தொகைகள் ஒவ்வொரு கல்வி ஆண்டுக்கும் நிர்ணயிக்கப்படும்."
                ),
                "eligibility": (
                    "மேல்நிலைக்குப் பிந்தைய நிலையில் படிக்கும் பட்டியல் சாதி மாணவர்கள், திட்டத்திற்கு "
                    "அறிவிக்கப்பட்ட வரம்புக்குள் குடும்ப வருமானம் உள்ளவர்கள், அறிவிக்கப்பட்ட "
                    "தேதிகளுக்குள் தேசிய கல்வி உதவித்தொகை இணையதளத்தில் விண்ணப்பிப்பவர்கள். "
                    "நிறுவன சரிபார்ப்பு மற்றும் ஆவண சரிபார்ப்பு பொருந்தும்."
                ),
                "documents": [
                    "பட்டியல் சாதி சான்றிதழ்",
                    "குடும்ப வருமான சான்றிதழ்",
                    "முந்தைய தகுதித் தேர்வு மதிப்பெண் சான்றிதழ்",
                    "மாணவர் பெயரில் வங்கிக் கணக்கு",
                    "நிறுவன சரிபார்ப்பு",
                ],
                "steps": [
                    "தேசிய கல்வி உதவித்தொகை இணையதளத்தில் பதிவு செய்யவும்.",
                    "விண்ணப்பத்தை முடித்து தேவையான ஆவணங்களைப் பதிவேற்றவும்.",
                    "அறிவிக்கப்பட்ட கடைசி தேதிக்குள் சமர்ப்பித்து நிறுவன சரிபார்ப்பை முடிக்கவும்.",
                    "இணையதளத்தில் விண்ணப்ப நிலையைக் கண்காணிக்கவும்.",
                ],
            },
        },
    },
    {
        "slug": "pmay-gramin",
        "name": "Pradhan Mantri Awaas Yojana - Gramin (PMAY-G)",
        "department": "Ministry of Rural Development",
        "scope": "central",
        "state_name": None,
        "category": "Housing",
        "beneficiary_groups": ["rural", "low_income"],
        "official_url": "https://pmayg.dord.gov.in/netiayHome/Home.aspx",
        "application_url": "https://pmayg.dord.gov.in/netiayHome/Home.aspx",
        "application_mode": "through the Gram Panchayat and the PMAY-G portal",
        "benefit": (
            "Financial assistance for constructing a pucca house, with support for a toilet, electricity "
            "and drinking-water connection for eligible rural households, as notified."
        ),
        "eligibility": (
            "Rural households identified through SECC deprivation criteria and verified by the Gram "
            "Sabha, who do not already own a pucca house. Selection depends on the official priority "
            "list; this questionnaire covers only the documented self-checkable conditions."
        ),
        "documents": [
            {"key": "aadhaar", "name": "Aadhaar card", "required": True},
            {"key": "secc_or_jobcard", "name": "SECC or MGNREGA job card details", "note": "As available.", "required": True},
            {"key": "bank_account", "name": "Bank account details", "required": True},
            {"key": "land_documents", "name": "Land documents", "note": "As applicable in your state.", "required": False},
        ],
        "steps": [
            "Check the PMAY-G priority list or contact your Gram Panchayat.",
            "Complete the beneficiary verification process with the Gram Panchayat.",
            "Provide bank and Aadhaar details for instalment release.",
            "Track construction progress and instalments on the portal.",
        ],
        "rules": [
            {
                "key": "rural_household", "field": "residence_area", "operator": "eq", "value": "rural",
                "description": "The scheme is for rural households.",
            },
            {
                "key": "no_pucca_house", "field": "has_pucca_house", "operator": "is_false", "value": True,
                "description": "Households that already own a pucca house are excluded.",
            },
        ],
        "translations": {},
    },
    {
        "slug": "atal-pension-yojana",
        "name": "Atal Pension Yojana (APY)",
        "department": "Pension Fund Regulatory and Development Authority (PFRDA)",
        "scope": "central",
        "state_name": None,
        "category": "Pension",
        "beneficiary_groups": ["unorganised_worker", "worker"],
        "official_url": "https://www.pfrda.org.in/",
        "application_url": "https://www.pfrda.org.in/",
        "application_mode": "through a bank or post office branch",
        "benefit": (
            "A guaranteed pension of ₹1,000 to ₹5,000 per month after age 60, depending on the "
            "contribution chosen, for subscribers who contribute until age 60. Spouse and nominee "
            "benefits apply as per scheme rules."
        ),
        "eligibility": (
            "Indian citizens aged 18 to 40 with a savings bank or post office account, who are not "
            "income-tax payers. Subscribers must keep contributing until age 60."
        ),
        "documents": [
            {"key": "aadhaar", "name": "Aadhaar card", "required": True},
            {"key": "bank_account", "name": "Savings bank or post office account", "required": True},
            {"key": "mobile", "name": "Mobile number", "required": True},
        ],
        "steps": [
            "Visit your bank or post office branch.",
            "Complete the APY registration with Aadhaar and account details.",
            "Choose the pension amount and contribution frequency.",
            "Keep contributing until age 60 to receive the pension.",
        ],
        "rules": [
            {
                "key": "min_age", "field": "age", "operator": "gte", "value": 18,
                "description": "The minimum entry age is 18.",
            },
            {
                "key": "max_age", "field": "age", "operator": "lte", "value": 40,
                "description": "The maximum entry age is 40.",
            },
            {
                "key": "bank_account_required", "field": "has_bank_account", "operator": "is_true", "value": True,
                "description": "A savings bank or post office account is required.",
            },
            {
                "key": "not_income_tax_payer", "field": "is_income_tax_payer", "operator": "is_false", "value": True,
                "description": "Income-tax payers are not eligible to join.",
            },
        ],
        "translations": {},
    },
    {
        "slug": "mgnrega-job-card",
        "name": "Mahatma Gandhi National Rural Employment Guarantee Act (MGNREGA)",
        "department": "Ministry of Rural Development",
        "scope": "central",
        "state_name": None,
        "category": "Employment",
        "beneficiary_groups": ["rural", "worker"],
        "official_url": "https://nrega.nic.in/",
        "application_url": "https://nrega.nic.in/",
        "application_mode": "through the Gram Panchayat",
        "benefit": (
            "At least 100 days of unskilled wage employment per rural household per financial year, "
            "provided on demand, with wages paid to a bank or post office account within the statutory "
            "time limit."
        ),
        "eligibility": (
            "Adult members of rural households. Apply for a job card at the Gram Panchayat; employment "
            "must be provided on demand within the time limits set by the Act."
        ),
        "documents": [
            {"key": "aadhaar", "name": "Aadhaar card", "required": True},
            {"key": "photo", "name": "Passport-size photograph", "required": True},
            {"key": "bank_account", "name": "Bank or post office account", "required": True},
            {"key": "residence_proof", "name": "Residence proof", "note": "As requested by the Gram Panchayat.", "required": False},
        ],
        "steps": [
            "Apply for a job card at your Gram Panchayat.",
            "Collect the job card once issued.",
            "Submit a written demand for work for the period you need.",
            "Attend the allotted work and receive wages in your account.",
        ],
        "rules": [
            {
                "key": "adult", "field": "age", "operator": "gte", "value": 18,
                "description": "Only adults can register for a job card.",
            },
            {
                "key": "rural_household", "field": "residence_area", "operator": "eq", "value": "rural",
                "description": "The Act applies to rural households.",
            },
        ],
        "translations": {
            "hi": {
                "benefit": (
                    "प्रत्येक ग्रामीण परिवार को प्रति वित्तीय वर्ष कम से कम 100 दिन का अकुशल "
                    "मजदूरी रोजगार, माँग पर, वेतन बैंक या डाकघर खाते में वैधानिक समय सीमा के भीतर।"
                ),
                "eligibility": (
                    "ग्रामीण परिवारों के वयस्क सदस्य। ग्राम पंचायत में जॉब कार्ड के लिए आवेदन करें; "
                    "अधिनियम की समय सीमा के भीतर माँग पर रोजगार दिया जाना चाहिए।"
                ),
                "documents": ["आधार कार्ड", "पासपोर्ट आकार का फोटो", "बैंक या डाकघर खाता", "निवास प्रमाण"],
                "steps": [
                    "अपनी ग्राम पंचायत में जॉब कार्ड के लिए आवेदन करें।",
                    "जारी होने पर जॉब कार्ड प्राप्त करें।",
                    "जिस अवधि के लिए काम चाहिए, उसके लिए लिखित माँग दें।",
                    "आवंटित कार्य में उपस्थित रहें और खाते में मजदूरी प्राप्त करें।",
                ],
            },
            "ta": {
                "benefit": (
                    "ஒவ்வொரு கிராமப்புறக் குடும்பத்திற்கும் நிதியாண்டுக்கு குறைந்தது 100 நாட்கள் "
                    "திறனில்லாத ஊதிய வேலை, கேட்பின் அடிப்படையில்; ஊதியம் சட்டப்பூர்வ கால வரம்புக்குள் "
                    "வங்கி அல்லது தபால் அலுவலகக் கணக்கில்."
                ),
                "eligibility": (
                    "கிராமப்புறக் குடும்பங்களின் பெரியவர்கள். கிராம பஞ்சாயத்தில் வேலை அட்டைக்கு "
                    "விண்ணப்பிக்கவும்; சட்டத்தில் நிர்ணயிக்கப்பட்ட கால வரம்புக்குள் கேட்பின் "
                    "அடிப்படையில் வேலை வழங்கப்பட வேண்டும்."
                ),
                "documents": ["ஆதார் அட்டை", "பாஸ்போர்ட் அளவு புகைப்படம்", "வங்கி அல்லது தபால் அலுவலகக் கணக்கு", "வசிப்பிடச் சான்று"],
                "steps": [
                    "உங்கள் கிராம பஞ்சாயத்தில் வேலை அட்டைக்கு விண்ணப்பிக்கவும்.",
                    "வழங்கப்பட்ட பிறகு வேலை அட்டையைப் பெறவும்.",
                    "தேவையான காலத்திற்கு எழுத்துப்பூர்வமாக வேலை கோரிக்கை அளிக்கவும்.",
                    "ஒதுக்கப்பட்ட வேலைக்குச் சென்று கணக்கில் ஊதியம் பெறவும்.",
                ],
            },
        },
    },
    {
        "slug": "nsap-old-age-pension",
        "name": "Indira Gandhi National Old Age Pension Scheme (IGNOAPS)",
        "department": "Ministry of Rural Development (National Social Assistance Programme)",
        "scope": "central",
        "state_name": None,
        "category": "Pension",
        "beneficiary_groups": ["senior_citizen", "low_income"],
        "official_url": "https://nsap.dord.gov.in/",
        "application_url": "https://nsap.dord.gov.in/",
        "application_mode": "through the Block/Tehsil office or the state social welfare portal",
        "benefit": (
            "A monthly pension for eligible persons aged 60 and above from Below Poverty Line "
            "households. The central contribution is fixed by the scheme and many states add a top-up; "
            "the exact amount is notified by the administering authority."
        ),
        "eligibility": (
            "Persons aged 60 or above belonging to Below Poverty Line households, as identified by the "
            "state or union territory. Apply through the local Block/Tehsil social welfare office or "
            "the state pension portal."
        ),
        "documents": [
            {"key": "age_proof", "name": "Age proof", "required": True},
            {"key": "bpl_card", "name": "BPL card or household certificate", "required": True},
            {"key": "bank_account", "name": "Bank or post office account", "required": True},
            {"key": "aadhaar", "name": "Aadhaar card", "required": True},
        ],
        "steps": [
            "Apply at the Block/Tehsil social welfare office or your state pension portal.",
            "Complete verification of age and household details.",
            "Wait for sanction and first credit to your bank account.",
            "Report changes that affect eligibility to the local office.",
        ],
        "rules": [
            {
                "key": "minimum_age", "field": "age", "operator": "gte", "value": 60,
                "description": "The applicant must be at least 60 years old.",
            },
            {
                "key": "bpl_household", "field": "is_bpl", "operator": "is_true", "value": True,
                "description": "The household must be below the poverty line as identified by the state.",
            },
        ],
        "translations": {
            "hi": {
                "benefit": (
                    "गरीबी रेखा से नीचे के परिवारों के 60 वर्ष या अधिक आयु के पात्र व्यक्तियों के लिए "
                    "मासिक पेंशन। केंद्र का अंश योजना द्वारा निर्धारित है और कई राज्य अतिरिक्त राशि "
                    "देते हैं; सटीक राशि प्रशासन द्वारा अधिसूचित होती है।"
                ),
                "eligibility": (
                    "राज्य या केंद्रशासित प्रदेश द्वारा चिह्नित गरीबी रेखा से नीचे के परिवारों के 60 "
                    "वर्ष या अधिक आयु के व्यक्ति। स्थानीय ब्लॉक/तहसील समाज कल्याण कार्यालय या राज्य "
                    "पेंशन पोर्टल से आवेदन करें।"
                ),
                "documents": ["आयु प्रमाण", "बीपीएल कार्ड या परिवार प्रमाण पत्र", "बैंक या डाकघर खाता", "आधार कार्ड"],
                "steps": [
                    "ब्लॉक/तहसील समाज कल्याण कार्यालय या राज्य पेंशन पोर्टल पर आवेदन करें।",
                    "आयु और परिवार विवरण का सत्यापन पूरा कराएँ।",
                    "स्वीकृति और बैंक खाते में पहली राशि की प्रतीक्षा करें।",
                    "पात्रता प्रभावित करने वाले बदलाव स्थानीय कार्यालय को बताएँ।",
                ],
            },
            "ta": {
                "benefit": (
                    "வறுமைக் கோட்டுக்குக் கீழ் உள்ள குடும்பங்களைச் சேர்ந்த 60 வயது மற்றும் "
                    "அதற்கு மேற்பட்ட தகுதியுள்ள நபர்களுக்கு மாதாந்திர ஓய்வூதியம். மத்திய அரசின் "
                    "பங்கு திட்டத்தால் நிர்ணயிக்கப்படுகிறது; பல மாநிலங்கள் கூடுதல் தொகை வழங்குகின்றன; "
                    "சரியான தொகை நிர்வாகத்தால் அறிவிக்கப்படும்."
                ),
                "eligibility": (
                    "மாநிலம் அல்லது யூனியன் பிரதேசத்தால் அடையாளம் காணப்பட்ட வறுமைக் கோட்டுக்குக் "
                    "கீழ் உள்ள குடும்பங்களைச் சேர்ந்த 60 வயது அல்லது அதற்கு மேற்பட்ட நபர்கள். "
                    "உள்ளூர் வட்டார/தாலுக்கா சமூக நல அலுவலகம் அல்லது மாநில ஓய்வூதிய "
                    "இணையதளத்தில் விண்ணப்பிக்கவும்."
                ),
                "documents": ["வயது சான்று", "வறுமைக் கோட்டு அட்டை அல்லது குடும்பச் சான்றிதழ்", "வங்கி அல்லது தபால் அலுவலகக் கணக்கு", "ஆதார் அட்டை"],
                "steps": [
                    "வட்டார/தாலுக்கா சமூக நல அலுவலகம் அல்லது மாநில ஓய்வூதிய இணையதளத்தில் விண்ணப்பிக்கவும்.",
                    "வயது மற்றும் குடும்ப விவரங்களின் சரிபார்ப்பை முடிக்கவும்.",
                    "ஒப்புதல் மற்றும் வங்கிக் கணக்கில் முதல் தொகை வரும் வரை காத்திருக்கவும்.",
                    "தகுதியைப் பாதிக்கும் மாற்றங்களை உள்ளூர் அலுவலகத்திற்குத் தெரிவிக்கவும்.",
                ],
            },
        },
    },
    {
        "slug": "sukanya-samriddhi-yojana",
        "name": "Sukanya Samriddhi Yojana (SSY)",
        "department": "Department of Posts / Ministry of Finance",
        "scope": "central",
        "state_name": None,
        "category": "Savings",
        "beneficiary_groups": ["girl_child"],
        "official_url": "https://www.indiapost.gov.in/",
        "application_url": "https://www.indiapost.gov.in/",
        "application_mode": "at a post office or authorised bank branch",
        "benefit": (
            "A small savings account for a girl child with a government-notified interest rate. "
            "Deposits are made for 15 years and the account matures 21 years after opening, subject to "
            "scheme rules."
        ),
        "eligibility": (
            "A girl child below 10 years of age, with an account opened by a parent or guardian. "
            "A maximum of two accounts per family is allowed, subject to the scheme rules."
        ),
        "documents": [
            {"key": "birth_certificate", "name": "Birth certificate of the child", "required": True},
            {"key": "guardian_id", "name": "Guardian identity and address proof", "required": True},
            {"key": "photograph", "name": "Photograph of the child and guardian", "required": True},
        ],
        "steps": [
            "Visit a post office or an authorised bank branch.",
            "Complete the account opening form and submit documents.",
            "Make the initial deposit within the prescribed limit.",
            "Keep deposit records and review the passbook.",
        ],
        "rules": [
            {
                "key": "child_age_limit", "field": "child_age", "operator": "lte", "value": 10,
                "description": "The account must be opened before the girl child turns 10.",
            },
            {
                "key": "girl_child", "field": "child_gender", "operator": "in", "value": ["female"],
                "description": "The account is for a girl child.",
            },
        ],
        "translations": {},
    },
]

PINCODES: list[dict] = [
    {"pincode": "110001", "name": "New Delhi GPO", "district": "New Delhi", "state": "Delhi", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "400001", "name": "Mumbai GPO", "district": "Mumbai", "state": "Maharashtra", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "600001", "name": "Chennai GPO", "district": "Chennai", "state": "Tamil Nadu", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "560001", "name": "Bengaluru GPO", "district": "Bengaluru", "state": "Karnataka", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "500001", "name": "Hyderabad GPO", "district": "Hyderabad", "state": "Telangana", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "700001", "name": "Kolkata GPO", "district": "Kolkata", "state": "West Bengal", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "411001", "name": "Pune GPO", "district": "Pune", "state": "Maharashtra", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "380001", "name": "Ahmedabad GPO", "district": "Ahmedabad", "state": "Gujarat", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "302001", "name": "Jaipur GPO", "district": "Jaipur", "state": "Rajasthan", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "226001", "name": "Lucknow GPO", "district": "Lucknow", "state": "Uttar Pradesh", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "800001", "name": "Patna GPO", "district": "Patna", "state": "Bihar", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "751001", "name": "Bhubaneswar GPO", "district": "Khordha", "state": "Odisha", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
    {"pincode": "781001", "name": "Guwahati GPO", "district": "Kamrup Metropolitan", "state": "Assam", "branch_type": "Head Post Office", "delivery_status": "Delivery"},
]
