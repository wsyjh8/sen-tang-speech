import { ReportResponseSchema, type ReportResponse } from "@/lib/schemas";

const API_BASE = "/api";

// 默认测试音频路径（从环境变量读取，可修改）
const DEFAULT_AUDIO_PATH = process.env.NEXT_PUBLIC_DEFAULT_AUDIO_PATH 
  || "D:/code/AI/startUp/sen-tang-speech/mvp/phase1_test/artifacts/test_16k.wav";

export async function fetchReportDemo(audioPath?: string): Promise<ReportResponse> {
  const audio = audioPath || DEFAULT_AUDIO_PATH;
  const url = `${API_BASE}/pipeline/step1_6_demo?audio=${encodeURIComponent(audio)}&use_llm=0`;
  
  const res = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    if (res.status === 404 || res.status === 405) {
      throw new Error("后端暂不支持上传，已使用 demo");
    }
    throw new Error(`API request failed: ${res.status} ${res.statusText}`);
  }

  const data = await res.json();

  // 使用 zod 解析，passthrough 已配置，容忍多余字段
  const result = ReportResponseSchema.parse(data);
  return result;
}
