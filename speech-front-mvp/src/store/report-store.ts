import { create } from "zustand";
import type { ReportResponse } from "@/lib/schemas";

interface ReportStore {
  report: ReportResponse | null;
  setReport: (report: ReportResponse | null) => void;
}

export const useReportStore = create<ReportStore>((set) => ({
  report: null,
  setReport: (report) => set({ report }),
}));
