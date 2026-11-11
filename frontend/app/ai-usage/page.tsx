"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  Bot,
  Clock3,
  Database,
  Loader2,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import {
  fetchAIUsageAnalytics,
  AIUsageAnalytics,
} from "@/lib/api";

function isAdminToken(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const role = String(
      payload.role ?? payload.role_name ?? ""
    ).toUpperCase();

    return role === "ADMIN";
  } catch {
    return false;
  }
}

function formatLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .replace(/\bSql\b/g, "SQL")
    .replace(/\bHr\b/g, "HR")
    .replace(/\bRag\b/g, "RAG")
    .replace(/\bAi\b/g, "AI");
}

function MetricCard({
  title,
  value,
  description,
  icon: Icon,
}: {
  title: string;
  value: string;
  description: string;
  icon: typeof Activity;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-[#10182b] p-5 shadow-lg">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-slate-400">{title}</p>
          <p className="mt-3 text-3xl font-semibold text-white">
            {value}
          </p>
        </div>

        <div className="rounded-xl bg-indigo-500/15 p-3">
          <Icon className="h-5 w-5 text-indigo-300" />
        </div>
      </div>

      <p className="mt-4 text-xs text-slate-500">
        {description}
      </p>
    </div>
  );
}

function UsageBars({
  title,
  items,
  nameKey,
}: {
  title: string;
  items: { count: number; [key: string]: unknown }[];
  nameKey: "intent" | "tool";
}) {
  const maximum = Math.max(
    1,
    ...items.map((item) => item.count)
  );

  return (
    <section className="rounded-2xl border border-slate-800 bg-[#10182b] p-5">
      <h2 className="text-lg font-semibold text-white">
        {title}
      </h2>

      {items.length === 0 ? (
        <p className="mt-6 text-sm text-slate-400">
          No usage data available yet.
        </p>
      ) : (
        <div className="mt-6 space-y-5">
          {items.map((item) => {
            const rawLabel = String(item[nameKey] ?? "Unknown");
            const label = formatLabel(rawLabel);
            const percentage = (item.count / maximum) * 100;

            return (
              <div key={label}>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="break-all text-sm text-slate-300">
                    {label}
                  </span>

                  <span className="shrink-0 text-sm font-medium text-white">
                    {item.count.toLocaleString()}
                  </span>
                </div>

                <div className="h-2.5 overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-indigo-500 transition-all"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default function AIUsagePage() {
  const router = useRouter();

  const [analytics, setAnalytics] =
    useState<AIUsageAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [name, setName] = useState("Administrator");
  const [authorized, setAuthorized] = useState(false);

  async function loadAnalytics(token: string) {
    setError("");
    setRefreshing(true);

    try {
      const response = await fetchAIUsageAnalytics(token);

      if (response.status === 401) {
        localStorage.removeItem("hrms_access_token");
        localStorage.removeItem("hrms_refresh_token");

        document.cookie =
          "hrms_auth=; path=/; max-age=0; samesite=lax";
        document.cookie =
          "hrms_role=; path=/; max-age=0; samesite=lax";

        router.push("/login");
        return;
      }

      if (response.status === 403) {
        setError(
          "Access denied. Only administrators can view AI usage analytics."
        );
        return;
      }

      const body = response.body;

      if (
        !response.ok ||
        !("success" in body) ||
        !body.success ||
        !body.data
      ) {
        const message =
          "error" in body && body.error?.message
            ? body.error.message
            : "Unable to load AI usage analytics.";

        setError(message);
        return;
      }

      setAnalytics(body.data);
    } catch {
      setError(
        "Unable to connect to the HRMS backend. Check that the backend is running."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    const token = localStorage.getItem("hrms_access_token");

    if (!token) {
      router.push("/login");
      return;
    }

    if (!isAdminToken(token)) {
      setLoading(false);
      setError(
        "This page is restricted to administrators."
      );
      return;
    }

    try {
      const payload = JSON.parse(atob(token.split(".")[1]));

      if (typeof payload.name === "string") {
        setName(payload.name);
      } else if (typeof payload.email === "string") {
        setName(payload.email);
      }
    } catch {
      // Keep the default name.
    }

    setAuthorized(true);
    void loadAnalytics(token);
    // Initial authentication check and data load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  function refresh() {
    const token = localStorage.getItem("hrms_access_token");

    if (!token) {
      router.push("/login");
      return;
    }

    if (!isAdminToken(token)) {
      setError("Administrator access is required.");
      return;
    }

    void loadAnalytics(token);
  }

  const ragPercentage = analytics
    ? (analytics.rag_no_answer_rate * 100).toFixed(1)
    : "0.0";

  return (
    <main className="flex min-h-screen bg-[#0b1020]">
      <Sidebar />

      <section className="flex min-w-0 flex-1 flex-col bg-[#060a16]">
        <Topbar name={name} title="AI Usage Dashboard" />

        <div className="space-y-6 p-4 md:p-6">
          <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <div className="flex items-center gap-2">
                <Bot className="h-7 w-7 text-indigo-400" />

                <h1 className="text-2xl font-semibold text-white">
                  AI Usage Analytics
                </h1>
              </div>

              <p className="mt-2 text-sm text-slate-400">
                Monitor AI requests, tool usage, latency,
                permission failures, and query safety.
              </p>
            </div>

            <button
              type="button"
              onClick={refresh}
              disabled={refreshing || !authorized}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-[#10182b] px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {refreshing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}

              Refresh
            </button>
          </header>

          {loading && (
            <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-[#10182b] p-8 text-slate-300">
              <Loader2 className="h-5 w-5 animate-spin text-indigo-400" />
              Loading AI analytics...
            </div>
          )}

          {!loading && error && (
            <div
              role="alert"
              className="flex items-start gap-3 rounded-2xl border border-red-900/70 bg-red-950/30 p-5 text-red-200"
            >
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />

              <div>
                <p className="font-medium">
                  Unable to display analytics
                </p>
                <p className="mt-1 text-sm">{error}</p>
              </div>
            </div>
          )}

          {!loading && analytics && authorized && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  title="Total AI Requests"
                  value={analytics.total_requests.toLocaleString()}
                  description="Recorded AI interactions"
                  icon={Activity}
                />

                <MetricCard
                  title="Permission Failures"
                  value={analytics.failed_permission_attempts.toLocaleString()}
                  description="Recorded denied permission attempts"
                  icon={ShieldAlert}
                />

                <MetricCard
                  title="Average Latency"
                  value={`${analytics.average_latency_ms.toFixed(2)} ms`}
                  description="Average of recorded latency measurements"
                  icon={Clock3}
                />

                <MetricCard
                  title="SQL Blocked Queries"
                  value={analytics.sql_blocked_queries.toLocaleString()}
                  description="SQL requests classified as blocked"
                  icon={Database}
                />
              </div>

              <div className="grid gap-5 xl:grid-cols-2">
                <UsageBars
                  title="Most Common Intents"
                  items={analytics.most_common_intents}
                  nameKey="intent"
                />

                <UsageBars
                  title="Most Used AI Tools"
                  items={analytics.most_used_tools}
                  nameKey="tool"
                />
              </div>

              <section className="rounded-2xl border border-slate-800 bg-[#10182b] p-5">
                <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                  <div>
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-indigo-300" />

                      <h2 className="text-lg font-semibold text-white">
                        Policy RAG Performance
                      </h2>
                    </div>

                    <p className="mt-2 text-sm text-slate-400">
                      Recorded policy retrieval activity and the
                      current no-answer proxy.
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-700 bg-slate-900/70 px-4 py-3">
                    <p className="text-xs text-slate-400">
                      No-answer rate (proxy)
                    </p>

                    <p className="mt-1 text-2xl font-semibold text-white">
                      {ragPercentage}%
                    </p>
                  </div>
                </div>

                <div className="mt-6 grid gap-4 sm:grid-cols-2">
                  <div className="rounded-xl bg-slate-900/60 p-4">
                    <p className="text-sm text-slate-400">
                      Requests counted
                    </p>

                    <p className="mt-2 text-2xl font-semibold text-white">
                      {analytics.rag_requests_counted.toLocaleString()}
                    </p>
                  </div>

                  <div className="rounded-xl bg-slate-900/60 p-4">
                    <p className="text-sm text-slate-400">
                      Requests with zero recorded sources
                    </p>

                    <p className="mt-2 text-2xl font-semibold text-white">
                      {analytics.rag_no_answer_count.toLocaleString()}
                    </p>
                  </div>
                </div>

                <p className="mt-4 text-xs leading-5 text-slate-500">
                  Note: Zero recorded sources is a proxy, not a
                  definitive indication that the AI did not answer.
                  Validate this metric against explicit RAG outcome
                  logging before using it as a quality KPI.
                </p>
              </section>

            </>
          )}
        </div>
      </section>
    </main>
  );
}