"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Mail,
  Linkedin,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  Archive,
  TrendingUp,
  Activity,
  RefreshCw,
  Zap,
  AlertCircle,
} from "lucide-react";

interface VaultStats {
  timestamp: string;
  vault_path: string;
  directories: {
    Needs_Action: { total: number; categories: Record<string, number> };
    Pending_Approval: { total: number; categories: Record<string, number> };
    Approved: { total: number; categories: Record<string, number> };
    Done: { total: number; categories: Record<string, number> };
    Rejected: { total: number; categories: Record<string, number> };
    Archive: { total: number; categories: Record<string, number> };
    Plans: { total: number; categories: Record<string, number> };
  };
}

interface Activity {
  timestamp: string;
  message: string;
}

interface LoopStatus {
  enabled: boolean;
  total_processed: number;
  total_created: number;
  recent_actions: Array<{
    timestamp: string;
    source_files: string[];
    created_file: string;
    reasoning: string;
  }>;
}

interface DashboardData {
  timestamp: string;
  stats: VaultStats;
  recent_activity: Activity[];
  loop_status: LoopStatus;
}

interface MetricCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  subCategories?: Record<string, number>;
  onClick?: () => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function MetricCard({
  title,
  value,
  icon,
  color,
  subCategories,
  onClick,
}: MetricCardProps) {
  return (
    <div
      onClick={onClick}
      className={`bg-gradient-to-br ${color} rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 cursor-pointer transform hover:-translate-y-1 ${onClick ? "cursor-pointer" : ""
        }`}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="p-3 bg-white/20 rounded-xl">{icon}</div>
        <span className="text-4xl font-bold text-white">{value}</span>
      </div>
      <h3 className="text-lg font-semibold text-white/90">{title}</h3>
      {subCategories && Object.keys(subCategories).length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {Object.entries(subCategories).map(([cat, count]) => (
            <span
              key={cat}
              className="px-2 py-1 bg-white/20 rounded-lg text-xs text-white"
            >
              {cat}: {count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function ActivityItem({ timestamp, message }: Activity) {
  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
      <div className="p-2 bg-blue-100 rounded-lg">
        <Activity className="w-4 h-4 text-blue-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 font-medium truncate">{message}</p>
        <p className="text-xs text-gray-500 mt-1">{timestamp}</p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setIsRefreshing(true);
      const res = await fetch(`${API_URL}/api/dashboard`);
      if (!res.ok) throw new Error("Failed to fetch dashboard data");
      const json = await res.json();
      setData(json);
      setError(null);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsRefreshing(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-500 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-400">Loading Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center bg-red-900/30 rounded-2xl p-8">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <p className="text-red-400 text-lg">Failed to connect to API</p>
          <p className="text-gray-500 text-sm mt-2">Make sure api_server.py is running on port 8000</p>
          <button
            onClick={fetchData}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const stats = data?.stats;
  const recentActivity = data?.recent_activity || [];
  const loopStatus = data?.loop_status;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="bg-gray-900/80 backdrop-blur-sm border-b border-gray-700 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">AI Employee Dashboard</h1>
              <p className="text-xs text-gray-400">Autonomous Task Management System</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
              <span>Updated {lastRefresh.toLocaleTimeString()}</span>
            </div>
            <button
              onClick={fetchData}
              className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-5 h-5 text-gray-400 ${isRefreshing ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Metric Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Needs Action"
            value={stats?.directories.Needs_Action.total || 0}
            icon={<Clock className="w-6 h-6 text-white" />}
            color="from-amber-600 to-orange-500"
            subCategories={stats?.directories.Needs_Action.categories}
          />
          <MetricCard
            title="Pending Approval"
            value={stats?.directories.Pending_Approval.total || 0}
            icon={<FileText className="w-6 h-6 text-white" />}
            color="from-blue-600 to-cyan-500"
            subCategories={stats?.directories.Pending_Approval.categories}
          />
          <MetricCard
            title="Successfully Executed"
            value={stats?.directories.Done.total || 0}
            icon={<CheckCircle className="w-6 h-6 text-white" />}
            color="from-emerald-600 to-green-500"
            subCategories={stats?.directories.Done.categories}
          />
          <MetricCard
            title="Rejected Tasks"
            value={stats?.directories.Rejected.total || 0}
            icon={<XCircle className="w-6 h-6 text-white" />}
            color="from-red-600 to-rose-500"
            subCategories={stats?.directories.Rejected.categories}
          />
        </div>

        {/* Secondary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-6 border border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-purple-500/20 rounded-xl">
                <TrendingUp className="w-5 h-5 text-purple-400" />
              </div>
              <span className="text-gray-400 text-sm">In Execution</span>
            </div>
            <p className="text-3xl font-bold text-white">
              {stats?.directories.Approved.total || 0}
            </p>
            <p className="text-xs text-gray-500 mt-2">Tasks ready for MCP execution</p>
          </div>

          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-6 border border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-gray-600/20 rounded-xl">
                <Archive className="w-5 h-5 text-gray-400" />
              </div>
              <span className="text-gray-400 text-sm">Archived</span>
            </div>
            <p className="text-3xl font-bold text-white">
              {stats?.directories.Archive.total || 0}
            </p>
            <p className="text-xs text-gray-500 mt-2">Original trigger files archived</p>
          </div>

          {/* Ralph Wiggum Loop Status */}
          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-6 border border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-cyan-500/20 rounded-xl">
                <Zap className="w-5 h-5 text-cyan-400" />
              </div>
              <span className="text-gray-400 text-sm">Ralph Wiggum Loop</span>
              <span className={`px-2 py-1 rounded-full text-xs ${loopStatus?.enabled ? "bg-green-500/20 text-green-400" : "bg-gray-600/20 text-gray-400"
                }`}>
                {loopStatus?.enabled ? "Active" : "Paused"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-2xl font-bold text-white">
                  {loopStatus?.total_processed || 0}
                </p>
                <p className="text-xs text-gray-500">Tasks Analyzed</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-cyan-400">
                  {loopStatus?.total_created || 0}
                </p>
                <p className="text-xs text-gray-500">Follow-ups Created</p>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Activity Feed */}
          <div className="lg:col-span-2 bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700">
            <div className="p-6 border-b border-gray-700">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-400" />
                  Recent Activity
                </h2>
                <span className="text-sm text-gray-500">Last 24 hours</span>
              </div>
            </div>
            <div className="p-6 space-y-3 max-h-96 overflow-y-auto">
              {recentActivity.length > 0 ? (
                recentActivity.map((activity, idx) => (
                  <ActivityItem key={idx} {...activity} />
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No recent activity</p>
                </div>
              )}
            </div>
          </div>

          {/* Category Breakdown */}
          <div className="bg-gray-800/50 backdrop-blur rounded-2xl border border-gray-700">
            <div className="p-6 border-b border-gray-700">
              <h2 className="text-lg font-semibold text-white">Category Breakdown</h2>
            </div>
            <div className="p-6 space-y-6">
              {/* Email */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Mail className="w-4 h-4 text-blue-400" />
                    <span className="text-sm text-gray-300">Email</span>
                  </div>
                  <span className="text-sm font-medium text-white">
                    {(stats?.directories.Done.categories.email || 0) +
                      (stats?.directories.Pending_Approval.categories.email || 0)}
                  </span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-400"
                    style={{
                      width: `${Math.min(100, ((stats?.directories.Done.categories.email || 0) +
                        (stats?.directories.Pending_Approval.categories.email || 0)) * 10)}%`,
                    }}
                  />
                </div>
              </div>

              {/* LinkedIn */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Linkedin className="w-4 h-4 text-sky-400" />
                    <span className="text-sm text-gray-300">LinkedIn</span>
                  </div>
                  <span className="text-sm font-medium text-white">
                    {(stats?.directories.Done.categories.linkedin || 0) +
                      (stats?.directories.Pending_Approval.categories.linkedin || 0)}
                  </span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-sky-500 to-blue-400"
                    style={{
                      width: `${Math.min(100, ((stats?.directories.Done.categories.linkedin || 0) +
                        (stats?.directories.Pending_Approval.categories.linkedin || 0)) * 10)}%`,
                    }}
                  />
                </div>
              </div>

              {/* Accounting */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-gray-300">Accounting</span>
                  </div>
                  <span className="text-sm font-medium text-white">
                    {(stats?.directories.Done.categories.accounting || 0) +
                      (stats?.directories.Pending_Approval.categories.accounting || 0)}
                  </span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-green-400"
                    style={{
                      width: `${Math.min(100, ((stats?.directories.Done.categories.accounting || 0) +
                        (stats?.directories.Pending_Approval.categories.accounting || 0)) * 10)}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-8 text-center text-gray-500 text-sm">
          <p>AI Employee Dashboard v1.0 • Human-in-the-Loop Architecture</p>
          <p className="mt-1 text-xs">
            Vault: {data?.stats?.vault_path || "Loading..."}
          </p>
        </footer>
      </main>
    </div>
  );
}