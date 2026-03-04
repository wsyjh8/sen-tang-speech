"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useReportStore } from "@/store/report-store";
import type { Trigger, Suggestion } from "@/lib/schemas";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function ReportPage() {
  const router = useRouter();
  const report = useReportStore((state) => state.report);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // 如果没有报告数据，返回首页
  if (!report) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-gray-600 mb-4">暂无报告数据</p>
          <button
            onClick={() => router.push("/practice")}
            className="py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            返回练习页
          </button>
        </div>
      </div>
    );
  }

  const { scores, rule_engine, llm_feedback, report_view, warnings, session } = report;

  const topTrigger = rule_engine.top_trigger_id
    ? rule_engine.triggers.find((t) => t.id === rule_engine.top_trigger_id)
    : null;

  const topSuggestion = llm_feedback.suggestions[0];

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-800">报告详情</h1>
          <button
            onClick={() => router.push("/practice")}
            className="py-2 px-4 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
          >
            返回练习页
          </button>
        </div>

        {/* Warnings Banner */}
        {warnings && warnings.length > 0 && (
          <div className="mb-6 p-4 bg-yellow-100 border border-yellow-400 rounded-lg">
            <h3 className="font-semibold text-yellow-800 mb-2">警告</h3>
            <ul className="space-y-1">
              {warnings.map((w, idx) => (
                <li key={idx} className="text-yellow-700 text-sm">
                  <span className="font-mono bg-yellow-200 px-2 py-0.5 rounded">{w.code}</span>
                  {w.message && <span className="ml-2">{w.message}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Overall Score */}
        <div className="mb-6 p-6 bg-white rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">综合评分</h2>
          <div className="flex items-center">
            <div className="text-6xl font-bold text-blue-600">{scores.overall}</div>
            <span className="text-2xl text-gray-500 ml-2">/ 100</span>
          </div>
        </div>

        {/* Session Info */}
        <div className="mb-6 p-6 bg-white rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">会话信息</h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Session ID:</span>
              <span className="ml-2 font-mono">{session.session_id}</span>
            </div>
            <div>
              <span className="text-gray-500">任务类型:</span>
              <span className="ml-2">{session.task_type}</span>
            </div>
            <div>
              <span className="text-gray-500">语言:</span>
              <span className="ml-2">{session.language}</span>
            </div>
            <div>
              <span className="text-gray-500">生成时间:</span>
              <span className="ml-2">{session.generated_at}</span>
            </div>
          </div>
        </div>

        {/* Top1 Trigger & Suggestion */}
        <div className="mb-6 p-6 bg-white rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">Top1 建议</h2>
          
          {rule_engine.top_trigger_id ? (
            <div className="space-y-6">
              {/* Top Trigger Info */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-semibold text-gray-700 mb-2">触发规则</h3>
                <div className="text-sm space-y-2">
                  <div>
                    <span className="text-gray-500">Trigger ID:</span>
                    <span className="ml-2 font-mono">{rule_engine.top_trigger_id}</span>
                  </div>
                  {topTrigger && (
                    <>
                      <div>
                        <span className="text-gray-500">严重等级:</span>
                        <span className={`ml-2 px-2 py-0.5 rounded text-xs font-semibold ${
                          topTrigger.severity === "P0" ? "bg-red-200 text-red-800" :
                          topTrigger.severity === "P1" ? "bg-orange-200 text-orange-800" :
                          "bg-yellow-200 text-yellow-800"
                        }`}>
                          {topTrigger.severity}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">影响分数:</span>
                        <span className="ml-2">{topTrigger.impact_score}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">优先级分数:</span>
                        <span className="ml-2">{topTrigger.priority_score}</span>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Top Suggestion */}
              {topSuggestion && (
                <SuggestionCard suggestion={topSuggestion} />
              )}
            </div>
          ) : (
            <div className="p-4 bg-gray-100 rounded-lg text-center text-gray-500">
              无触发规则
            </div>
          )}
        </div>

        {/* Chart Section */}
        <div className="mb-6 p-6 bg-white rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">图表数据</h2>
          
          {report_view ? (
            <div className="space-y-6">
              {/* Pace Series Chart */}
              {mounted && report_view.chart_data?.pace_series && report_view.chart_data.pace_series.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">语速趋势</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={report_view.chart_data.pace_series}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis 
                          dataKey="t_ms" 
                          label={{ value: "时间 (ms)", position: "insideBottom", offset: -5 }}
                        />
                        <YAxis 
                          label={{ value: "语速", angle: -90, position: "insideLeft" }}
                        />
                        <Tooltip />
                        <Line type="monotone" dataKey="speech_ms" stroke="#3b82f6" strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Pause Series List */}
              {report_view.chart_data?.pause_series && report_view.chart_data.pause_series.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">停顿列表</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-100">
                        <tr>
                          <th className="px-4 py-2 text-left">开始 (ms)</th>
                          <th className="px-4 py-2 text-left">结束 (ms)</th>
                          <th className="px-4 py-2 text-left">时长 (ms)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report_view.chart_data.pause_series.map((pause, idx) => (
                          <tr key={idx} className="border-t">
                            <td className="px-4 py-2 font-mono">{pause.start_ms}</td>
                            <td className="px-4 py-2 font-mono">{pause.end_ms}</td>
                            <td className="px-4 py-2 font-mono">{pause.duration_ms}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Highlights */}
              {report_view.highlights && report_view.highlights.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-700 mb-2">高亮片段</h3>
                  <div className="space-y-2">
                    {report_view.highlights.map((h, idx) => (
                      <div key={idx} className="p-3 bg-blue-50 rounded border border-blue-200">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="px-2 py-0.5 bg-blue-200 text-blue-800 text-xs rounded">
                            {h.type}
                          </span>
                          <span className="text-xs text-gray-500 font-mono">
                            {h.start_ms} - {h.end_ms}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700">{h.text_snippet}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 bg-gray-100 rounded-lg text-center text-gray-500">
              本次未生成图表（降级）
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SuggestionCard({ suggestion }: { suggestion: Suggestion }) {
  return (
    <div className="p-4 border border-gray-200 rounded-lg">
      <h3 className="font-semibold text-lg text-gray-800 mb-3">{suggestion.title}</h3>
      
      <div className="space-y-3">
        <div>
          <h4 className="font-medium text-gray-700 text-sm">问题</h4>
          <p className="text-gray-600 text-sm mt-1">{suggestion.problem}</p>
        </div>
        
        <div>
          <h4 className="font-medium text-gray-700 text-sm">原因</h4>
          <p className="text-gray-600 text-sm mt-1">{suggestion.cause}</p>
        </div>

        {/* Evidence Ref */}
        <div className="p-3 bg-gray-50 rounded">
          <h4 className="font-medium text-gray-700 text-sm mb-2">证据参考</h4>
          {suggestion.evidence_ref.time_ranges && suggestion.evidence_ref.time_ranges.length > 0 ? (
            <div className="space-y-1">
              {suggestion.evidence_ref.time_ranges.map((range, idx) => (
                <div key={idx} className="text-xs font-mono text-gray-600">
                  {range.start_ms} - {range.end_ms} ms
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm italic">降级：暂无证据片段</p>
          )}
          {suggestion.evidence_ref.text_snippets && suggestion.evidence_ref.text_snippets.length > 0 && (
            <div className="mt-2 space-y-1">
              {suggestion.evidence_ref.text_snippets.map((snippet, idx) => (
                <p key={idx} className="text-xs text-gray-500 italic">
                  "{snippet}"
                </p>
              ))}
            </div>
          )}
        </div>

        {/* Drill */}
        <div className="p-3 bg-blue-50 rounded">
          <h4 className="font-medium text-blue-700 text-sm mb-2">训练计划</h4>
          <div className="text-sm text-gray-700">
            <div className="mb-2">
              <span className="text-gray-500">Drill ID:</span>
              <span className="ml-2 font-mono">{suggestion.drill.drill_id}</span>
            </div>
            <div className="mb-2">
              <span className="text-gray-500">时长:</span>
              <span className="ml-2">{suggestion.drill.duration_sec} 秒</span>
            </div>
            {suggestion.drill.steps && suggestion.drill.steps.length > 0 && (
              <div className="mb-2">
                <span className="text-gray-500">步骤:</span>
                <ol className="list-decimal list-inside mt-1 space-y-1">
                  {suggestion.drill.steps.map((step, idx) => (
                    <li key={idx} className="text-gray-600">{step}</li>
                  ))}
                </ol>
              </div>
            )}
            {suggestion.drill.tips && suggestion.drill.tips.length > 0 && (
              <div>
                <span className="text-gray-500">提示:</span>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  {suggestion.drill.tips.map((tip, idx) => (
                    <li key={idx} className="text-gray-600">{tip}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Acceptance */}
        <div className="p-3 bg-green-50 rounded">
          <h4 className="font-medium text-green-700 text-sm mb-2">验收标准</h4>
          <div className="text-sm text-gray-700 space-y-1">
            <div>
              <span className="text-gray-500">指标:</span>
              <span className="ml-2">{suggestion.acceptance.metric}</span>
            </div>
            <div>
              <span className="text-gray-500">目标:</span>
              <span className="ml-2 font-semibold">{String(suggestion.acceptance.target)}</span>
            </div>
            <div>
              <span className="text-gray-500">测量方法:</span>
              <span className="ml-2">{suggestion.acceptance.how_to_measure}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
