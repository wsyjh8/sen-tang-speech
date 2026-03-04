import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// 增加超时时间到 5 分钟
export const maxDuration = 300;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
    const url = apiBaseUrl + "/pipeline/run_from_upload";
    
    // 使用 AbortController 设置更长的超时
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 300000); // 5 分钟
    
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    
    clearTimeout(timeout);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.error || "分析失败" },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return NextResponse.json(
        { error: "分析超时，请稍后重试" },
        { status: 504 }
      );
    }
    console.error("API Route error:", error);
    return NextResponse.json(
      { error: "内部错误" },
      { status: 500 }
    );
  }
}
