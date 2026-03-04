import { z } from "zod";

// TimeRange schema
const TimeRangeSchema = z.object({
  start_ms: z.number(),
  end_ms: z.number(),
}).passthrough();

// Trigger evidence schema
const TriggerEvidenceSchema = z.object({
  time_ranges: z.array(TimeRangeSchema),
  text_snippets: z.array(z.string()),
}).passthrough();

// Trigger schema
export const TriggerSchema = z.object({
  id: z.string(),
  severity: z.enum(["P0", "P1", "P2"]),
  impact_score: z.number(),
  weight: z.number(),
  priority_score: z.number(),
  conflict_priority: z.number(),
  trigger_count: z.number(),
  evidence: TriggerEvidenceSchema,
}).passthrough();

// Drill schema
const DrillSchema = z.object({
  drill_id: z.string(),
  steps: z.array(z.string()),
  duration_sec: z.number(),
  tips: z.array(z.string()),
}).passthrough();

// Acceptance schema
const AcceptanceSchema = z.object({
  metric: z.string(),
  target: z.union([z.string(), z.number(), z.boolean()]),
  how_to_measure: z.string(),
}).passthrough();

// Suggestion evidence_ref schema
const SuggestionEvidenceRefSchema = z.object({
  time_ranges: z.array(TimeRangeSchema),
  text_snippets: z.array(z.string()),
}).passthrough();

// Suggestion schema
export const SuggestionSchema = z.object({
  title: z.string(),
  problem: z.string(),
  cause: z.string(),
  evidence_ref: SuggestionEvidenceRefSchema,
  drill: DrillSchema,
  acceptance: AcceptanceSchema,
}).passthrough();

// Session schema
const SessionSchema = z.object({
  session_id: z.string(),
  task_type: z.string(),
  language: z.string(),
  generated_at: z.string(),
}).passthrough();

// Scores schema
const ScoresSchema = z.object({
  overall: z.number(),
}).passthrough();

// Rule engine schema
const RuleEngineSchema = z.object({
  triggers: z.array(TriggerSchema),
  top_trigger_id: z.string().nullable(),
  next_target: z.unknown().nullable(),
}).passthrough();

// LLM feedback schema
const LlmFeedbackSchema = z.object({
  suggestions: z.array(SuggestionSchema),
}).passthrough();

// Chart data schema
const ChartDataSchema = z.object({
  pace_series: z.array(z.object({
    t_ms: z.number(),
    speech_ms: z.number(),
  }).passthrough()),
  pause_series: z.array(z.object({
    start_ms: z.number(),
    end_ms: z.number(),
    duration_ms: z.number(),
  }).passthrough()),
}).passthrough();

// Highlights schema
const HighlightsSchema = z.array(z.object({
  start_ms: z.number(),
  end_ms: z.number(),
  type: z.string(),
  text_snippet: z.string(),
}).passthrough());

// Report view schema (optional)
const ReportViewSchema = z.object({
  chart_data: ChartDataSchema,
  highlights: HighlightsSchema,
}).passthrough();

// Warnings schema
const WarningsSchema = z.array(z.object({
  code: z.string(),
  message: z.string().optional(),
}).passthrough());

// ReportResponse schema
export const ReportResponseSchema = z.object({
  pol_version: z.string(),
  session: SessionSchema,
  scores: ScoresSchema,
  rule_engine: RuleEngineSchema,
  llm_feedback: LlmFeedbackSchema,
  report_view: ReportViewSchema.optional(),
  warnings: WarningsSchema,
}).passthrough();

export type ReportResponse = z.infer<typeof ReportResponseSchema>;
export type Trigger = z.infer<typeof TriggerSchema>;
export type Suggestion = z.infer<typeof SuggestionSchema>;
