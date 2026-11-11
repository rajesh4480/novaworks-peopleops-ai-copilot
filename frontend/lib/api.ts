const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type LoginResponse = {
  success: boolean;
  data: {
    access_token: string;
    refresh_token: string;
    token_type: string;
  };
  error: { code: string; message: string } | null;
};

export type Employee = {
  id: number;
  name: string;
  email: string;
  department_id: number | null;
  role: string;
  status: string;
  joining_date: string;
  phone?: string | null;
  address?: string | null;
  blood_type?: string | null;
  occupancy?: string | null;
};

export type Profile = {
  id: number;
  name: string;
  email: string;
  department_id: number | null;
  role: string;
  status: string;
  joining_date: string;
  date_of_birth: string | null;
  phone: string | null;
  address: string | null;
  blood_type: string | null;
  occupancy: string | null;
  has_profile_photo?: boolean;
};

export type EmployeeDetails = {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  role: string;
  status: string;
  department_id?: number | null;
  department: string | null;
  location: string | null;
  job_title: string | null;
  date_of_birth?: string | null;
  blood_type?: string | null;
  occupancy?: string | null;
  address: string | null;
  joining_date: string;
  current_salary_usd?: number | null;
  bank_name?: string | null;
  bank_account_number?: string | null;
  bank_account_name?: string | null;
  bank_branch?: string | null;
  bank_ifsc?: string | null;
  pan_number?: string | null;
  pan_name?: string | null;
  pan_dob?: string | null;
  pf_uan?: string | null;
  esi_no?: string | null;
  has_profile_photo?: boolean;
  projects?: Array<{
    id: number;
    name: string;
    description: string | null;
    role_on_project: string | null;
  }>;
};

export type ProjectCatalogItem = {
  id: number;
  name: string;
  description: string | null;
  status: "ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED";
};

export type EmployeeProjectItem = {
  project_id: number;
  project_name: string;
  project_description: string | null;
  project_status: "ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED";
  role_on_project: string | null;
};

export type DepartmentOption = {
  id: number;
  name: string;
  location: string;
};

export type AttendanceLog = {
  id: number;
  date: string;
  clock_in: string | null;
  clock_out: string | null;
  status: string;
  work_mode?: string | null;
  punctuality?: string | null;
};

export type LeaveBalance = {
  id: number;
  leave_type: string;
  total: number;
  used: number;
  remaining: number;
};

export type LeaveRequest = {
  id: number;
  employee_id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  is_half_day?: boolean;
  half_day_period?: "FIRST_HALF" | "SECOND_HALF" | null;
  reason: string;
  status: string;
  approver_id: number | null;
};

export type Announcement = {
  id: number;
  title: string;
  body: string;
  author_id: number;
  author_name: string;
  created_at: string;
};

export type HRPolicy = {
  id: number;
  title: string;
  category: string;
  content?: string | null;
  original_filename?: string | null;
  file_path?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
  uploaded_by?: number | null;
  checksum?: string | null;
  created_at?: string | null;
};

export type TeamCalendarDay = {
  date: string;
  day: number;
  weekday: string;
};

export type Holiday = {
  name: string;
  date: string;
};

export type Birthday = {
  name: string;
  team: string;
  date: string;
};

export type TeamCalendarItem = {
  employee_id: number;
  employee_name: string;
  employee_role: string;
  markers: Record<string, "LEAVE" | "WFH">;
};

export type OnboardingTask = {
  id: number;
  ticket_id: number;
  task_name: string;
  is_completed: boolean;
  due_date: string | null;
};

export type Ticket = {
  id: number;
  employee_id: number;
  assignee_id: number | null;
  title: string;
  description: string;
  category: "IT" | "HR" | "ONBOARDING";
  priority: "LOW" | "MEDIUM" | "HIGH";
  status: "OPEN" | "IN_PROGRESS" | "RESOLVED";
  created_at: string;
  onboarding_tasks?: OnboardingTask[];
};

export type PayrollRecord = {
  id: number;
  month: string;
  gross: number;
  deductions: Record<string, number>;
  net: number;
  pan: string;
  pf_uan: string | null;
  esi_no: string | null;
};

export type StatutoryDetails = {
  employee_id: number;
  pan: string | null;
  pf_uan: string | null;
  esi_no: string | null;
};

export type FinanceProfile = {
  employee_id: number;
  current_salary_usd: number | null;
  bank_name: string | null;
  bank_account_number: string | null;
  bank_account_name: string | null;
  bank_branch: string | null;
  bank_ifsc: string | null;
  pan_number: string | null;
  pan_name: string | null;
  pan_dob: string | null;
};

export type Poll = {
  id: number;
  question: string;
  options: string[];
  created_by: number;
  created_at: string;
  my_vote: number | null;
};

export type PollResultItem = {
  option_index: number;
  option: string;
  votes: number;
  percentage: number;
};

export type JobHistoryItem = {
  id: number;
  designation: string;
  business_unit: string;
  department: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
};

export type EmployeeDocument = {
  id: string;
  title: string;
  type: "APPOINTMENT" | "PAYSLIP" | "TAX" | "OTHER";
  uploaded_by?: number | null;
  issued_on: string;
  original_filename?: string;
  mime_type?: string;
  size_bytes?: number;
  created_at?: string;
};

export type OrgNode = {
  id: number;
  name: string;
  role: string;
  manager_id: number | null;
  children: OrgNode[];
};

export type ApiEnvelope<T> = {
  success: boolean;
  data: T;
  error: { code: string; message: string } | null;
};

export type EmployeesPayload = {
  items: Employee[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
};

export type EmployeeCreatePayload = {
  name: string;
  email: string;
  password: string;
  department_id?: number;
  role?: "ADMIN" | "MANAGER" | "EMPLOYEE";
  joining_date: string;
  date_of_birth?: string;
  phone?: string;
  address?: string;
  blood_type?: string;
  occupancy?: string;
  job_title?: string;
  current_salary_usd?: number;
  bank_name?: string;
  bank_account_number?: string;
  bank_account_name?: string;
  bank_branch?: string;
  bank_ifsc?: string;
  pan_number?: string;
  pan_name?: string;
  pan_dob?: string;
  pf_uan?: string;
  esi_no?: string;
};

export type EmployeeUpdatePayload = {
  name?: string;
  email?: string;
  password?: string;
  department_id?: number;
  role?: "ADMIN" | "MANAGER" | "EMPLOYEE";
  joining_date?: string;
  date_of_birth?: string;
  phone?: string;
  occupancy?: string;
  job_title?: string;
  current_salary_usd?: number;
  bank_name?: string;
  bank_account_number?: string;
  bank_account_name?: string;
  bank_branch?: string;
  bank_ifsc?: string;
  pan_number?: string;
  pan_name?: string;
  pan_dob?: string;
  pf_uan?: string;
  esi_no?: string;
};


export type PaginatedPayload<T> = {
  items: T[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
};

export type ApiResult<T> = {
  ok: boolean;
  status: number;
  body: T;
};

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  return response.json();
}

export async function fetchEmployees(
  token: string,
  options?: { location?: string; department_id?: number; q?: string; limit?: number; offset?: number }
): Promise<ApiResult<ApiEnvelope<EmployeesPayload> | { detail?: unknown }>> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 20),
    offset: String(options?.offset ?? 0),
  });
  if (options?.location) {
    params.set("location", options.location);
  }
  if (typeof options?.department_id === "number") {
    params.set("department_id", String(options.department_id));
  }
  if (options?.q) {
    params.set("q", options.q);
  }

  const response = await fetch(`${API_BASE}/api/v1/employees?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function createEmployee(
  token: string,
  payload: EmployeeCreatePayload
): Promise<ApiResult<ApiEnvelope<Employee> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function updateEmployee(
  token: string,
  employeeId: number,
  payload: EmployeeUpdatePayload
): Promise<ApiResult<ApiEnvelope<{ id: number; status: string }> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchProjectsCatalog(
  token: string
): Promise<ApiResult<ApiEnvelope<ProjectCatalogItem[]> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/projects/catalog`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function createProjectCatalogItem(
  token: string,
  payload: { name: string; description?: string; status?: "ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED" }
): Promise<ApiResult<ApiEnvelope<ProjectCatalogItem> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/projects/catalog`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function updateProjectCatalogStatus(
  token: string,
  projectId: number,
  statusValue: "ONGOING" | "COMPLETED" | "ON_HOLD" | "PLANNED"
): Promise<ApiResult<ApiEnvelope<ProjectCatalogItem> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/projects/catalog/${projectId}/status`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ status: statusValue }),
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchEmployeeProjects(
  token: string,
  employeeId: number
): Promise<ApiResult<ApiEnvelope<EmployeeProjectItem[]> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}/projects`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function assignEmployeeProject(
  token: string,
  employeeId: number,
  payload: { project_id: number; role_on_project?: string }
): Promise<ApiResult<ApiEnvelope<{ employee_id: number; project_id: number; role_on_project: string | null }> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}/projects`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function removeEmployeeProject(
  token: string,
  employeeId: number,
  projectId: number
): Promise<ApiResult<ApiEnvelope<{ employee_id: number; project_id: number }> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}/projects/${projectId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function deactivateEmployee(
  token: string,
  employeeId: number
): Promise<ApiResult<ApiEnvelope<{ id: number; status: string }> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function reactivateEmployee(
  token: string,
  employeeId: number
): Promise<ApiResult<ApiEnvelope<{ id: number; status: string }> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}/reactivate`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function updateEmployeeJobTitle(
  token: string,
  employeeId: number,
  payload: { designation: string; effective_date?: string; business_unit?: string; department?: string }
): Promise<ApiResult<ApiEnvelope<JobHistoryItem> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}/job-title`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function uploadEmployeePayslip(
  token: string,
  employeeId: number,
  payload: { title: string; period?: string; file: File }
): Promise<ApiResult<ApiEnvelope<EmployeeDocument> | { detail?: unknown }>> {
  const form = new FormData();
  form.append("title", payload.title);
  if (payload.period) {
    form.append("period", payload.period);
  }
  form.append("file", payload.file);

  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}/documents/payslip`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: form,
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchDepartments(
  token: string
): Promise<ApiResult<ApiEnvelope<DepartmentOption[]> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/departments`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchProfile(
  token: string
): Promise<ApiResult<ApiEnvelope<Profile> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchEmployeeById(
  token: string,
  employeeId: number
): Promise<ApiResult<ApiEnvelope<EmployeeDetails> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function updateMyProfile(
  token: string,
  payload: { name?: string; phone?: string; address?: string; blood_type?: string; occupancy?: string; date_of_birth?: string }
): Promise<ApiResult<ApiEnvelope<Profile> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/me`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function uploadMyProfilePicture(
  token: string,
  file: File
): Promise<ApiResult<ApiEnvelope<{ message: string; has_profile_photo: boolean }> | { detail?: unknown }>> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_BASE}/api/v1/employees/me/profile-picture`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: form,
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchMyProfilePicture(token: string): Promise<ApiResult<Blob | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/me/profile-picture`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    return { ok: false, status: response.status, body: await response.json() };
  }
  return { ok: true, status: response.status, body: await response.blob() };
}

export async function fetchEmployeeProfilePicture(
  token: string,
  employeeId: number
): Promise<ApiResult<Blob | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}/profile-picture`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    return { ok: false, status: response.status, body: await response.json() };
  }
  return { ok: true, status: response.status, body: await response.blob() };
}

export async function fetchMyJobHistory(
  token: string
): Promise<ApiResult<ApiEnvelope<JobHistoryItem[]> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/me/job-history`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchMyDocuments(
  token: string
): Promise<ApiResult<ApiEnvelope<EmployeeDocument[]> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/me/documents`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function uploadMyDocument(
  token: string,
  payload: { title: string; document_type: "APPOINTMENT" | "PAYSLIP" | "TAX" | "OTHER"; file: File }
): Promise<ApiResult<ApiEnvelope<EmployeeDocument> | { detail?: unknown }>> {
  const form = new FormData();
  form.append("title", payload.title);
  form.append("document_type", payload.document_type);
  form.append("file", payload.file);

  const response = await fetch(`${API_BASE}/api/v1/employees/me/documents`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: form,
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function downloadMyDocument(
  token: string,
  documentId: string
): Promise<ApiResult<Blob | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/me/documents/${documentId}/download`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    return { ok: false, status: response.status, body: await response.json() };
  }
  return { ok: true, status: response.status, body: await response.blob() };
}

export async function deleteMyDocument(
  token: string,
  documentId: string
): Promise<ApiResult<ApiEnvelope<{ id: string; deleted: boolean }> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/employees/me/documents/${documentId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function uploadEmployeeDocument(
  token: string,
  employeeId: number,
  payload: { title: string; document_type: "APPOINTMENT" | "TAX" | "OTHER"; file: File }
): Promise<ApiResult<ApiEnvelope<EmployeeDocument> | { detail?: unknown }>> {
  const form = new FormData();
  form.append("title", payload.title);
  form.append("document_type", payload.document_type);
  form.append("file", payload.file);

  const response = await fetch(`${API_BASE}/api/v1/employees/${employeeId}/documents`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: form,
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchAttendanceLogs(
  token: string,
  options?: { limit?: number; offset?: number }
): Promise<ApiResult<ApiEnvelope<PaginatedPayload<AttendanceLog>> | { detail?: unknown }>> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 10),
    offset: String(options?.offset ?? 0),
  });
  const response = await fetch(`${API_BASE}/api/v1/attendance/me?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchTodayAttendance(token: string): Promise<ApiResult<ApiEnvelope<AttendanceLog | null> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/attendance/today`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function clockIn(
  token: string,
  mode: "PRESENT" | "WFH"
): Promise<ApiResult<ApiEnvelope<AttendanceLog> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/attendance/clock-in`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ mode }),
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function clockOut(token: string): Promise<ApiResult<ApiEnvelope<AttendanceLog> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/attendance/clock-out`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchMyLeaveBalances(
  token: string
): Promise<ApiResult<ApiEnvelope<LeaveBalance[]> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/leaves/balances/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchMyLeaveRequests(
  token: string,
  options?: { limit?: number; offset?: number }
): Promise<ApiResult<ApiEnvelope<PaginatedPayload<LeaveRequest>> | { detail?: unknown }>> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 20),
    offset: String(options?.offset ?? 0),
  });
  const response = await fetch(`${API_BASE}/api/v1/leaves/requests/me?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function submitLeaveRequest(
  token: string,
  payload: {
    leave_type: "CASUAL" | "SICK" | "EARNED";
    start_date: string;
    end_date: string;
    is_half_day?: boolean;
    half_day_period?: "FIRST_HALF" | "SECOND_HALF";
    reason: string;
  }
): Promise<ApiResult<ApiEnvelope<LeaveRequest> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/leaves/requests`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchPendingLeaveRequests(
  token: string,
  options?: { limit?: number; offset?: number }
): Promise<ApiResult<ApiEnvelope<PaginatedPayload<LeaveRequest>> | { detail?: unknown }>> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 20),
    offset: String(options?.offset ?? 0),
  });
  const response = await fetch(`${API_BASE}/api/v1/leaves/requests/pending?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function approveLeaveRequest(
  token: string,
  requestId: number
): Promise<ApiResult<ApiEnvelope<LeaveRequest> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/leaves/requests/${requestId}/approve`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function rejectLeaveRequest(
  token: string,
  requestId: number
): Promise<ApiResult<ApiEnvelope<LeaveRequest> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/leaves/requests/${requestId}/reject`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchAnnouncements(
  token: string,
  options?: { limit?: number; offset?: number }
): Promise<ApiResult<ApiEnvelope<PaginatedPayload<Announcement>> | { detail?: unknown }>> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 20),
    offset: String(options?.offset ?? 0),
  });
  const response = await fetch(`${API_BASE}/api/v1/announcements?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function createAnnouncement(
  token: string,
  payload: { title: string; body: string }
): Promise<ApiResult<ApiEnvelope<Announcement> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/announcements`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchTeamCalendar(
  token: string,
  options: { year: number; month: number }
): Promise<
  ApiResult<
    ApiEnvelope<{
      year: number;
      month: number;
      days: TeamCalendarDay[];
      items: TeamCalendarItem[];
    }> | { detail?: unknown }
  >
> {
  const params = new URLSearchParams({
    year: String(options.year),
    month: String(options.month),
  });
  const response = await fetch(`${API_BASE}/api/v1/calendar/team?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchHolidays(
  token: string,
  options?: { limit?: number }
): Promise<ApiResult<ApiEnvelope<Holiday[]> | { detail?: unknown }>> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 1),
  });
  const response = await fetch(`${API_BASE}/api/v1/calendar/holidays?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchBirthdays(
  token: string,
  options?: { limit?: number }
): Promise<ApiResult<ApiEnvelope<Birthday[]> | { detail?: unknown }>> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 8),
  });
  const response = await fetch(`${API_BASE}/api/v1/calendar/birthdays?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function fetchTickets(
  token: string,
  options?: { limit?: number; offset?: number; status?: "OPEN" | "IN_PROGRESS" | "RESOLVED"; mine?: boolean }
): Promise<ApiResult<ApiEnvelope<PaginatedPayload<Ticket>> | { detail?: unknown }>> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 20),
    offset: String(options?.offset ?? 0),
  });
  if (options?.status) params.set("status", options.status);
  if (options?.mine) params.set("mine", "true");

  const response = await fetch(`${API_BASE}/api/v1/tickets?${params.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function createTicket(
  token: string,
  payload: { title: string; description: string; category: "IT" | "HR" | "ONBOARDING"; priority: "LOW" | "MEDIUM" | "HIGH" }
): Promise<ApiResult<ApiEnvelope<Ticket> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/tickets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function assignTicket(
  token: string,
  ticketId: number,
  assigneeId: number
): Promise<ApiResult<ApiEnvelope<Ticket> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/tickets/${ticketId}/assign`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ assignee_id: assigneeId }),
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function updateTicketStatus(
  token: string,
  ticketId: number,
  statusValue: "OPEN" | "IN_PROGRESS" | "RESOLVED"
): Promise<ApiResult<ApiEnvelope<Ticket> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/tickets/${ticketId}/status`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ status: statusValue }),
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function createOnboardingTask(
  token: string,
  ticketId: number,
  payload: { task_name: string; due_date?: string }
): Promise<ApiResult<ApiEnvelope<OnboardingTask> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/tickets/${ticketId}/onboarding-tasks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function completeOnboardingTask(
  token: string,
  ticketId: number,
  taskId: number
): Promise<ApiResult<ApiEnvelope<OnboardingTask> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/tickets/${ticketId}/onboarding-tasks/${taskId}/complete`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function fetchMyPayroll(token: string): Promise<ApiResult<ApiEnvelope<PayrollRecord[]> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/finance/payroll/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function fetchMyStatutory(token: string): Promise<ApiResult<ApiEnvelope<StatutoryDetails> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/finance/statutory/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function fetchMyFinanceProfile(token: string): Promise<ApiResult<ApiEnvelope<FinanceProfile> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/finance/profile/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function fetchPolls(
  token: string,
  options?: { limit?: number; offset?: number }
): Promise<ApiResult<ApiEnvelope<PaginatedPayload<Poll>> | { detail?: unknown }>> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 20),
    offset: String(options?.offset ?? 0),
  });
  const response = await fetch(`${API_BASE}/api/v1/polls?${params.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function createPoll(
  token: string,
  payload: { question: string; options: string[] }
): Promise<ApiResult<ApiEnvelope<Poll> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/polls`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function votePoll(
  token: string,
  pollId: number,
  optionIndex: number
): Promise<ApiResult<ApiEnvelope<{ poll_id: number; employee_id: number; option_index: number }> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/polls/${pollId}/vote`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ option_index: optionIndex }),
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function fetchPollResults(
  token: string,
  pollId: number
): Promise<
  ApiResult<
    ApiEnvelope<{ poll_id: number; question: string; total_votes: number; items: PollResultItem[] }> | { detail?: unknown }
  >
> {
  const response = await fetch(`${API_BASE}/api/v1/polls/${pollId}/results`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function fetchOrgTree(token: string): Promise<ApiResult<ApiEnvelope<{ items: OrgNode[] }> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/org/tree`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function fetchHRPolicies(
  token: string,
  options?: { limit?: number; offset?: number }
): Promise<ApiResult<ApiEnvelope<PaginatedPayload<HRPolicy>> | { detail?: unknown }>> {
  const params = new URLSearchParams({
    limit: String(options?.limit ?? 50),
    offset: String(options?.offset ?? 0),
  });
  const response = await fetch(`${API_BASE}/api/v1/hr-policies?${params.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function uploadHRPolicyDocument(
  token: string,
  payload: { title: string; category: string; file: File }
): Promise<ApiResult<ApiEnvelope<HRPolicy & { file_name: string }> | { detail?: unknown }>> {
  const form = new FormData();
  form.append("title", payload.title);
  form.append("category", payload.category);
  form.append("file", payload.file);

  const response = await fetch(`${API_BASE}/api/v1/hr-policies/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: form,
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function downloadHRPolicyDocument(
  token: string,
  policyId: number
): Promise<ApiResult<Blob | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/hr-policies/${policyId}/download`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    return { ok: false, status: response.status, body: await response.json() };
  }
  return { ok: true, status: response.status, body: await response.blob() };
}
export type SQLCopilotResult = {
  question: string;
  generated_sql: string;
  columns: string[];
  rows: Record<string, unknown>[];
  row_count: number;
};

export async function askSQLCopilot(
  token: string,
  question: string
): Promise<ApiResult<ApiEnvelope<SQLCopilotResult> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/chat/sql`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      role: "user",
      content: question,
    }),
    cache: "no-store",
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}
export type HITLConfirmation = {
  id: string;
  action_type: string;
  request: string;
  expires_at: string;
  confirm_endpoint: string;
  cancel_endpoint: string;
};

export type HITLActionResult = {
  intent?: string;
  status?: string;
  answer?: string;
  confirmation?: HITLConfirmation;
};

export type AIRouterResult = {
  intent: "policy" | "sql" | "action" | "unknown";
  answer?: string;
  status?: string;
  confirmation?: HITLConfirmation;
  sources?: Array<{
    policy_id?: number;
    title?: string;
    category?: string;
    section?: string | null;
    page?: number | null;
    source_file?: string | null;
  }>;
  question?: string;
  generated_sql?: string;
  columns?: string[];
  rows?: Record<string, unknown>[];
  row_count?: number;
};

export async function askAIRouter(
  token: string,
  question: string
): Promise<ApiResult<ApiEnvelope<AIRouterResult> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}/api/v1/chat/router`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      role: "user",
      content: question,
    }),
    cache: "no-store",
  });

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}
export async function askAIRouterStream(
  token: string,
  question: string,
  onEvent: (event: Record<string, unknown>) => void,
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/chat/router/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ role: "user", content: question }),
    cache: "no-store",
  });

  if (!response.ok) {
    const errorText = await response.text();
    let message = `Streaming request failed (${response.status}).`;

    try {
      const parsed = JSON.parse(errorText) as {
        detail?: unknown;
        error?: { message?: unknown } | null;
      };
      if (typeof parsed.error?.message === "string") {
        message = parsed.error.message;
      } else if (typeof parsed.detail === "string") {
        message = parsed.detail;
      } else if (errorText.trim()) {
        message = `Streaming request failed (${response.status}): ${errorText}`;
      }
    } catch {
      if (errorText.trim()) {
        message = `Streaming request failed (${response.status}): ${errorText}`;
      }
    }

    throw new Error(message);
  }

  if (!response.body) {
    throw new Error("The server did not provide a streaming response.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // Parse one complete SSE frame. The SSE `event:` field is important for
  // non-policy responses, whose JSON payload may not contain its own `type`.
  const dispatchEvent = async (rawEvent: string): Promise<void> => {
    const lines = rawEvent.split(/\r?\n/);
    let eventName = "message";
    const dataLines: string[] = [];

    for (const line of lines) {
      if (!line || line.startsWith(":")) continue;

      const colonIndex = line.indexOf(":");
      const field = colonIndex === -1 ? line : line.slice(0, colonIndex);
      let value = colonIndex === -1 ? "" : line.slice(colonIndex + 1);
      if (value.startsWith(" ")) value = value.slice(1);

      if (field === "event") {
        eventName = value || "message";
      } else if (field === "data") {
        dataLines.push(value);
      }
    }

    if (dataLines.length === 0) return;

    const data = dataLines.join("\n");
    let parsed: unknown;
    try {
      parsed = JSON.parse(data);
    } catch {
      throw new Error("The server returned an invalid streaming event.");
    }

    if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
      const payload = parsed as Record<string, unknown>;
      onEvent({
        ...payload,
        // Preserve an explicit payload type; otherwise use the SSE event name.
        type: typeof payload.type === "string" ? payload.type : eventName,
        event: eventName,
      });
      const payloadType = typeof payload.type === "string" ? payload.type.toLowerCase() : "";
      const effectiveType = (!payloadType || payloadType === "message" || payloadType === "event")
        ? eventName.toLowerCase()
        : payloadType;
      // Multiple SSE frames can arrive in one network chunk. Yield after each
      // token so the browser can paint the updated React UI before parsing the
      // next frame; otherwise every token may be processed in one task and only
      // the final answer becomes visible.
      if (effectiveType === "token" || effectiveType === "chunk") {
        await new Promise<void>((resolve) => setTimeout(resolve, 16));
      }
      return;
    }

    onEvent({ type: eventName, event: eventName, data: parsed });
    if (eventName.toLowerCase() === "token" || eventName.toLowerCase() === "chunk") {
      await new Promise<void>((resolve) => setTimeout(resolve, 16));
    }
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      // Support both LF and CRLF frame separators.
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() ?? "";

      for (const rawEvent of events) {
        if (rawEvent.trim()) await dispatchEvent(rawEvent);
      }
    }

    buffer += decoder.decode();
    // A final SSE frame is valid even if the stream omitted its final blank line.
    if (buffer.trim()) await dispatchEvent(buffer);
  } finally {
    reader.releaseLock();
  }
}

export async function deleteHRPolicyDocument(
  token: string,
  policyId: number
): Promise<ApiResult<ApiEnvelope<{ id: number; message: string }> | { detail?: unknown }>> {
  const response = await fetch(
    `${API_BASE}/api/v1/hr-policies/${policyId}`,
    {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  );

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}

export async function confirmHITLAction(
  token: string,
  endpoint: string
): Promise<ApiResult<ApiEnvelope<HITLActionResult> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export async function cancelHITLAction(
  token: string,
  endpoint: string
): Promise<ApiResult<ApiEnvelope<HITLActionResult> | { detail?: unknown }>> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });
  return { ok: response.ok, status: response.status, body: await response.json() };
}

export type AIUsageCount = {
  intent?: string;
  tool?: string;
  count: number;
};

export type AIUsageAnalytics = {
  total_requests: number;
  most_common_intents: {
    intent: string;
    count: number;
  }[];
  failed_permission_attempts: number;
  most_used_tools: {
    tool: string;
    count: number;
  }[];
  average_latency_ms: number;
  rag_no_answer_rate: number;
  rag_no_answer_count: number;
  rag_requests_counted: number;
  sql_blocked_queries: number;
};

export async function fetchAIUsageAnalytics(
  token: string
): Promise<ApiResult<ApiEnvelope<AIUsageAnalytics> | { detail?: unknown }>> {
  const response = await fetch(
    `${API_BASE}/api/v1/ai-usage/analytics`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  );

  return {
    ok: response.ok,
    status: response.status,
    body: await response.json(),
  };
}
