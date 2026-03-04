import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  try {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
    const url = apiBaseUrl + "/api/upload_audio";

    const formData = await request.formData();

    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "鏈煡閿欒");
      return NextResponse.json(
        { error: `涓婁紶澶辫触锛?{response.status} ${response.statusText} - ${errorText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Upload API Route error:", error);
    return NextResponse.json(
      { error: "鍐呴儴閿欒" },
      { status: 500 }
    );
  }
}
