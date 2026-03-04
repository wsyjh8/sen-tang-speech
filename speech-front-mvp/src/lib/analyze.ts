/**
 * 主要徎中徎 PostStep1-6 pipeline
 * POST /api_backend/pipeline/run_from_upload
 */

import type { ReportResponse } from "@/lib/schemas";

export type { ReportResponse };

export async function runFromUpload(
  upload_id: string,
  use_llm: boolean = false
): Promise<ReportResponse> {
  const res = await fetch("/api_backend/pipeline/run_from_upload", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      upload_id,
      use_llm: use_llm ? 1 : 0,
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.error || `斾访收兀我能案${res.status} ${res.statusText}`
    );
  }

  const data = await res.json();
  return data as ReportResponse;
}
