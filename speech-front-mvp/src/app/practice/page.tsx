"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { fetchReportDemo } from "@/lib/api";
import { useReportStore } from "@/store/report-store";

export default function PracticePage() {
  const router = useRouter();
  const setReport = useReportStore((state) => state.setReport);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFetchDemo = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const report = await fetchReportDemo();
      setReport(report);
      router.push("/report");
    } catch (err) {
      setError(err instanceof Error ? err.message : "未知错误");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center mb-6">练习模式</h1>
        <p className="text-gray-600 text-center mb-6">
          点击下方按钮拉取 demo 报告数据进行测试
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
            {error}
          </div>
        )}

        <button
          onClick={handleFetchDemo}
          disabled={isLoading}
          className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold rounded-lg transition-colors"
        >
          {isLoading ? "拉取中..." : "拉取 demo 报告"}
        </button>
      </div>
    </div>
  );
}
