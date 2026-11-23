export type RuleResult = "met" | "not_met" | "unknown";

export interface Citation {
  n: number;
  id: string;
  title: string;
  url: string;
  publisher: string;
  date_checked: string | null;
}

export interface ServiceCardData {
  type: "service";
  service: {
    id: string;
    name: string;
    department: string;
    summary: string;
    benefit: string | null;
    status: "verified" | "partial";
    stale: boolean;
    official_url: string | null;
    source_n: number;
  };
  eligibility: {
    verdict: "likely" | "not_eligible" | "incomplete";
    rules: { rule_id: string; label: string; result: RuleResult; required: boolean; source_n: number }[];
    exclusions_hit: { id: string; label: string }[];
  };
  prerequisites: { id: string; name: string }[];
  fee_strip: {
    official_fee_inr: number | null;
    csc_max_inr: number | null;
    processing_days: number | null;
    day_type: string | null;
    source_n: number;
  };
}

export interface Chip {
  label: string;
  confirm: Record<string, unknown>;
}

export interface StatusPill {
  id: string;
  label: string;
  state: "running" | "done";
}
