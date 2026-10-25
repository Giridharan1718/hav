export type Lang = "en" | "hi" | "ta";

export interface User {
  id: string;
  email: string;
  role: "citizen" | "reviewer" | "admin";
  mfa_enabled: boolean;
  created_at: string;
}

export interface Profile {
  full_name: string;
  date_of_birth: string | null;
  preferred_language: Lang;
  phone: string | null;
  phone_masked?: string | null;
  phone_verified: boolean;
  gender: string | null;
  updated_at?: string;
}

export interface Address {
  line1: string | null;
  pincode: string;
  post_office: string | null;
  district: string | null;
  state: string | null;
  post_office_confirmed: boolean;
}

export interface Consent {
  purpose: string;
  granted: boolean;
  document_version: string;
  granted_at: string | null;
  withdrawn_at: string | null;
}

export interface Me {
  user: User;
  profile: Profile | null;
  address: Address | null;
  consents: Consent[];
  permissions: { reviewer: boolean; admin: boolean; mfa_satisfied: boolean };
}

export interface SourceStatus {
  code: string;
  label: string;
  verified: boolean;
}

export interface SchemeCard {
  slug: string;
  name: string;
  department: string;
  scope: string;
  state: string | null;
  category: string;
  beneficiary_groups: string[];
  summary: string;
  summary_language: string;
  translation_available: boolean;
  available_languages: string[];
  official_url: string;
  source_status: SourceStatus;
  version_no: number;
  verified_at: string | null;
  retrieved_at: string | null;
  deadline: string | null;
  match: { terms: string[]; reason: string };
}

export interface SearchResponse {
  items: SchemeCard[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  query: string;
  normalized_query: string;
  language: Lang;
  language_detected: [string, string] | null;
  sort: string;
  filters: Record<string, string | null>;
  disclaimer: string;
}

export interface SchemeDetail {
  slug: string;
  name: string;
  department: string;
  scope: string;
  state: string | null;
  category: string;
  beneficiary_groups: string[];
  official_url: string;
  application_url: string;
  application_mode: string | null;
  deadline: string | null;
  benefit_summary: string;
  eligibility_summary: string;
  documents: Array<{ name: string; note?: string | null; required?: boolean; key?: string }> | string[];
  application_steps: string[];
  language: Lang;
  requested_language: Lang;
  translation_available: boolean;
  available_languages: string[];
  version: {
    version_no: number;
    review_status: string;
    review_label: string;
    verified: boolean;
    verified_at: string | null;
    retrieved_at: string | null;
    source_published_at: string | null;
    content_hash: string | null;
    effective_from: string | null;
    effective_to: string | null;
    review_notes: string | null;
  };
  application_link: {
    url: string;
    http_status: number | null;
    checked_at: string | null;
    verified: boolean;
  };
  source: {
    url: string | null;
    host: string | null;
    title: string | null;
    publisher: string | null;
    http_status: number | null;
    retrieved_at: string | null;
    content_hash: string | null;
    link_verified: boolean;
  };
  eligibility: {
    rules: Array<{
      rule_key: string;
      field: string;
      description: string;
      source_reference: string | null;
      validation_status: string;
    }>;
    required_fields: string[];
    evaluable: boolean;
  };
  disclaimer: string;
}

export interface EligibilityField {
  key: string;
  type: "int" | "number" | "bool" | "str";
  label: string;
  purpose: string;
  choices: string[] | null;
  minimum: number | null;
  maximum: number | null;
  sensitive: boolean;
}

export interface Questions {
  scheme: {
    slug: string | null;
    name: string | null;
    version_no: number;
    review_status: string;
    verified: boolean;
  };
  fields: EligibilityField[];
  rules: Array<{
    rule_key: string;
    field: string;
    description: string;
    source_reference: string | null;
  }>;
  prefill: Record<string, unknown> & { _note?: string };
  disclaimer: string;
}

export type Outcome =
  | "eligible"
  | "not_eligible"
  | "insufficient_information"
  | "cannot_evaluate";

export interface EligibilityResult {
  outcome: Outcome;
  scheme: {
    slug: string;
    name: string;
    version_no: number;
    review_status: string;
    verified: boolean;
    official_url: string;
  };
  rules: Array<{
    rule_key: string;
    status: "met" | "not_met" | "missing" | "unsupported" | "not_applicable";
    field?: string;
    label?: string;
    description?: string;
    source_reference?: string;
  }>;
  missing_fields: EligibilityField[];
  reasons: Array<Record<string, string>>;
  disclaimer: string;
  evaluated_at: string;
  language: Lang;
}

export interface Citation {
  id: string;
  scheme_slug: string;
  scheme_name: string;
  field: string;
  excerpt: string;
  official_url: string;
  source_url: string | null;
  retrieved_at: string | null;
  review_status: string;
}

export interface AssistantResponse {
  answer: string;
  language: Lang;
  detected_language: Lang;
  detection_method: string;
  provider: string;
  fallback_used: boolean;
  notices: Array<{ code: string; message: string }>;
  citations: Citation[];
  schemes: Array<{
    slug: string;
    name: string;
    official_url: string;
    review_status: string;
    verified: boolean;
    translation_available: boolean;
  }>;
  missing_information: string[];
  eligibility: EligibilityResult | null;
  disclaimer: string;
}

export interface DraftField {
  key: string;
  label: string;
  help_text: string | null;
  value: string | null;
  required: boolean;
  source: "empty" | "profile" | "user" | "assistant";
  source_reference: string | null;
  user_confirmed: boolean;
  status: "confirmed" | "proposed" | "missing";
}

export interface Draft {
  id: string;
  scheme: { slug: string | null; title: string; version_no: number | null };
  scheme_slug: string | null;
  status: string;
  fields: DraftField[];
  missing_required: string[];
  unconfirmed: string[];
  ready_to_export: boolean;
  created_at: string;
  updated_at: string;
  last_exported_at: string | null;
  language: Lang;
  disclaimer: string;
}

export interface DraftExport {
  format: string;
  document: unknown;
  submitted: boolean;
  disclaimer: string;
  draft: Draft;
}

export interface Health {
  status: string;
  environment: string;
  database: string;
  features: {
    sms: { provider: string; configured: boolean };
    email: { provider: string; configured: boolean };
    assistant: { provider: string; configured: boolean; fallback: string };
    translation: { provider: string; configured: boolean };
    transcription: { provider: string; configured: boolean };
    oidc: { enabled: boolean; issuer: string | null };
    postal_source: string;
    mfa: boolean;
  };
  languages: Lang[];
  time: string;
}

export interface PostalResponse {
  pincode: string;
  matches: Array<{
    name: string;
    district: string;
    state: string;
    branch_type: string | null;
    delivery_status: string | null;
  }>;
  ambiguous: boolean;
  source: {
    name: string;
    url: string | null;
    retrieved_at: string | null;
    is_sample: boolean;
    cached: boolean;
  };
  message?: string;
}

export interface SessionInfo {
  id: string;
  created_at: string;
  last_seen_at: string;
  expires_at: string;
  auth_level: string;
  current: boolean;
}
