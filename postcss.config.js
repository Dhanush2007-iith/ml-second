import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL, timeout: 20000 });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("mindbridge_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let onUnauthorized = () => {};
export function registerUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

client.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      onUnauthorized();
    }
    const message =
      error.response?.data?.detail ||
      (Array.isArray(error.response?.data?.errors) && error.response.data.errors[0]?.msg) ||
      error.message ||
      "Something went wrong. Please try again.";
    return Promise.reject(new Error(typeof message === "string" ? message : "Something went wrong."));
  }
);

export default client;

/* ---------------- Auth ---------------- */
export const registerUser = (payload) => client.post("/api/auth/register", payload).then((r) => r.data);
export const loginUser = (email, password) => {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);
  return client
    .post("/api/auth/login", form, { headers: { "Content-Type": "application/x-www-form-urlencoded" } })
    .then((r) => r.data);
};
export const fetchMe = () => client.get("/api/auth/me").then((r) => r.data);

/* ---------------- Dashboard ---------------- */
export const fetchStudentDashboard = () => client.get("/api/dashboard/student").then((r) => r.data);
export const fetchCounsellorDashboard = () => client.get("/api/dashboard/counsellor").then((r) => r.data);
export const fetchVolunteerDashboard = () => client.get("/api/dashboard/volunteer").then((r) => r.data);

/* ---------------- Mood ---------------- */
export const submitMoodCheckin = (payload) => client.post("/api/mood/checkin", payload).then((r) => r.data);
export const fetchMoodHistory = (days = 30) =>
  client.get("/api/mood/history", { params: { days } }).then((r) => r.data);

/* ---------------- Assessments ---------------- */
export const fetchAssessmentQuestions = (type) =>
  client.get(`/api/assessments/questions/${type}`).then((r) => r.data);
export const submitAssessment = (payload) => client.post("/api/assessments", payload).then((r) => r.data);
export const fetchAssessmentHistory = (type) =>
  client.get("/api/assessments/history", { params: type ? { type } : {} }).then((r) => r.data);

/* ---------------- Chat ---------------- */
export const sendChatMessage = (message, session_id) =>
  client.post("/api/chat/message", { message, session_id }).then((r) => r.data);
export const fetchChatHistory = (session_id) =>
  client.get("/api/chat/history", { params: session_id ? { session_id } : {} }).then((r) => r.data);

/* ---------------- Resources ---------------- */
export const fetchResources = (params) => client.get("/api/resources", { params }).then((r) => r.data);
export const fetchResourceCategories = () => client.get("/api/resources/categories").then((r) => r.data);
export const fetchResourceLanguages = () => client.get("/api/resources/languages").then((r) => r.data);

/* ---------------- Appointments ---------------- */
export const fetchCounsellors = () => client.get("/api/appointments/counsellors").then((r) => r.data);
export const bookAppointment = (payload) => client.post("/api/appointments/book", payload).then((r) => r.data);
export const fetchMyAppointments = () => client.get("/api/appointments/my").then((r) => r.data);
export const fetchCounsellorAppointments = () => client.get("/api/appointments/counsellor").then((r) => r.data);
export const updateAppointmentStatus = (id, status) =>
  client.patch(`/api/appointments/${id}/status`, { status }).then((r) => r.data);

/* ---------------- Peer support ---------------- */
export const fetchPeerPosts = () => client.get("/api/peer/posts").then((r) => r.data);
export const createPeerPost = (payload) => client.post("/api/peer/posts", payload).then((r) => r.data);
export const replyToPost = (id) => client.post(`/api/peer/posts/${id}/reply`).then((r) => r.data);
export const reportPost = (id) => client.post(`/api/peer/posts/${id}/report`).then((r) => r.data);

/* ---------------- Notifications ---------------- */
export const fetchNotifications = () => client.get("/api/notifications").then((r) => r.data);
export const markNotificationRead = (id) => client.post(`/api/notifications/${id}/read`).then((r) => r.data);
export const markAllNotificationsRead = () => client.post("/api/notifications/read-all").then((r) => r.data);

/* ---------------- Admin ---------------- */
export const fetchAdminAnalytics = () => client.get("/api/admin/analytics").then((r) => r.data);
