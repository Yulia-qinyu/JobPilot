import type {
  CandidateType,
  AnalysisResponse,
  DashboardData,
  DecisionJobPage,
  DecisionSummary,
  FitAnalysisState,
  FitAnalysisPreview,
  Job,
  JobCreatePayload,
  JobListItem,
  JobPreview,
  JobImportSession,
  JobStatus,
  StructuredJD,
  JobDecision,
  EligibilityStatus,
  RoleFamily,
  RolePriority,
  ResumeTailoringState,
  TailoringAction,
  UserProfile,
  DiscoveryResultPage,
  DiscoverySession,
  ApplicationStatusDefinition,
  JobSearchStrategy,
  PlanItem,
  PlanType,
  PlanningToday,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const ERROR_MESSAGES: Record<string, string> = {
  "Only PDF and DOCX resumes are supported.": "仅支持 PDF 和 DOCX 格式的简历。",
  "Resume must be 10 MB or smaller.": "简历文件不能超过 10 MB。",
  "The resume could not be read. Check that the file is valid.": "无法读取简历，请确认文件有效。",
  "No text was found in the resume. Scanned PDFs are not supported in V0.1.": "简历中没有可提取的文字，目前不支持扫描版 PDF。",
  "Claude did not return structured output.": "AI 未能返回有效的结构化结果，请重试。",
  "Claude returned data in an unexpected format.": "AI 返回的数据格式异常，请重试。",
  "Claude API request failed. Please try again.": "AI 分析请求失败，请稍后重试。",
  "You can save up to 5 target companies.": "最多可保存 5 家目标公司。",
  "You can save up to 5 target roles.": "最多可保存 5 个目标岗位。",
  "That target company is already saved.": "这家目标公司已经添加。",
  "That target role is already saved.": "这个目标岗位已经添加。",
};

function localizeError(detail: unknown): string {
  if (Array.isArray(detail)) return "输入内容有误，请检查后重试。";
  if (detail && typeof detail === "object" && "message" in detail) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }
  if (typeof detail === "string") {
    if (detail.startsWith("ANTHROPIC_API_KEY is not configured")) {
      return "尚未配置 Anthropic API Key。";
    }
    return ERROR_MESSAGES[detail] || "请求失败，请检查输入后重试。";
  }
  return "请求失败，请稍后重试。";
}

export class ApiError extends Error {
  code?: string;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const error = new ApiError(localizeError(payload?.detail));
    if (payload?.detail && typeof payload.detail === "object") {
      error.code = payload.detail.code;
    }
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error("无法连接 JobPilot API，请确认后端和数据库正在运行。");
  }
  return parseResponse<T>(response);
}

async function profileRequest(path = "", init?: RequestInit): Promise<UserProfile> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/profile${path}`, {
      ...init,
      headers: init?.body instanceof FormData
        ? init.headers
        : { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error("无法连接 JobPilot API，请确认后端和数据库正在运行。");
  }
  return parseResponse<UserProfile>(response);
}

export async function analyzeApplication(
  resume: File,
  targetPosition: string,
  jobDescription: string,
): Promise<AnalysisResponse> {
  const form = new FormData();
  form.append("resume", resume);
  form.append("target_position", targetPosition);
  form.append("job_description", jobDescription);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/analyze`, { method: "POST", body: form });
  } catch {
    throw new Error("无法连接 JobPilot API，请确认后端正在运行。");
  }

  return parseResponse<AnalysisResponse>(response);
}

export const profileApi = {
  get: () => profileRequest(),
  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("resume", file);
    return profileRequest("/resume", { method: "POST", body: form });
  },
  updateLocation: (preferred_location: string | null) =>
    profileRequest("/location", { method: "PUT", body: JSON.stringify({ preferred_location }) }),
  updateIdentity: (candidate_type: CandidateType | null, graduation_year: number | null) =>
    profileRequest("/identity", {
      method: "PUT",
      body: JSON.stringify({ candidate_type, graduation_year }),
    }),
  addCompany: (name: string) =>
    profileRequest("/companies", { method: "POST", body: JSON.stringify({ name }) }),
  updateCompany: (id: number, name: string) =>
    profileRequest(`/companies/${id}`, { method: "PUT", body: JSON.stringify({ name }) }),
  deleteCompany: (id: number) => profileRequest(`/companies/${id}`, { method: "DELETE" }),
  addRole: (name: string, priority: RolePriority) =>
    profileRequest("/roles", {
      method: "POST",
      body: JSON.stringify({ name, priority }),
    }),
  updateRole: (
    id: number,
    values: Partial<{
      name: string;
      priority: RolePriority;
      role_family_override: RoleFamily | null;
    }>,
  ) => profileRequest(`/roles/${id}`, { method: "PUT", body: JSON.stringify(values) }),
  deleteRole: (id: number) => profileRequest(`/roles/${id}`, { method: "DELETE" }),
  addFact: (experienceId: number, text: string) =>
    profileRequest(`/experiences/${experienceId}/facts`, {
      method: "POST",
      body: JSON.stringify({ text, confirmed: false }),
    }),
  updateFact: (id: number, values: { text?: string; confirmed?: boolean }) =>
    profileRequest(`/facts/${id}`, { method: "PUT", body: JSON.stringify(values) }),
  deleteFact: (id: number) => profileRequest(`/facts/${id}`, { method: "DELETE" }),
};

export const resumeTailoringApi = {
  get: (jobId: number) => apiRequest<ResumeTailoringState>(`/api/jobs/${jobId}/resume-tailoring`),
  createPlan: (jobId: number) => apiRequest<ResumeTailoringState>(`/api/jobs/${jobId}/resume-tailoring/plan`, { method: "POST" }),
  patchPlan: (jobId: number, payload: { items?: { plan_item_id: string; action: TailoringAction; omit_confirmed?: boolean }[]; section_order?: string[]; confirmed?: boolean }) => apiRequest<ResumeTailoringState>(`/api/jobs/${jobId}/resume-tailoring/plan`, { method: "PATCH", body: JSON.stringify(payload) }),
  generateDraft: (jobId: number) => apiRequest<ResumeTailoringState>(`/api/jobs/${jobId}/resume-tailoring/draft`, { method: "POST" }),
  editDraft: (jobId: number, items: { plan_item_id: string; text: string; keep_original?: boolean }[]) => apiRequest<ResumeTailoringState>(`/api/jobs/${jobId}/resume-tailoring/draft`, { method: "PATCH", body: JSON.stringify({ items }) }),
  validate: (jobId: number) => apiRequest<ResumeTailoringState>(`/api/jobs/${jobId}/resume-tailoring/validate`, { method: "POST" }),
  accept: (jobId: number) => apiRequest<ResumeTailoringState>(`/api/jobs/${jobId}/resume-tailoring/accept`, { method: "POST" }),
};

export const jobsApi = {
  previewUrl: (url: string) =>
    apiRequest<JobPreview>("/api/jobs/preview/url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),
  previewJd: (job_description: string) =>
    apiRequest<JobPreview>("/api/jobs/preview/jd", {
      method: "POST",
      body: JSON.stringify({ job_description }),
    }),
  analyzePreview: (structured_jd: StructuredJD) =>
    apiRequest<FitAnalysisPreview>("/api/jobs/preview/analysis", {
      method: "POST",
      body: JSON.stringify({ structured_jd }),
    }),
  create: (payload: JobCreatePayload) =>
    apiRequest<Job>("/api/jobs", { method: "POST", body: JSON.stringify(payload) }),
  list: (status = "all", sort = "recent") =>
    apiRequest<JobListItem[]>(
      `/api/jobs?status=${encodeURIComponent(status)}&sort=${encodeURIComponent(sort)}`,
    ),
  get: (id: number) => apiRequest<Job>(`/api/jobs/${id}`),
  delete: (id: number) => apiRequest<void>(`/api/jobs/${id}`, { method: "DELETE" }),
  update: (
    id: number,
    values: Partial<{
      company: string;
      role: string;
      location: string | null;
      recruitment_type: string | null;
      published_date: string | null;
      status: JobStatus;
      application_date: string | null;
      next_stage: string | null;
      interview_date: string | null;
      notes: string | null;
      structured_jd: StructuredJD;
      application_status_id: number;
    }>,
  ) => apiRequest<Job>(`/api/jobs/${id}`, { method: "PATCH", body: JSON.stringify(values) }),
};

export const workspaceApi = {
  getStrategy: () => apiRequest<{ job_search_strategy: JobSearchStrategy }>("/api/workspace/strategy"),
  updateStrategy: (job_search_strategy: JobSearchStrategy) => apiRequest<{ job_search_strategy: JobSearchStrategy }>("/api/workspace/strategy", { method: "PATCH", body: JSON.stringify({ job_search_strategy }) }),
  statuses: () => apiRequest<ApplicationStatusDefinition[]>("/api/workspace/application-statuses"),
  createStatus: (label: string) => apiRequest<ApplicationStatusDefinition>("/api/workspace/application-statuses", { method: "POST", body: JSON.stringify({ label }) }),
  updateStatus: (id: number, values: { label?: string; sort_order?: number }) => apiRequest<ApplicationStatusDefinition>(`/api/workspace/application-statuses/${id}`, { method: "PATCH", body: JSON.stringify(values) }),
  deleteStatus: (id: number, migrate_to_status_id?: number) => apiRequest<{ deleted_id: number; migrated_jobs: number }>(`/api/workspace/application-statuses/${id}`, { method: "DELETE", body: JSON.stringify({ migrate_to_status_id: migrate_to_status_id ?? null }) }),
  plans: () => apiRequest<PlanItem[]>("/api/workspace/plan-items"),
  createPlan: (payload: { title: string; date: string; time_optional?: string | null; job_id?: number | null; type: PlanType; notes?: string | null }) => apiRequest<PlanItem>("/api/workspace/plan-items", { method: "POST", body: JSON.stringify(payload) }),
  updatePlan: (id: number, payload: Partial<{ title: string; date: string; time_optional: string | null; job_id: number | null; type: PlanType; status: "todo" | "done"; notes: string | null }>) => apiRequest<PlanItem>(`/api/workspace/plan-items/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deletePlan: (id: number) => apiRequest<void>(`/api/workspace/plan-items/${id}`, { method: "DELETE" }),
};

export const planningApi = {
  today: () => apiRequest<PlanningToday>("/api/planning/today"),
  generate: (force_regenerate = false) => apiRequest<PlanningToday>("/api/planning/today", {
    method: "POST",
    body: JSON.stringify({ force_regenerate }),
  }),
  addToPlan: (snapshotId: number, itemId: string, values?: { title?: string; date?: string }) =>
    apiRequest<PlanItem>(`/api/planning/snapshots/${snapshotId}/items/${encodeURIComponent(itemId)}/add-to-plan`, {
      method: "POST",
      body: JSON.stringify(values ?? {}),
    }),
};

export const jobImportsApi = {
  create: (search_url: string) =>
    apiRequest<JobImportSession>("/api/job-imports", {
      method: "POST",
      body: JSON.stringify({ search_url }),
    }),
  get: (id: number) => apiRequest<JobImportSession>(`/api/job-imports/${id}`),
  jobs: (id: number) =>
    apiRequest<{ session_id: number; jobs: JobListItem[] }>(`/api/job-imports/${id}/jobs`),
};

export const fitAnalysisApi = {
  get: (jobId: number) => apiRequest<FitAnalysisState>(`/api/jobs/${jobId}/analysis`),
  run: (jobId: number) =>
    apiRequest<FitAnalysisState>(`/api/jobs/${jobId}/analysis`, { method: "POST" }),
};

export const jobDecisionsApi = {
  list: (params: URLSearchParams) =>
    apiRequest<DecisionJobPage>(`/api/job-decisions?${params.toString()}`),
  summary: () => apiRequest<DecisionSummary>("/api/job-decisions/summary"),
  get: (jobId: number) => apiRequest<JobDecision>(`/api/jobs/${jobId}/decision`),
  override: (
    jobId: number,
    values: {
      role_family_override?: RoleFamily | null;
      eligibility_override?: EligibilityStatus | null;
      eligibility_override_reason?: string | null;
    },
  ) => apiRequest<JobDecision>(`/api/jobs/${jobId}/decision`, {
    method: "PATCH",
    body: JSON.stringify(values),
  }),
  recompute: (job_ids?: number[]) =>
    apiRequest<{ requested: number; processed: number; failed: number; elapsed_seconds: number; claude_api_calls: 0 }>(
      "/api/job-decisions/recompute",
      { method: "POST", body: JSON.stringify({ job_ids: job_ids ?? null }) },
    ),
};

export const dashboardApi = {
  get: () => apiRequest<DashboardData>("/api/dashboard"),
};

export const discoveryApi = {
  create: (input: string, personalizationEnabled = false) => apiRequest<DiscoverySession>("/api/discovery/sessions", {
    method: "POST",
    body: JSON.stringify({ input, personalization_enabled: personalizationEnabled }),
  }),
  search: (sessionId: string) => apiRequest<DiscoverySession>(
    `/api/discovery/sessions/${sessionId}/search`,
    { method: "POST" },
  ),
  updateContext: (
    sessionId: string,
    payload: { selected_tag_ids?: string[]; exclusions?: string[]; skip_refinement?: boolean; personalization_enabled?: boolean },
  ) => apiRequest<DiscoverySession>(`/api/discovery/sessions/${sessionId}/context`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }),
  get: (sessionId: string) => apiRequest<DiscoverySession>(
    `/api/discovery/sessions/${sessionId}`,
  ),
  results: (sessionId: string, params: URLSearchParams) => apiRequest<DiscoveryResultPage>(
    `/api/discovery/sessions/${sessionId}/results?${params.toString()}`,
  ),
  add: (sessionId: string, resultId: string) => apiRequest<{
    outcome: "created" | "existing" | "updated";
    persistent_job_id: number;
    claude_api_calls: 0;
    phase3_calls: 0;
  }>(`/api/discovery/sessions/${sessionId}/results/${resultId}/my-job`, { method: "POST" }),
};
