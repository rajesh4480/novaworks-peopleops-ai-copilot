"use client";
import { flushSync } from "react-dom";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  FileText,
  Loader2,
  Send,
  ShieldCheck,
  Table2,
  Wrench,
  LockKeyhole,
  CheckCircle2,
  AlertCircle,
  Copy,
  Trash2,
  Upload,
  X,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import {
  askAIRouterStream,
  uploadHRPolicyDocument,
  confirmHITLAction,
  cancelHITLAction,
  AIRouterResult,
  HITLActionResult,
} from "@/lib/api";
type ApiError = {
  code?: string;
  message?: string;
};
type ChatMessage = {
  id?: string;
  question: string;
  result?: AIRouterResult;
  error?: string;
  confirmationError?: string;
  permissionDenied?: boolean;
  streaming?: boolean;
};
type RouterResponseBody = {
  success?: boolean;
  data?: AIRouterResult | null;
  error?: ApiError | null;
  detail?: unknown;
};
export default function CopilotPage() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [chatStorageKey, setChatStorageKey] = useState("");
  const [historyLoadedFor, setHistoryLoadedFor] = useState("");
  const [loading, setLoading] = useState(false);
  const [confirmationBusyId, setConfirmationBusyId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(() => Date.now());

  // Re-render periodically so expired confirmations update even when the user
  // leaves the chat open without interacting with it.
  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const questionRef = useRef("");
  const autoSubmitRef = useRef(false);
  const pendingSubmitRef = useRef(false);
  const [voiceError, setVoiceError] = useState("");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState("");
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [name, setName] = useState("User");
  const [canUploadPolicy, setCanUploadPolicy] = useState(false);
  const [showPolicyUpload, setShowPolicyUpload] = useState(false);
  const [policyTitle, setPolicyTitle] = useState("");
  const [policyCategory, setPolicyCategory] = useState("");
  const [policyFile, setPolicyFile] = useState<File | null>(null);
  const [uploadingPolicy, setUploadingPolicy] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");
  const [uploadError, setUploadError] = useState("");
  const conversationRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const accessToken = localStorage.getItem("hrms_access_token");
    if (!accessToken) {
      // If the user has logged out, remove any persisted Copilot conversations.
      for (let index = localStorage.length - 1; index >= 0; index -= 1) {
        const key = localStorage.key(index);
        if (key?.startsWith("hrms_copilot_history\_")) {
          localStorage.removeItem(key);
        }
      }
      sessionStorage.removeItem("hrms_copilot_session_token");
      router.push("/login");
      return;
    }
    try {
      const payload = JSON.parse(atob(accessToken.split(".")[1]));
      const tokenRole = String(payload.role ?? payload.role_name ?? "").toUpperCase();
      const cookieRole = document.cookie
        .split(";")
        .map((part) => part.trim())
        .find((part) => part.startsWith("hrms_role="))
        ?.split("=")[1];
      setCanUploadPolicy(
        ["ADMIN", "MANAGER"].includes(tokenRole) ||
        ["ADMIN", "MANAGER"].includes(decodeURIComponent(cookieRole || "").toUpperCase())
      );
      if (typeof payload.name === "string") {
        setName(payload.name);
      } else if (typeof payload.email === "string") {
        setName(payload.email);
      }
      const userKey =
        typeof payload.sub === "string" || typeof payload.sub === "number"
          ? String(payload.sub)
          : typeof payload.email === "string"
            ? payload.email
            : typeof payload.name === "string"
              ? payload.name
              : "current-user";
      const storageKey = `hrms_copilot_history\_${userKey}`;
      const previousSessionToken = sessionStorage.getItem(
        "hrms_copilot_session_token"
      );
      // A new login usually creates a new access token. Clear the old chat
      // when the token changes, and also clear stale history on first use of
      // this session marker. Normal page refreshes keep the same token/history.
      if (previousSessionToken !== accessToken) {
        localStorage.removeItem(storageKey);
        setHistory([]);
        setError("");
        setPermissionDenied(false);
        setHistoryLoadedFor("");
        sessionStorage.setItem("hrms_copilot_session_token", accessToken);
      }
      setChatStorageKey(storageKey);
    } catch {
      // Keep fallback name if the access token cannot be decoded.
    }
  }, [router]);
  useEffect(() => {
    if (!chatStorageKey) return;
    try {
      const saved = localStorage.getItem(chatStorageKey);
      const parsed: unknown = saved ? JSON.parse(saved) : [];
      if (
        Array.isArray(parsed) &&
        parsed.every(
          (item) =>
            item &&
            typeof item.question === "string" &&
            (item.permissionDenied === true ||
              typeof item.error === "string" ||
              (item.result && typeof item.result.intent === "string"))
        )
      ) {
        setHistory(parsed as ChatMessage[]);
      } else {
        setHistory([]);
      }
    } catch {
      setHistory([]);
    }
    setHistoryLoadedFor(chatStorageKey);
  }, [chatStorageKey]);
  useEffect(() => {
    if (!chatStorageKey || historyLoadedFor !== chatStorageKey) return;
    try {
      localStorage.setItem(chatStorageKey, JSON.stringify(history));
    } catch (storageError) {
      console.warn("Unable to save Copilot chat history:", storageError);
    }
  }, [history, chatStorageKey, historyLoadedFor]);
  useEffect(() => {
    const container = conversationRef.current;
    if (container) container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [history, loading, error, permissionDenied]);
  function clearChat() {
    setHistory([]);
    setError("");
    setPermissionDenied(false);
  }
  const suggestions = useMemo(
    () => [
      "How many casual leave days do I get?",
      "Show me the employees reporting to me.",
      "Can you show me the leave requests I submitted last month?",
      "What are the rules for employees working from home?",
      "Can you submit a leave request for me for next Monday?",
    ],
    []
  );
  // Browser-native speech input. Stop recognition first, then submit only after the
  // browser has delivered its final transcript via the recognition end event.
  function stopVoiceInput(submitRecognized = false) {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    pendingSubmitRef.current = submitRecognized;
    autoSubmitRef.current = false;
    const recognition = recognitionRef.current;
    if (recognition) {
      try { recognition.stop(); } catch { /* recognition may already have ended */ }
      // Keep the ref until onend so the final transcript can be received.
    } else {
      setIsListening(false);
      if (submitRecognized && questionRef.current.trim()) {
        window.setTimeout(() => {
          const form = document.getElementById("copilot-question-form") as HTMLFormElement | null;
          form?.requestSubmit();
        }, 0);
      }
    }
  }

  function clearQuestion() {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    pendingSubmitRef.current = false;
    autoSubmitRef.current = false;
    const recognition = recognitionRef.current;
    recognitionRef.current = null;
    if (recognition) {
      try { recognition.abort(); } catch { /* recognition may already have ended */ }
    }
    setIsListening(false);
    questionRef.current = "";
    setQuestion("");
    setVoiceError("");
  }

  function startVoiceInput() {
    if (isListening) {
      stopVoiceInput(true);
      return;
    }
    setVoiceError("");
    const browserWindow = window as Window & {
      SpeechRecognition?: new () => any;
      webkitSpeechRecognition?: new () => any;
    };
    const Recognition = browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition;
    if (!Recognition) {
      setVoiceError("Voice input is not supported by this browser. Try the latest Chrome or Edge.");
      return;
    }
    const recognition = new Recognition();
    recognitionRef.current = recognition;
    recognition.lang = "en-IN";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 3;
    autoSubmitRef.current = true;
    pendingSubmitRef.current = false;
    // Preserve existing typed text when starting a new recording.
    let finalTranscript = questionRef.current.trim();
    recognition.onresult = (event: any) => {
      let interimTranscript = "";
      for (let i = event.resultIndex ?? 0; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result?.[0]?.transcript ?? "";
        if (result.isFinal) finalTranscript += `${text} `;
        else interimTranscript += text;
      }
      const transcript = `${finalTranscript}${interimTranscript}`.trim();
      if (transcript) {
        questionRef.current = transcript;
        setQuestion(transcript);
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        if (finalTranscript.trim() && autoSubmitRef.current) {
          silenceTimerRef.current = setTimeout(() => stopVoiceInput(true), 2200);
        }
      }
    };
    recognition.onerror = (event: any) => {
      if (event?.error === "aborted") return;
      if (event?.error === "no-speech") {
        setVoiceError("No speech detected. Try speaking a little closer to the microphone.");
      } else {
        setVoiceError("Could not recognize speech. Check microphone permission, speak clearly, or edit the text and try again.");
      }
      pendingSubmitRef.current = false;
      autoSubmitRef.current = false;
      setIsListening(false);
      if (recognitionRef.current === recognition) recognitionRef.current = null;
    };
    recognition.onend = () => {
      setIsListening(false);
      if (recognitionRef.current === recognition) recognitionRef.current = null;
      const shouldSubmit = pendingSubmitRef.current;
      pendingSubmitRef.current = false;
      autoSubmitRef.current = false;
      if (shouldSubmit && questionRef.current.trim()) {
        window.setTimeout(() => {
          const form = document.getElementById("copilot-question-form") as HTMLFormElement | null;
          form?.requestSubmit();
        }, 0);
      }
    };
    try {
      recognition.start();
      setIsListening(true);
    } catch {
      setVoiceError("Voice input could not start. Please try again.");
      setIsListening(false);
      recognitionRef.current = null;
    }
  }


  function stopSpeaking() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || loading) return;

    const accessToken = localStorage.getItem("hrms_access_token");
    if (!accessToken) {
      router.push("/login");
      return;
    }

    setLoading(true);
    setError("");
    setPermissionDenied(false);
    setQuestion("");

    // Do not guess the intent while the request is in flight. The backend
    // confirms the route through Policy token/source events or a final result
    // event for SQL and HR Action requests.
    const streamMessageId = `stream-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setHistory((previous) => [
      ...previous,
      {
        id: streamMessageId,
        question: trimmedQuestion,
        streaming: true,
      },
    ]);

    let streamedAnswer = "";
    let streamedSources: AIRouterResult["sources"] = [];
    let streamedIntent: AIRouterResult["intent"] = "unknown";
    let receivedFinalResult = false;

    const updateCurrentMessage = (updater: (message: ChatMessage) => ChatMessage) => {
      flushSync(() => setHistory((previous) => {
        let matched = false;
        const next = previous.map((message) => {
          // Match by stable ID first. The question/streaming fallback protects
          // against older persisted messages or an ID being lost during hydration.
          if (
            message.id === streamMessageId ||
            (!matched && message.question === trimmedQuestion && message.streaming)
          ) {
            matched = true;
            return updater(message);
          }
          return message;
        });
        // Defensive recovery: if a state update raced with history hydration,
        // attach the completed answer to the newest matching question.
        if (!matched) {
          for (let index = next.length - 1; index >= 0; index -= 1) {
            if (next[index].question === trimmedQuestion) {
              next[index] = updater(next[index]);
              break;
            }
          }
        }
        return next;
      }));
    };

    try {
      await askAIRouterStream(accessToken, trimmedQuestion, (event) => {
        const payloadType = String(event.type ?? "").toLowerCase();
        const sseEventType = String(event.event ?? "").toLowerCase();
        // Some SSE servers put a generic "message" type in the JSON payload
        // while the actual event name (token/sources/done) is in the SSE frame.
        // Prefer that meaningful SSE event name over a generic payload type.
        const eventType =
          (!payloadType || payloadType === "message" || payloadType === "event") &&
          sseEventType
            ? sseEventType
            : payloadType || sseEventType;

        if (eventType === "token" || eventType === "chunk") {
          const nestedData =
            event.data && typeof event.data === "object"
              ? (event.data as Record<string, unknown>)
              : {};
          // The backend currently uses token events only for Policy RAG.
          // SQL and Action requests use the separate `result` event below.
          if (streamedIntent === "unknown") {
            streamedIntent = "policy";
          }
          const tokenText =
            typeof event.token === "string"
              ? event.token
              : typeof event.text === "string"
                ? event.text
                : typeof event.content === "string"
                  ? event.content
                  : typeof nestedData.token === "string"
                    ? nestedData.token
                    : typeof nestedData.text === "string"
                      ? nestedData.text
                      : typeof nestedData.content === "string"
                        ? nestedData.content
                        : "";
          if (!tokenText) return;

          streamedAnswer += tokenText;
          updateCurrentMessage((message) => ({
            ...message,
            streaming: true,
            result: {
              ...(message.result ?? {
                intent: streamedIntent,
                question: trimmedQuestion,
                answer: "",
                sources: [],
              }),
              intent: streamedIntent,
              question: trimmedQuestion,
              answer: streamedAnswer,
              sources: streamedSources,
            },
          }));
          return;
        }

        if (eventType === "sources") {
          const sourcesValue = event.sources;
          if (Array.isArray(sourcesValue)) {
            if (streamedIntent === "unknown") {
              streamedIntent = "policy";
            }
            streamedSources = sourcesValue as AIRouterResult["sources"];
            updateCurrentMessage((message) => ({
              ...message,
              result: {
                ...(message.result ?? {
                  intent: streamedIntent,
                  question: trimmedQuestion,
                  answer: streamedAnswer,
                  sources: [],
                }),
                intent: streamedIntent,
                sources: streamedSources,
              },
            }));
          }
          return;
        }

        if (eventType === "done") {
          if (streamedIntent === "unknown") {
            streamedIntent = "policy";
          }
          const finalAnswer =
            typeof event.answer === "string" ? event.answer : streamedAnswer;
          if (Array.isArray(event.sources)) {
            streamedSources = event.sources as AIRouterResult["sources"];
          }
          // Apply the terminal event directly by the placeholder's stable ID.
          // This avoids any fallback matching issue leaving the loader visible.
          setHistory((previous) => previous.map((message) =>
            message.id === streamMessageId
              ? {
                  ...message,
                  streaming: false,
                  result: {
                    ...(message.result ?? { intent: streamedIntent }),
                    intent: streamedIntent,
                    question: trimmedQuestion,
                    answer: finalAnswer,
                    sources: streamedSources,
                  },
                  error: undefined,
                }
              : message
          ));
          setLoading(false);
          receivedFinalResult = true;
          return;
        }

        if (eventType === "result") {
          let payload: unknown = event.data ?? event.result ?? event;
          if (typeof payload === "string") {
            try {
              payload = JSON.parse(payload);
            } catch {
              updateCurrentMessage((message) => ({
                ...message,
                streaming: false,
                error: payload as string,
                result: undefined,
              }));
              receivedFinalResult = true;
              return;
            }
          }

          if (payload && typeof payload === "object") {
            const record = payload as Record<string, unknown>;
            if (record.success === false || record.error) {
              const apiError = record.error as ApiError | null | undefined;
              const errorMessage =
                apiError?.message ||
                (typeof record.detail === "string" ? record.detail : "") ||
                "The Copilot could not process this request.";
              const denied = apiError?.code === "AI_PERMISSION_DENIED";
              updateCurrentMessage((message) => ({
                question: message.question,
                ...(denied ? { permissionDenied: true } : { error: errorMessage }),
                streaming: false,
              }));
              receivedFinalResult = true;
              return;
            }

            const candidate =
              record.data && typeof record.data === "object"
                ? (record.data as Record<string, unknown>)
                : record;
            if (
              ["policy", "sql", "action", "unknown"].includes(
                String(candidate.intent ?? "").toLowerCase()
              )
            ) {
              streamedIntent = String(candidate.intent).toLowerCase() as AIRouterResult["intent"];
              updateCurrentMessage((message) => ({
                ...message,
                question: trimmedQuestion,
                result: {
                  ...candidate,
                  intent: streamedIntent,
                } as unknown as AIRouterResult,
                streaming: false,
              }));
              receivedFinalResult = true;
              return;
            }
          }
          updateCurrentMessage((message) => ({
            ...message,
            streaming: false,
            error: "The Copilot returned an invalid response.",
          }));
          receivedFinalResult = true;
          return;
        }

        if (eventType === "error") {
          const errorObject =
            event.error && typeof event.error === "object"
              ? (event.error as Record<string, unknown>)
              : undefined;

          const message =
            (typeof event.message === "string" && event.message) ||
            (typeof errorObject?.message === "string" && errorObject.message) ||
            (typeof event.error === "string" && event.error) ||
            "The Copilot could not complete the request.";
          const code = String(
            (event.error as Record<string, unknown> | undefined)?.code ?? event.code ?? ""
          );
          const denied = code === "AI_PERMISSION_DENIED";
          updateCurrentMessage((previousMessage) => ({
            question: previousMessage.question,
            ...(denied
              ? { permissionDenied: true }
              : { error: message }),
            streaming: false,
          }));
          receivedFinalResult = true;
        }
      });

      if (!receivedFinalResult) {
        updateCurrentMessage((message) => ({
          ...message,
          streaming: false,
          result: message.result
            ? { ...message.result, answer: streamedAnswer, sources: streamedSources }
            : undefined,
          ...(streamedAnswer
            ? {}
            : { error: "The stream ended before a response was received. Please try again." }),
        }));
      }
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to connect to the HR Copilot. Please make sure the backend is running.";

      if (/401|unauthorized/i.test(message)) {
        localStorage.removeItem("hrms_access_token");
        localStorage.removeItem("hrms_refresh_token");
        for (let index = localStorage.length - 1; index >= 0; index -= 1) {
          const key = localStorage.key(index);
          if (key?.startsWith("hrms_copilot_history_")) localStorage.removeItem(key);
        }
        sessionStorage.removeItem("hrms_copilot_session_token");
        document.cookie = "hrms_auth=; path=/; max-age=0; samesite=lax";
        document.cookie = "hrms_role=; path=/; max-age=0; samesite=lax";
        router.push("/login");
        return;
      }

      console.error("HR Copilot streaming request failed:", err);
      updateCurrentMessage((chatMessage) => ({
        question: chatMessage.question,
        error: message,
        streaming: false,
      }));
    } finally {
      // Always clear the per-message spinner when the stream promise settles,
      // even if the backend emitted `done` but React state updates raced.
      updateCurrentMessage((message) => ({
        ...message,
        streaming: false,
        ...(message.result && streamedAnswer && !message.result.answer
          ? { result: { ...message.result, answer: streamedAnswer, sources: streamedSources } }
          : {}),
      }));
      setLoading(false);
    }
  }
  async function handleHITLConfirmation(messageIndex: number, decision: "confirm" | "cancel") {
    const message = history[messageIndex];
    const confirmation = message?.result?.confirmation;
    if (!confirmation || confirmationBusyId) return;

    const accessToken = localStorage.getItem("hrms_access_token");
    if (!accessToken) {
      router.push("/login");
      return;
    }

    setConfirmationBusyId(confirmation.id);
    setHistory((previous) => previous.map((item, index) =>
      index === messageIndex ? { ...item, confirmationError: undefined } : item
    ));
    try {
      const response = decision === "confirm"
        ? await confirmHITLAction(accessToken, confirmation.confirm_endpoint)
        : await cancelHITLAction(accessToken, confirmation.cancel_endpoint);

      if (response.status === 401) {
        localStorage.removeItem("hrms_access_token");
        localStorage.removeItem("hrms_refresh_token");
        sessionStorage.removeItem("hrms_copilot_session_token");
        router.push("/login");
        return;
      }

      const body = response.body as {
        success?: boolean;
        data?: HITLActionResult | null;
        error?: { message?: string; code?: string } | null;
        detail?: unknown;
      };
      if (!response.ok || !body?.success || !body.data) {
        const detail =
          typeof body?.detail === "string"
            ? body.detail
            : body?.detail && typeof body.detail === "object" && "message" in body.detail
              ? String((body.detail as { message?: unknown }).message || "")
              : body?.detail != null
                ? JSON.stringify(body.detail)
                : undefined;
        const errorCode = String(body?.error?.code || "").toUpperCase();
        const errorMessage = String(body?.error?.message || detail || "");
        const isExpired = errorCode.includes("EXPIRED") || /expired/i.test(errorMessage);
        if (isExpired) {
          setHistory((previous) => previous.map((item, index) =>
            index === messageIndex && item.result
              ? {
                  ...item,
                  result: {
                    ...item.result,
                    status: "expired",
                    answer: "This confirmation has expired and can no longer be executed. No changes were made to HR records.",
                  },
                }
              : item
          ));
          return;
        }
        throw new Error(errorMessage || `Unable to ${decision} this action (HTTP ${response.status}).`);
      }

      setHistory((previous) =>
        previous.map((item, index) => {
          if (index !== messageIndex || !item.result) return item;

          const actionResult = item.result as AIRouterResult & {
            details?: Record<string, unknown>;
          };

          const confirmationResult = body.data as
            | (HITLActionResult & {
                details?: Record<string, unknown>;
              })
            | undefined;

          return {
            ...item,
            confirmationError: undefined,
            result: {
              ...item.result,
              status:
                body.data?.status ||
                (decision === "confirm" ? "success" : "cancelled"),
              answer:
                body.data?.answer ||
                (decision === "confirm"
                  ? "Action confirmed and executed."
                  : "Action cancelled. No change was made."),
              details: confirmationResult?.details ?? actionResult.details,
              confirmation: undefined,
            } as AIRouterResult,
          };
        })
      );
    } catch (err) {
      const messageText = err instanceof Error ? err.message : `Unable to ${decision} this action.`;
      setHistory((previous) => previous.map((item, index) =>
        index === messageIndex && item.result
          ? { ...item, confirmationError: messageText }
          : item
      ));
    } finally {
      setConfirmationBusyId(null);
    }
  }

  async function handlePolicyUpload(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (uploadingPolicy) return;

    if (!policyTitle.trim() || !policyCategory.trim() || !policyFile) {
      setUploadError("Enter a policy title and category, then choose a file.");
      setUploadMessage("");
      return;
    }

    const extension = policyFile.name.split(".").pop()?.toLowerCase();
    if (!extension || !["txt", "md", "pdf"].includes(extension)) {
      setUploadError("Only .txt, .md, and .pdf files are supported.");
      setUploadMessage("");
      return;
    }
    if (policyFile.size > 2 * 1024 * 1024) {
      setUploadError("File too large. Maximum size is 2 MB.");
      setUploadMessage("");
      return;
    }

    const accessToken = localStorage.getItem("hrms_access_token");
    if (!accessToken) {
      router.push("/login");
      return;
    }

    setUploadingPolicy(true);
    setUploadError("");
    setUploadMessage("");
    try {
      const response = await uploadHRPolicyDocument(accessToken, {
        title: policyTitle.trim(),
        category: policyCategory.trim(),
        file: policyFile,
      });

      if (response.status === 401) {
        localStorage.removeItem("hrms_access_token");
        localStorage.removeItem("hrms_refresh_token");
        router.push("/login");
        return;
      }

      const body = response.body as {
        success?: boolean;
        data?: { id?: number; title?: string } | null;
        error?: { message?: string } | null;
        detail?: unknown;
      };

      if (!response.ok || !body?.success || !body.data) {
        const detail = typeof body?.detail === "string" ? body.detail : undefined;
        throw new Error(
          body?.error?.message || detail ||
          `Policy upload failed (HTTP ${response.status}).`
        );
      }

      setUploadMessage(
        `“${body.data.title || policyTitle.trim()}” uploaded and indexed successfully. You can now ask the Copilot questions about this policy.`
      );
      setPolicyTitle("");
      setPolicyCategory("");
      setPolicyFile(null);
      const fileInput = document.getElementById("copilot-policy-file") as HTMLInputElement | null;
      if (fileInput) fileInput.value = "";
      setQuestion(`According to the ${body.data.title || policyTitle.trim()}, summarize the key rules and requirements.`);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Unable to upload the policy.");
    } finally {
      setUploadingPolicy(false);
    }
  }

  return (
    <main className="flex h-screen overflow-hidden bg-[#0b1020]">
      <Sidebar />
      <section className="flex h-screen w-full min-w-0 flex-col overflow-hidden bg-[#060a16]">
        <Topbar name={name} title="AI HR Copilot" />
        <div className="min-h-0 flex-1 overflow-hidden px-3 py-2 md:px-5 md:py-3">
          <div className="mx-auto flex h-full w-full max-w-none flex-col gap-2.5">
            {/* Compact welcome header: hide once the conversation begins */}
            {history.length === 0 && (
              <div className="shrink-0 rounded-xl border border-indigo-400/20 bg-gradient-to-r from-[#20204f] to-[#302d75] px-3.5 py-2.5 text-white shadow-md">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/15 bg-white/10">
                    <Bot className="h-[18px] w-[18px]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-sm font-semibold tracking-tight sm:text-base">HR Intelligence Copilot</h2>
                    <p className="mt-0.5 text-xs text-indigo-100/80 sm:text-sm">Ask about HR policies, HR data, or supported tasks.</p>
                  </div>
                  <span className="hidden shrink-0 items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-200 sm:inline-flex">
                    <ShieldCheck className="h-4 w-4" /> Role-secured
                  </span>
                </div>
              </div>
            )}
            {/* Question form */}
            <form
              id="copilot-question-form"
              onSubmit={handleSubmit}
              className="order-last shrink-0 rounded-2xl border border-slate-800/90 bg-[#0f172a]/95 p-3 md:p-3.5 shadow-lg backdrop-blur-md sticky bottom-0 z-10"
            >
              <div className="mb-2 flex items-center justify-between gap-3">
                <label htmlFor="copilot-question" className="block text-sm font-medium text-slate-200">
                  Ask the HR Copilot
                </label>
                <div className="flex items-center gap-2">
                  {canUploadPolicy && (
                    <button
                      type="button"
                      onClick={() => {
                        setShowPolicyUpload((visible) => !visible);
                        setUploadError("");
                        setUploadMessage("");
                      }}
                      disabled={loading || uploadingPolicy}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-400/30 px-2.5 py-1.5 text-xs font-medium text-indigo-200 transition hover:bg-indigo-500/10 disabled:opacity-40"
                    >
                      {showPolicyUpload ? <X className="h-3.5 w-3.5" /> : <Upload className="h-3.5 w-3.5" />}
                      {showPolicyUpload ? "Close upload" : "Upload HR Policy"}
                    </button>
                  )}
                  {history.length > 0 && (
                  <button type="button" onClick={clearChat} disabled={loading} className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-slate-400 transition hover:bg-red-500/10 hover:text-red-300 disabled:opacity-40">
                    <Trash2 className="h-3.5 w-3.5" /> Clear chat
                  </button>
                  )}
                </div>
              </div>
              {canUploadPolicy && showPolicyUpload && (
                <div className="mb-3 rounded-xl border border-indigo-400/20 bg-slate-900/80 p-3">
                  <div className="mb-3 flex items-start gap-2">
                    <FileText className="mt-0.5 h-4 w-4 shrink-0 text-indigo-300" />
                    <div>
                      <p className="text-sm font-semibold text-slate-100">Upload and index an HR policy</p>
                      <p className="mt-0.5 text-xs text-slate-400">PDF, TXT, or Markdown · maximum 2 MB. The backend indexes the file after upload.</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    <input
                      value={policyTitle}
                      onChange={(event) => setPolicyTitle(event.target.value)}
                      placeholder="Policy title"
                      minLength={3}
                      maxLength={220}
                      required
                      disabled={uploadingPolicy}
                      className="min-w-0 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500 focus:border-indigo-500 disabled:opacity-60"
                    />
                    <input
                      value={policyCategory}
                      onChange={(event) => setPolicyCategory(event.target.value)}
                      placeholder="Category (e.g. Leave, Remote Work)"
                      minLength={2}
                      maxLength={60}
                      required
                      disabled={uploadingPolicy}
                      className="min-w-0 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500 focus:border-indigo-500 disabled:opacity-60"
                    />
                    <input
                      id="copilot-policy-file"
                      type="file"
                      accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
                      onChange={(event) => setPolicyFile(event.target.files?.[0] ?? null)}
                      required
                      disabled={uploadingPolicy}
                      className="min-w-0 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-slate-800 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-slate-200 hover:file:bg-slate-700 md:col-span-2"
                    />
                  </div>
                  {uploadError && <p role="alert" className="mt-2 text-xs text-red-300">{uploadError}</p>}
                  {uploadMessage && <p role="status" className="mt-2 text-xs text-emerald-300">{uploadMessage}</p>}
                  <div className="mt-3 flex justify-end">
                    <button
                      type="button"
                      onClick={() => void handlePolicyUpload()}
                      disabled={uploadingPolicy || !policyTitle.trim() || !policyCategory.trim() || !policyFile}
                      className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {uploadingPolicy ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Uploading and indexing…</> : <><Upload className="h-3.5 w-3.5" /> Upload policy</>}
                    </button>
                  </div>
                </div>
              )}
              <div className="flex flex-col gap-3 md:flex-row">
                <input
                  id="copilot-question"
                  type="text"
                  value={question}
                  onChange={(event) => { questionRef.current = event.target.value; setQuestion(event.target.value); }}
                  placeholder="Example: How many casual leave days do I get?"
                  disabled={loading}
                  className="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                />
                <button
                  type="submit"
                  disabled={loading || !question.trim()}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Thinking...
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4" />
                      Ask
                    </>
                  )}
                </button>
              </div>
            </form>
            <div ref={conversationRef} className="copilot-conversation min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain px-1 pb-2">
            {/* Empty-state welcome: keep the help prompt until the first response */}
            {history.length === 0 && (
              <div className="flex min-h-full flex-col items-center justify-center px-4 py-4 text-center sm:py-6">
                <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-indigo-400/20 bg-indigo-500/10 shadow-md shadow-indigo-950/20">
                  <Bot className="h-8 w-8 text-indigo-300" />
                </div>
                <h2 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">How can I help?</h2>
                <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">
                  Ask about HR policies, your leave balance, team information, or an HR task. I’ll route your question to the right capability based on your role.
                </p>
                <div className="mt-5 flex max-w-4xl flex-wrap justify-center gap-2">
                  {suggestions.slice(0, 4).map((suggestion) => (
                    <button
                      key={`welcome-${suggestion}`}
                      type="button"
                      onClick={() => setQuestion(suggestion)}
                      disabled={loading}
                      className="rounded-xl border border-slate-700/80 bg-slate-900/60 px-3 py-2 text-left text-xs text-slate-300 transition hover:border-indigo-400/60 hover:bg-indigo-500/10 hover:text-indigo-100 sm:text-sm"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {/* General Error */}
            {error && (
              <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300">
                {error}
              </div>
            )}
            {/* Continuous chat history */}
            {history.map(({ question: askedQuestion, result, error: messageError, confirmationError, permissionDenied: messagePermissionDenied, streaming: messageStreaming }, messageIndex) => (
              <div key={`${messageIndex}-${askedQuestion}`} className="block w-full min-w-0 space-y-4">
                <div className="ml-auto max-w-3xl rounded-2xl border border-indigo-400/20 bg-indigo-500/10 p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-300">You</p>
                  <p className="whitespace-pre-wrap text-sm leading-6 text-slate-100">{askedQuestion}</p>
                </div>
                {messagePermissionDenied ? (
                  <div className="block w-full min-w-0 self-stretch rounded-xl border border-amber-400/20 bg-amber-500/[0.06] px-3 py-2.5 sm:px-4">
                    <div className="flex items-center gap-2.5">
                      <LockKeyhole className="h-4 w-4 shrink-0 text-amber-300" />
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-amber-200">Access denied</p>
                        <p className="mt-0.5 text-xs leading-5 text-slate-300">Your HRMS role doesn&apos;t allow this request.</p>
                      </div>
                    </div>
                  </div>
                ) : messageError ? (
                  <div role="alert" className="block w-full min-w-0 rounded-xl border border-red-500/20 bg-red-500/[0.06] px-4 py-3 text-sm leading-6 text-red-300">
                    {messageError}
                  </div>
                ) : messageStreaming && !result ? (
                  <div className="flex items-center gap-2 rounded-xl border border-indigo-400/20 bg-indigo-500/[0.06] px-4 py-3 text-sm text-indigo-200">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Understanding your request and routing it to the right Copilot…</span>
                  </div>
                ) : result ? (
                  <>
                {/* Intent */}
                <div className="rounded-2xl border border-slate-800/90 bg-[#0f172a] p-5 shadow-lg">
                  <div className="flex items-center gap-3">
                    <Bot className="h-5 w-5 text-indigo-400" />
                    <h2 className="font-semibold text-white">Copilot Result</h2>
                    <IntentBadge intent={result.intent} />
                  </div>
                  {result.question && (
                    <p className="mt-2 text-sm text-slate-400">
                      {result.question}
                    </p>
                  )}
                </div>
                {/* Streaming status */}
                {messageStreaming && (
                  <div className="flex items-center gap-2 rounded-xl border border-indigo-400/20 bg-indigo-500/[0.06] px-4 py-3 text-sm text-indigo-200">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>{result.answer?.length ? "Generating response…" : "Connecting to Copilot…"}</span>
                  </div>
                )}
                {/* Answer */}
                {result.answer && result.intent !== "action" && (
                  <div className="rounded-2xl border border-slate-800/90 bg-[#0f172a] p-5 shadow-lg">
                    <h2 className="mb-3 font-semibold text-white">Answer</h2>
                    <p className="whitespace-pre-wrap text-sm leading-6 text-slate-300">
                      {result.answer}
                    </p>
                  </div>
                )}
                {/* Policy sources */}
                {result.intent === "policy" &&
                  result.sources &&
                  result.sources.length > 0 && (
                    <details className="group overflow-hidden rounded-xl border border-slate-800/90 bg-[#0f172a] shadow-sm">
                      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 [&::-webkit-details-marker]:hidden">
                        <FileText className="h-4 w-4 shrink-0 text-indigo-400" />
                        <span className="text-sm font-semibold text-white">Policy Sources</span>
                        <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] text-indigo-300">{result.sources.length}</span>
                        <span className="ml-auto text-xs text-slate-500 group-open:hidden">Show</span>
                        <span className="ml-auto hidden text-xs text-slate-500 group-open:inline">Hide</span>
                      </summary>
                      <div className="space-y-2 border-t border-slate-800 px-3 py-2.5">
                        {result.sources.map((source, index) => (
                          <div
                            key={`${source.policy_id ?? "source"}-${index}`}
                            className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2"
                          >
                            <p className="text-sm font-medium text-slate-200">{source.title || "HR Policy"}</p>
                            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500">
                              {source.category && <span>{source.category}</span>}
                              {source.section && <span>Section: {source.section}</span>}
                              {source.page != null && <span>Page: {source.page}</span>}
                              {source.source_file && <span>File: {source.source_file}</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                {/* SQL */}
                {result.intent === "sql" && (
                  <>
                    {result.generated_sql && (
                      <details className="group overflow-hidden rounded-xl border border-slate-800/90 bg-[#0f172a] shadow-sm">
                        <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 [&::-webkit-details-marker]:hidden">
                          <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-400" />
                          <span className="text-sm font-semibold text-white">Generated Read-only SQL</span>
                          <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-300">SELECT only</span>
                          <span className="ml-auto text-xs text-slate-500 group-open:hidden">View SQL</span>
                          <span className="ml-auto hidden text-xs text-slate-500 group-open:inline">Hide SQL</span>
                        </summary>
                        <div className="border-t border-slate-800 p-3">
                          <div className="mb-2 flex justify-end">
                            <button
                              type="button"
                              onClick={() => {
                                void navigator.clipboard.writeText(result.generated_sql || "");
                              }}
                              className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 px-2.5 py-1.5 text-[11px] text-slate-300 transition hover:border-indigo-400/50 hover:text-indigo-200"
                            >
                              <Copy className="h-3 w-3" /> Copy SQL
                            </button>
                          </div>
                          <pre className="max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-slate-800 bg-[#020617] p-3 font-mono text-xs leading-5 text-indigo-200">
                            {result.generated_sql}
                          </pre>
                        </div>
                      </details>
                    )}
                    <div className="overflow-hidden rounded-2xl border border-slate-800/90 bg-[#0f172a] shadow-lg">
                      <div className="flex items-center justify-between border-b border-slate-800 px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <Table2 className="h-5 w-5 text-indigo-400" />
                          <h2 className="font-semibold text-white">
                            Query Results
                          </h2>
                        </div>
                        <span className="rounded-full bg-indigo-500/10 px-2 py-0.5 text-[11px] font-medium text-indigo-300">
                          {result.row_count ?? 0} rows
                        </span>
                      </div>
                      {!result.rows || result.rows.length === 0 ? (
                        <div className="px-4 py-5 text-center text-xs text-slate-500">
                          No records found.
                        </div>
                      ) : (
                        <div className="max-h-[600px] overflow-auto">
                          <table className="min-w-full text-left text-sm">
                            <thead className="sticky top-0 bg-slate-900">
                              <tr>
                                {(result.columns || []).map((column) => (
                                  <th
                                    key={column}
                                    className="whitespace-nowrap border-b border-slate-800 px-3 py-2 text-xs font-semibold text-slate-300"
                                  >
                                    {column}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                              {result.rows.map((row, rowIndex) => (
                                <tr
                                  key={rowIndex}
                                  className="hover:bg-white/[0.02]"
                                >
                                  {(result.columns || []).map((column) => (
                                    <td
                                      key={`${rowIndex}-${column}`}
                                      className="whitespace-nowrap px-3 py-2 text-xs text-slate-400"
                                    >
                                      {formatCellValue(row[column])}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  </>
                )}
                {/* Human-in-the-loop confirmation */}
                {result.intent === "action" && result.confirmation && (() => {
                  const expiryTimestamp = Date.parse(result.confirmation.expires_at);
                  const isConfirmationExpired =
                    String(result.status || "").toLowerCase() === "expired" ||
                    (!Number.isNaN(expiryTimestamp) && expiryTimestamp <= currentTime);
                  return (
                    <div className={`rounded-2xl border p-5 shadow-lg ${isConfirmationExpired ? "border-rose-400/30 bg-rose-500/[0.06]" : "border-amber-400/30 bg-amber-500/[0.06]"}`}>
                      <div className="flex items-start gap-3">
                        {isConfirmationExpired
                          ? <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-300" />
                          : <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-amber-300" />}
                        <div className="min-w-0 flex-1">
                          <h3 className={`font-semibold ${isConfirmationExpired ? "text-rose-100" : "text-amber-100"}`}>
                            {isConfirmationExpired ? "Confirmation expired" : "Confirmation required"}
                          </h3>
                          <p className="mt-1 text-sm leading-6 text-slate-300">
                            {isConfirmationExpired
                              ? "This confirmation has expired and can no longer be executed. No changes were made to HR records."
                              : "This action may change HR records. Review the request before proceeding. No change has been made yet."}
                          </p>
                          <div className="mt-3 rounded-xl border border-slate-700 bg-[#080d1b] p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Proposed action</p>
                            <p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-100">{result.confirmation.request}</p>
                            <p className="mt-3 text-xs text-slate-500">
                              Expires: {Number.isNaN(expiryTimestamp)
                                ? result.confirmation.expires_at
                                : new Date(expiryTimestamp).toLocaleString()}
                            </p>
                          </div>
                          {confirmationError && (
                            <div role="alert" aria-live="assertive" className="mt-4 flex items-start gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
                              <div className="min-w-0">
                                <p className="font-semibold text-red-100">Action could not be completed</p>
                                <p className="mt-1 whitespace-pre-wrap break-words">{confirmationError}</p>
                              </div>
                            </div>
                          )}
                          {isConfirmationExpired || confirmationError ? (
                            <div className="mt-5 inline-flex items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm font-medium text-red-300">
                              <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
                              <span>
                                {isConfirmationExpired
                                  ? "Expired — confirmation buttons are no longer available."
                                  : "This confirmation could not be completed. Confirmation buttons are no longer available."}
                              </span>
                            </div>
                          ) : (
                            <div className="mt-4 flex flex-wrap gap-2">
                              <button
                                type="button"
                                onClick={() => void handleHITLConfirmation(messageIndex, "confirm")}
                                disabled={confirmationBusyId !== null}
                                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {confirmationBusyId === result.confirmation.id
                                  ? <><Loader2 className="h-4 w-4 animate-spin" /> Processing...</>
                                  : <><CheckCircle2 className="h-4 w-4" /> Confirm &amp; Execute</>}
                              </button>
                              <button
                                type="button"
                                onClick={() => void handleHITLConfirmation(messageIndex, "cancel")}
                                disabled={confirmationBusyId !== null}
                                className="inline-flex items-center gap-2 rounded-lg border border-slate-600 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                <X className="h-4 w-4" /> Cancel Action
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })()}
                {/* HR Action */}
                {result.intent === "action" && !result.confirmation && (
                  <ActionResult result={result} />
                )}
                {/* Unknown */}
                {result.intent === "unknown" && (
                  <div className="rounded-2xl border border-slate-800/90 bg-[#0f172a] p-5 shadow-lg">
                    <p className="text-sm leading-6 text-slate-400">
                      {result.answer ||
                        "This request is outside the current HR Copilot scope. Try asking about HR policies, HRMS data, or supported HR tasks."}
                    </p>
                  </div>
                )}
                  </>
                ) : null}
              </div>
            ))}
            </div>
          </div>
        </div>
        <style jsx global>{`
          .copilot-conversation { scrollbar-width: none; -ms-overflow-style: none; }
          .copilot-conversation::-webkit-scrollbar { display: none; width: 0; height: 0; }
        `}</style>
      </section>
    </main>
  );
}
function ActionResult({ result }: { result: AIRouterResult }) {
  type Ticket = {
    id?: number | string;
    title?: string;
    description?: string;
    category?: string;
    priority?: string;
    status?: string;
    employee_id?: number;
    assignee_id?: number | null;
    created_at?: string;
    onboarding_tasks?: Array<{
      id?: number;
      task_name?: string;
      is_completed?: boolean;
      due_date?: string | null;
    }>;
  };
  type ProjectAssignment = {
    project_id?: number;
    project_name?: string;
    project_description?: string | null;
    project_status?: string;
    role_on_project?: string | null;
  };
  type LeaveHistoryItem = {
    id?: number | string;
    employee_id?: number;
    leave_type?: string;
    start_date?: string;
    end_date?: string;
    is_half_day?: boolean;
    reason?: string | null;
    status?: string;
    approver_id?: number | null;
  };
  type ActionPayload = {
    id?: number | string;
    title?: string;
    description?: string;
    category?: string;
    priority?: string;
    status?: string;
    employee_id?: number;
    assignee_id?: number | null;
    created_at?: string;
    onboarding_tasks?: Array<{
      id?: number;
      task_name?: string;
      is_completed?: boolean;
      due_date?: string | null;
    }>;
    leave_type?: string;
    start_date?: string;
    end_date?: string;
    is_half_day?: boolean;
    reason?: string;
    leave_request?: Record<string, unknown>;
    action_result?: Record<string, unknown>;
    request?: Record<string, unknown>;
    ticket?: Record<string, unknown>;
    data?: Record<string, unknown>;
    body?: string;
    message?: string;
    author_id?: number;
    author_name?: string;
    details?: {
      id?: number;
      title?: string;
      body?: string;
      message?: string;
      author_id?: number;
      author_name?: string;
      description?: string;
      category?: string;
      priority?: string;
      status?: string;
      employee_id?: number;
      assignee_id?: number | null;
      created_at?: string;
      ticket?: Record<string, unknown>;
      data?: Record<string, unknown>;
      result?: Record<string, unknown>;
      action_result?: Record<string, unknown>;
      balances?: Array<{
        leave_type?: string;
        total?: number | null;
        used?: number | null;
        remaining?: number | null;
        available?: boolean;
        note?: string | null;
      }>;
      items?: Array<Ticket | ProjectAssignment | LeaveHistoryItem>;
      meta?: {
        total?: number;
        limit?: number;
        offset?: number;
      };
    };
  };
  // Normalize the common API envelope ({ success: true, data: {...} }) as well
  // as the already-unwrapped AIRouterResult. This keeps ticket rendering stable
  // whether the caller passes the router payload or the raw API data envelope.
  const unwrapActionEnvelope = (value: unknown): unknown => {
    let current = value;
    for (let depth = 0; depth < 5; depth += 1) {
      if (!current || typeof current !== "object" || Array.isArray(current)) break;
      const record = current as Record<string, unknown>;
      const nested = record.data;
      if (
        nested &&
        typeof nested === "object" &&
        !Array.isArray(nested) &&
        (record.success === true || !("intent" in record))
      ) {
        current = nested;
        continue;
      }
      break;
    }
    return current;
  };
  const normalizedResult = unwrapActionEnvelope(result) as AIRouterResult;
  const actionResult = normalizedResult ?? result;
  const actionData = actionResult as AIRouterResult & ActionPayload;
  // Action responses can be returned directly or wrapped by the API/tool in
  // data/details/result objects. Unwrap those envelopes before rendering.
  // Search nested action envelopes recursively. Some router/tool responses wrap
  // the created record several levels deep (for example data.result.ticket).
  const payloadCandidates: Record<string, unknown>[] = [];
  const visited = new Set<object>();
  const collectPayloads = (value: unknown, depth = 0): void => {
    if (!value || typeof value !== "object" || depth > 6 || visited.has(value)) return;
    visited.add(value);
    // Do not search list results for a single created-record candidate.
    // Otherwise a status/list response can promote its first existing ticket
    // to `directTicket`, making it look like a creation confirmation and
    // rendering the same ticket twice (once from details.items and once as
    // directTicket).
    if (Array.isArray(value)) return;
    const record = value as Record<string, unknown>;
    payloadCandidates.push(record);
    Object.values(record).forEach((child) => collectPayloads(child, depth + 1));
  };
  collectPayloads(actionData);
  const ticketSource = payloadCandidates.find(
    (value) =>
      (typeof value.id === "number" || (typeof value.id === "string" && /^\d+$/.test(value.id))) &&
      typeof value.category === "string" &&
      typeof value.priority === "string" &&
      (typeof value.title === "string" || typeof value.description === "string")
  );
  const ticketCandidate = (ticketSource ?? {}) as ActionPayload;
  // Announcement responses may include the created record in `details`, but
  // some router responses only include the success answer/status. Do not make
  // the polished confirmation card depend on author fields being present.
  const announcementSource = payloadCandidates.find(
    (value) =>
      typeof value.title === "string" &&
      (typeof value.body === "string" || typeof value.message === "string") &&
      (value.id == null ||
        typeof value.id === "number" ||
        (typeof value.id === "string" && /^\d+$/.test(value.id)))
  );
  const announcement = (announcementSource ?? {}) as ActionPayload;
  const answerText = String(actionData.answer ?? actionResult.answer ?? "");
  const announcementCreated = Boolean(
    ["success", "completed", "created"].includes(
      String(actionResult.status ?? actionData.status ?? "").toLowerCase()
    ) &&
      (announcementSource || /^Announcement\s+['\"].+['\"]\s+was created\./i.test(answerText))
  );
  // Detect a newly created project even when the API wraps it in data/result/details.
  const projectSource = payloadCandidates.find(
    (value) =>
      typeof value.project_name === "string" ||
      (typeof value.name === "string" &&
        ("project_description" in value ||
          "project_status" in value ||
          ("id" in value && "status" in value && "description" in value)))
  );

  // Some action tools mistakenly put the whole natural-language request in the
  // project's name and return a null description. Recover the intended fields
  // from the action answer when that happens.
  const rawProjectName = String(projectSource?.project_name ?? projectSource?.name ?? "");
  const projectAssignmentMatch =
    /Project\s+#?(\d+)\s+was assigned to employee\s+#?(\d+)/i.exec(
      answerText
    );
  const projectAssigned = Boolean(
    projectAssignmentMatch &&
      ["success", "completed"].includes(
        String(actionResult.status ?? actionData.status ?? "").toLowerCase()
      )
  );
  const assignedProjectId = projectAssignmentMatch?.[1];
  const assignedEmployeeId = projectAssignmentMatch?.[2];
  const parsedProjectName =
    /Project\s+['"](.+?)['"]\s+with the description/i.exec(answerText)?.[1] ??
    /Project\s+(.+?)\s+was created/i.exec(answerText)?.[1] ??
    "";
  const parsedProjectDescription =
    /with the description\s+["'](.+?)["']\s+was created/i.exec(answerText)?.[1] ?? "";
  const nameLooksLikeRequest = /with the description/i.test(rawProjectName);
  const createdProject = projectSource
    ? {
        id: projectSource.project_id ?? projectSource.id,
        name: (nameLooksLikeRequest && parsedProjectName ? parsedProjectName : rawProjectName).replace(/^[\'"]+|[\'"]+$/g, "").trim(),
        description: String(projectSource.project_description ?? projectSource.description ?? "") || parsedProjectDescription,
        status: String(projectSource.project_status ?? projectSource.status ?? actionData.status ?? "CREATED"),
      }
    : null;
  const projectCreated = Boolean(
    createdProject?.name &&
      ["success", "completed", "created", "submitted", "pending"].includes(
        String(actionResult.status ?? actionData.status ?? "").toLowerCase()
      )
  );
  const balances =
    actionData.details?.balances ??
    (actionData.details?.data as ActionPayload | undefined)?.details?.balances ??
    [];
  // The router may return a created ticket at the top level or nested under
  // action_result/ticket/details. Normalize both shapes for the same UI.
  const directTicket =
    (typeof ticketCandidate.id === "number" ||
      (typeof ticketCandidate.id === "string" && /^\d+$/.test(ticketCandidate.id))) &&
    typeof ticketCandidate.category === "string" &&
    typeof ticketCandidate.priority === "string"
      ? {
          id: typeof ticketCandidate.id === "string" ? Number(ticketCandidate.id) : ticketCandidate.id,
          title: ticketCandidate.title,
          description: ticketCandidate.description,
          category: ticketCandidate.category,
          priority: ticketCandidate.priority,
          status: ticketCandidate.status ?? actionData.status,
          employee_id: ticketCandidate.employee_id,
          assignee_id: ticketCandidate.assignee_id,
          created_at: ticketCandidate.created_at,
          onboarding_tasks: ticketCandidate.onboarding_tasks,
        }
      : null;
  const items = [
    ...(actionData.details?.items ?? []),
    ...(directTicket ? [directTicket] : []),
  ];
  const projects = items.filter(
    (item): item is ProjectAssignment => "project_name" in item
  );
  // Leave-history records have leave-specific fields and must not be rendered
  // by the generic support-ticket card.
  const leaveRequests = items.filter(
    (item): item is LeaveHistoryItem =>
      "leave_type" in item &&
      typeof item.leave_type === "string" &&
      "start_date" in item &&
      typeof item.start_date === "string" &&
      "end_date" in item &&
      typeof item.end_date === "string"
  );
  const ticketItems = items.filter(
    (item): item is Ticket =>
      !("project_name" in item) &&
      !(
        "leave_type" in item &&
        typeof item.leave_type === "string" &&
        "start_date" in item &&
        typeof item.start_date === "string" &&
        "end_date" in item &&
        typeof item.end_date === "string"
      )
  );
  // Avoid duplicate cards if an API envelope happens to include the same
  // ticket both in details.items and as the direct action result.
  const seenTicketKeys = new Set<string>();
  const tickets = ticketItems.filter((ticket, index) => {
    const key = ticket.id != null ? `id:${ticket.id}` : `index:${index}`;
    if (seenTicketKeys.has(key)) return false;
    seenTicketKeys.add(key);
    return true;
  });
  const details =
    actionData.details ??
    actionData.leave_request ??
    actionData.action_result ??
    actionData.request ??
    (actionData.intent === "action" &&
    "leave_type" in actionData &&
    "start_date" in actionData &&
    "end_date" in actionData
      ? (actionData as unknown as Record<string, unknown>)
      : null);
  const status = actionResult.status?.toLowerCase() ?? "";
  const leaveRequest =
    details &&
    typeof details === "object" &&
    "leave_type" in details &&
    "start_date" in details &&
    "end_date" in details
      ? details
      : null;
  // The action envelope can say SUCCESS while the leave record itself is
  // REJECTED or APPROVED. Prefer the status on the leave record.
  const leaveStatus = String(
    (leaveRequest as Record<string, unknown> | null)?.status ?? status
  ).toLowerCase();
  const isLeaveConfirmation = Boolean(
    leaveRequest &&
      ["pending", "approved", "rejected", "success", "created", "submitted", "completed"].includes(leaveStatus)
  );
  const leaveType = String(leaveRequest?.leave_type ?? "Leave")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase());
  const formatDate = (value: unknown): string => {
    if (typeof value !== "string") return "—";
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!match) return value;
    const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
    return date.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    });
  };
  const leaveDuration = (() => {
    if (!leaveRequest) return "—";
    if (leaveRequest.is_half_day === true) return "Half day";
    const start = leaveRequest.start_date;
    const end = leaveRequest.end_date;
    if (typeof start !== "string" || typeof end !== "string") return "—";
    const startTime = Date.parse(`${start}T00:00:00Z`);
    const endTime = Date.parse(`${end}T00:00:00Z`);
    if (!Number.isFinite(startTime) || !Number.isFinite(endTime) || endTime < startTime) return "—";
    const days = Math.floor((endTime - startTime) / 86400000) + 1;
    return `${days} day${days === 1 ? "" : "s"}`;
  })();
  // A created ticket is returned by the API as the ticket record itself inside
  // `data`; the ticket's workflow status is OPEN (not the action status SUCCESS).
  // Use the normalized ticket record as the source of truth for this confirmation.
  const ticketCreated = Boolean(
    directTicket &&
      directTicket.id != null &&
      typeof directTicket.title === "string" &&
      typeof directTicket.category === "string" &&
      typeof directTicket.priority === "string" &&
      String(directTicket.status ?? actionResult.status ?? "").toLowerCase() === "open"
  );
  const succeeded = [
    "success",
    "completed",
    "created",
    "submitted",
    "pending",
  ].includes(status) || ticketCreated || projectCreated;
  const failed = [
    "failed",
    "error",
    "denied",
    "not_implemented",
    "unsupported",
  ].includes(status);
  const entries = details && !leaveRequest
    ? Object.entries(details).filter(
        ([key, value]) =>
          value !== null &&
          value !== undefined &&
          ![
            "hashed_password",
            "bank_account_number",
            "pan_number",
          ].includes(key.toLowerCase())
      )
    : [];
  return (
    <div
      className={`relative overflow-hidden rounded-2xl border shadow-lg ${
        projectCreated || projectAssigned || announcementCreated
          ? "border-emerald-400/30 bg-slate-900/95 p-0 shadow-emerald-950/30"
          : `p-5 ${ticketCreated || isLeaveConfirmation ? "border-emerald-400/20 bg-emerald-500/5" : "border-amber-500/20 bg-amber-500/10"}`
      }`}
    >
      {projectCreated && (
        <div className="flex items-center gap-3 border-b border-emerald-400/20 bg-emerald-500/10 px-5 py-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-400/15 ring-1 ring-emerald-300/30">
            <CheckCircle2 className="h-6 w-6 text-emerald-300" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Project created</p>
            <h2 className="mt-1 text-lg font-semibold text-white">Project Confirmation</h2>
            <p className="mt-1 text-sm text-emerald-100/80">Your new project is ready. Review the details below.</p>
          </div>
          <span className="shrink-0 rounded-full border border-emerald-300/30 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-200">SUCCESS</span>
        </div>
      )}
      {announcementCreated && (
        <div className="flex items-center gap-3 border-b border-emerald-400/20 bg-gradient-to-r from-emerald-500/10 to-teal-500/5 px-5 py-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-400/15 ring-1 ring-emerald-300/30">
            <CheckCircle2 className="h-6 w-6 text-emerald-300" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Action completed</p>
            <h2 className="mt-1 text-lg font-semibold text-white">Announcement created successfully</h2>
            <p className="mt-1 text-sm text-emerald-100/80">Your announcement has been saved. Review the confirmation details below.</p>
          </div>
          <span className="shrink-0 rounded-full border border-emerald-300/30 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-200">SUCCESS</span>
        </div>
      )}
      {projectAssigned && (
        <div className="flex items-center gap-3 border-b border-emerald-400/20 bg-emerald-500/10 px-5 py-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-400/15 ring-1 ring-emerald-300/30">
            <CheckCircle2 className="h-6 w-6 text-emerald-300" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">
              Assignment completed
            </p>
            <h2 className="mt-1 text-lg font-semibold text-white">
              Project Assignment Confirmation
            </h2>
            <p className="mt-1 text-sm text-emerald-100/80">
              The employee has been assigned to the project successfully.
            </p>
          </div>
          <span className="shrink-0 rounded-full border border-emerald-300/30 bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-200">
            SUCCESS
          </span>
        </div>
      )}
      <div className={`flex items-start gap-3 ${projectCreated || projectAssigned || announcementCreated ? "p-5 pt-4" : ""}`}>

        {succeeded ? (
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
        ) : (
          <Wrench className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
        )}
        <div className="min-w-0 flex-1">
          {!projectCreated && !projectAssigned && !announcementCreated && <h2 className={`font-semibold ${ticketCreated || isLeaveConfirmation ? "text-emerald-300" : "text-amber-200"}`}>{ticketCreated ? "Support Ticket Confirmation" : isLeaveConfirmation ? "Leave Request Confirmation" : "HR Action"}</h2>}
          {(ticketCreated ? directTicket?.status : actionResult.status) && (
            <div className="mt-2">
              <span
                className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${
                  succeeded
                    ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-300"
                    : failed
                      ? "border-red-400/20 bg-red-500/10 text-red-300"
                      : "border-amber-400/20 bg-amber-500/10 text-amber-200"
                }`}
              >
                Status: {String(ticketCreated ? directTicket?.status : actionResult.status).replaceAll("_", " ")}
              </span>
            </div>
          )}
          {!projectCreated && !projectAssigned && <p className={`mt-3 whitespace-pre-wrap text-sm leading-6 ${ticketCreated || isLeaveConfirmation || announcementCreated ? "text-slate-200" : "text-amber-100/80"}`}>
            {ticketCreated
              ? "Your support ticket has been created successfully. You can use the details below to track it."
              : announcementCreated
                ? "Your announcement has been created successfully. The details are below."
              : projectCreated
                ? "Your project has been created successfully. The details are below."
              : isLeaveConfirmation
                ? leaveStatus === "rejected"
                  ? "The leave request has been rejected. The details are below."
                  : leaveStatus === "approved"
                    ? "The leave request has been approved successfully. The details are below."
                    : "Your leave request has been submitted successfully. The details are below."
                : actionResult.answer ||
                  (actionResult.status
                    ? `The backend returned an action result with status "${actionResult.status.replaceAll("_", " ")}".`
                    : "The backend returned an action response without a message or status.")}
          </p>}
          {projectCreated && createdProject && (
            <div className="mt-0 rounded-xl border border-emerald-400/20 bg-slate-950/40 p-4">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-emerald-300"><FileText className="h-4 w-4" /> Project Details</h3>
              <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-slate-400">Project ID</dt>
                  <dd className="mt-1 text-sm text-white">{createdProject.id != null ? `#${String(createdProject.id)}` : "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Status</dt>
                  <dd className="mt-1">
                    <span className="inline-flex rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300">
                      {createdProject.status.replaceAll("_", " ").toUpperCase()}
                    </span>
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs text-slate-400">Project Name</dt>
                  <dd className="mt-1 break-words text-sm font-medium text-white">{createdProject.name}</dd>
                </div>
                {createdProject.description && (
                  <div className="sm:col-span-2">
                    <dt className="text-xs text-slate-400">Description</dt>
                    <dd className="mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-slate-200">{createdProject.description}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}
          {projectAssigned && (
            <div className="mt-4 rounded-xl border border-emerald-400/20 bg-slate-950/40 p-4">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-emerald-300">
                <FileText className="h-4 w-4" /> Assignment Details
              </h3>
              <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-slate-400">Project ID</dt>
                  <dd className="mt-1 text-2xl font-semibold text-white">
                    #{assignedProjectId}
                  </dd>
                  <p className="mt-1 text-xs text-slate-500">Assigned project</p>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Employee ID</dt>
                  <dd className="mt-1 text-2xl font-semibold text-white">
                    #{assignedEmployeeId}
                  </dd>
                  <p className="mt-1 text-xs text-slate-500">Assignment confirmed</p>
                </div>
              </dl>
              <div className="mt-4 flex items-center gap-2 rounded-lg border border-emerald-400/15 bg-emerald-500/[0.06] px-3 py-3">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-300" />
                <p className="text-sm text-slate-300">
                  Project assignment completed successfully.
                </p>
              </div>
            </div>
          )}
          {announcementCreated && (
            <div className="mt-4 rounded-xl border border-emerald-400/20 bg-slate-950/40 p-4">
              <h3 className="mb-3 text-sm font-semibold text-emerald-300">
                Announcement Details
              </h3>
              <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {announcement.id != null && (
                  <div>
                    <dt className="text-xs text-slate-400">Announcement ID</dt>
                    <dd className="mt-1 text-sm text-white">#{String(announcement.id)}</dd>
                  </div>
                )}
                {(announcement.author_name || announcement.author_id != null) && (
                  <div>
                    <dt className="text-xs text-slate-400">Author</dt>
                    <dd className="mt-1 text-sm text-white">{announcement.author_name || `Employee #${announcement.author_id}`}</dd>
                  </div>
                )}
                {typeof announcement.title === "string" && (
                  <div className="sm:col-span-2">
                    <dt className="text-xs text-slate-400">Title</dt>
                    <dd className="mt-1 break-words text-sm font-medium text-white">{announcement.title}</dd>
                  </div>
                )}
                {(typeof announcement.body === "string" || typeof announcement.message === "string") && (
                  <div className="sm:col-span-2">
                    <dt className="text-xs text-slate-400">Message</dt>
                    <dd className="mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-slate-200">{announcement.body ?? announcement.message}</dd>
                  </div>
                )}
                {typeof announcement.created_at === "string" && (
                  <div className="sm:col-span-2">
                    <dt className="text-xs text-slate-400">Created</dt>
                    <dd className="mt-1 text-sm text-slate-300">{new Date(announcement.created_at).toLocaleString()}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}
          {isLeaveConfirmation && leaveRequest && (
            <div className="mt-4 rounded-xl border border-emerald-400/20 bg-slate-950/40 p-4">
              <h3 className="mb-3 text-sm font-semibold text-emerald-300">
                Leave Request Details
              </h3>
              <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-slate-400">Request ID</dt>
                  <dd className="mt-1 text-sm text-white">#{String(leaveRequest.id ?? "—")}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Leave Type</dt>
                  <dd className="mt-1 text-sm text-white">{leaveType}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Start Date</dt>
                  <dd className="mt-1 text-sm text-white">{formatDate(leaveRequest.start_date)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">End Date</dt>
                  <dd className="mt-1 text-sm text-white">{formatDate(leaveRequest.end_date)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Duration</dt>
                  <dd className="mt-1 text-sm text-white">{leaveDuration}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-400">Status</dt>
                  <dd className="mt-1">
                    <span
                      className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${
                        leaveStatus === "approved"
                          ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-300"
                          : leaveStatus === "rejected"
                            ? "border-red-400/20 bg-red-500/10 text-red-300"
                            : "border-amber-400/20 bg-amber-500/10 text-amber-200"
                      }`}
                    >
                      {leaveStatus === "pending" ? "Pending Approval" : leaveStatus.replaceAll("_", " ").toUpperCase()}
                    </span>
                  </dd>
                </div>
                {typeof leaveRequest.reason === "string" && leaveRequest.reason.trim() && (
                  <div className="sm:col-span-2">
                    <dt className="text-xs text-slate-400">Reason</dt>
                    <dd className="mt-1 break-words text-sm text-white">{leaveRequest.reason}</dd>
                  </div>
                )}
              </dl>
            </div>
          )}
          {/* Project assignment results */}
          {projects.length > 0 && (
            <div className="mt-4 overflow-hidden rounded-xl border border-slate-700 bg-slate-950/60">
              <div className="flex items-center justify-between gap-3 border-b border-slate-700 px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-100">
                  My Project Assignments
                </h3>
                <span className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-slate-300">
                  {projects.length} project(s)
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-900/80">
                    <tr>
                      <th className="px-4 py-3 font-semibold text-slate-300">
                        Project
                      </th>
                      <th className="px-4 py-3 font-semibold text-slate-300">
                        Description
                      </th>
                      <th className="px-4 py-3 font-semibold text-slate-300">
                        Status
                      </th>
                      <th className="px-4 py-3 font-semibold text-slate-300">
                        My Role
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {projects.map((project, index) => (
                      <tr
                        key={project.project_id ?? index}
                        className="hover:bg-white/[0.02]"
                      >
                        <td className="px-4 py-3 font-medium text-slate-100">
                          {project.project_name || "Unnamed project"}
                        </td>
                        <td className="max-w-md whitespace-normal px-4 py-3 text-slate-400">
                          {project.project_description || "—"}
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-flex rounded-full border border-blue-400/20 bg-blue-500/10 px-2.5 py-1 text-xs font-medium text-blue-300">
                            {(project.project_status || "UNKNOWN")
                              .replaceAll("_", " ")
                              .toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          {project.role_on_project || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {/* Leave request history */}
          {leaveRequests.length > 0 && (
            <div className="mt-4 overflow-hidden rounded-xl border border-emerald-400/20 bg-slate-950/60">
              <div className="flex items-center justify-between gap-3 border-b border-emerald-400/10 px-4 py-3">
                <div>
                  <h3 className="text-sm font-semibold text-emerald-300">
                    Leave Request History
                  </h3>
                  {actionData.details?.employee_id != null && (
                    <p className="mt-1 text-xs text-slate-500">
                      Employee ID: {actionData.details.employee_id}
                    </p>
                  )}
                </div>
                <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-300">
                  {actionData.details?.meta?.total ?? leaveRequests.length} request(s)
                </span>
              </div>
              <div className="max-h-[520px] overflow-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="sticky top-0 z-10 bg-slate-900/95">
                    <tr>
                      <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-300">Request ID</th>
                      <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-300">Leave Type</th>
                      <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-300">Start Date</th>
                      <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-300">End Date</th>
                      <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-300">Duration</th>
                      <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-300">Approval Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {leaveRequests.map((leave, index) => {
                      const leaveStatus = (leave.status || "UNKNOWN").replaceAll("_", " ").toUpperCase();
                      const statusClass =
                        leaveStatus === "APPROVED"
                          ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-300"
                          : leaveStatus === "REJECTED"
                            ? "border-red-400/20 bg-red-500/10 text-red-300"
                            : leaveStatus === "CANCELLED"
                              ? "border-slate-500/20 bg-slate-500/10 text-slate-300"
                              : "border-amber-400/20 bg-amber-500/10 text-amber-200";
                      const startTime = leave.start_date ? Date.parse(`${leave.start_date}T00:00:00Z`) : NaN;
                      const endTime = leave.end_date ? Date.parse(`${leave.end_date}T00:00:00Z`) : NaN;
                      const duration =
                        leave.is_half_day
                          ? "Half day"
                          : Number.isFinite(startTime) && Number.isFinite(endTime) && endTime >= startTime
                            ? `${Math.floor((endTime - startTime) / 86400000) + 1} day${Math.floor((endTime - startTime) / 86400000) + 1 === 1 ? "" : "s"}`
                            : "—";
                      return (
                        <tr key={`${leave.id ?? "leave"}-${index}`} className="hover:bg-white/[0.02]">
                          <td className="whitespace-nowrap px-4 py-3 font-medium text-white">#{leave.id ?? "—"}</td>
                          <td className="whitespace-nowrap px-4 py-3 text-slate-200">{formatLabel(leave.leave_type || "Leave")}</td>
                          <td className="whitespace-nowrap px-4 py-3 text-slate-300">{formatDate(leave.start_date)}</td>
                          <td className="whitespace-nowrap px-4 py-3 text-slate-300">{formatDate(leave.end_date)}</td>
                          <td className="whitespace-nowrap px-4 py-3 text-slate-300">{duration}</td>
                          <td className="whitespace-nowrap px-4 py-3">
                            <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass}`}>
                              {leaveStatus}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          {/* Ticket results */}
          {tickets.length > 0 && (
            <div className="mt-4 rounded-xl border border-emerald-400/20 bg-slate-950/40 p-4 space-y-3">
              <div className="flex items-center justify-between gap-3 border-b border-emerald-400/10 pb-3">
                <h3 className="text-sm font-semibold text-emerald-300">
                  {ticketCreated ? "Ticket Creation Details" : "Ticket Details"}
                </h3>
                <span className="rounded-full border border-emerald-400/20 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-300">
                  {ticketCreated ? "Created successfully" : `${actionData.details?.meta?.total ?? tickets.length} ticket(s)`}
                </span>
              </div>
              {tickets.map((ticket, index) => {
                const ticketStatus = (ticket.status ?? "UNKNOWN")
                  .replaceAll("_", " ")
                  .toUpperCase();
                const statusClass =
                  ticketStatus === "RESOLVED"
                    ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-300"
                    : ticketStatus === "OPEN"
                      ? "border-amber-400/20 bg-amber-500/10 text-amber-300"
                      : "border-blue-400/20 bg-blue-500/10 text-blue-300";
                return (
                  <article
                    key={ticket.id ?? index}
                    className="overflow-hidden rounded-xl border border-emerald-400/20 bg-slate-950/70"
                  >
                    <div className="flex flex-col gap-3 border-b border-emerald-400/10 p-4 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-indigo-300">
                          Ticket #{ticket.id ?? "—"}
                        </p>
                        <h4 className="mt-1 break-words font-semibold text-white">
                          {ticket.title || "Untitled ticket"}
                        </h4>
                      </div>
                      <span
                        className={`inline-flex w-fit shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass}`}
                      >
                        {ticketStatus}
                      </span>
                    </div>
                    <div className="space-y-4 p-4">
                      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                        <div>
                          <p className="text-xs text-slate-500">Category</p>
                          <p className="mt-1 text-sm text-slate-200">
                            {ticket.category || "—"}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500">Priority</p>
                          <p className="mt-1 text-sm text-slate-200">
                            {ticket.priority || "—"}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-slate-500">Assignee ID</p>
                          <p className="mt-1 text-sm text-slate-200">
                            {ticket.assignee_id ?? "Unassigned"}
                          </p>
                        </div>
                      </div>
                      {ticket.description && (
                        <div>
                          <p className="text-xs text-slate-500">Description</p>
                          <p className="mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-slate-300">
                            {ticket.description}
                          </p>
                        </div>
                      )}
                      {ticket.created_at && (
                        <p className="text-xs text-slate-500">
                          Created:{" "}
                          {new Date(ticket.created_at).toLocaleString()}
                        </p>
                      )}
                      {ticket.onboarding_tasks &&
                        ticket.onboarding_tasks.length > 0 && (
                          <div className="border-t border-slate-800 pt-3">
                            <h5 className="mb-3 text-sm font-medium text-slate-200">
                              Onboarding Tasks
                            </h5>
                            <div className="space-y-2">
                              {ticket.onboarding_tasks.map((task, taskIndex) => (
                                <div
                                  key={task.id ?? taskIndex}
                                  className="flex items-start gap-3 rounded-lg bg-slate-900/80 p-3"
                                >
                                  {task.is_completed ? (
                                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                                  ) : (
                                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                                  )}
                                  <div className="min-w-0 flex-1">
                                    <p className="break-words text-sm text-slate-200">
                                      {task.task_name || "Untitled task"}
                                    </p>
                                    <p className="mt-1 text-xs text-slate-500">
                                      {task.is_completed
                                        ? "Completed"
                                        : "Pending"}
                                      {task.due_date
                                        ? ` · Due ${task.due_date}`
                                        : ""}
                                    </p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                    </div>
                  </article>
                );
              })}
            </div>
          )}
          {/* Existing leave balance table */}
          {balances.length > 0 && (
            <div className="mt-4 overflow-hidden rounded-xl border border-slate-700 bg-slate-950/60">
              <div className="border-b border-slate-700 px-4 py-3">
                <h3 className="text-sm font-medium text-slate-200">
                  Leave Balance
                </h3>
                {actionData.details?.employee_id != null && (
                  <p className="mt-1 text-xs text-slate-500">
                    Employee ID: {actionData.details.employee_id}
                  </p>
                )}
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-900/80">
                    <tr>
                      <th className="px-4 py-3 font-semibold text-slate-300">Leave type</th>
                      <th className="px-4 py-3 text-right font-semibold text-slate-300">Total</th>
                      <th className="px-4 py-3 text-right font-semibold text-slate-300">Used</th>
                      <th className="px-4 py-3 text-right font-semibold text-slate-300">Remaining</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {balances.map((balance, index) => (
                      <tr key={`${balance.leave_type ?? "leave"}-${index}`}>
                        <td className="px-4 py-3 text-slate-200">
                          {formatLabel(balance.leave_type ?? "Leave")}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-300">
                          {formatCellValue(balance.total)}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-300">
                          {formatCellValue(balance.used)}
                        </td>
                        <td className="px-4 py-3 text-right font-semibold text-emerald-300">
                          {balance.available === false
                            ? "Unavailable"
                            : `${formatCellValue(balance.remaining)} days`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {balances.some((balance) => balance.note) && (
                <div className="border-t border-slate-700 px-4 py-3 text-xs text-amber-200/80">
                  {balances
                    .filter((balance) => balance.note)
                    .map((balance, index) => (
                      <p key={`${balance.leave_type ?? "note"}-${index}`}>
                        {formatLabel(balance.leave_type ?? "Leave")}: {balance.note}
                      </p>
                    ))}
                </div>
              )}
            </div>
          )}
          
          {failed && (
            <div className="mt-3 flex items-start gap-2 text-xs text-amber-200/70">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                The action was not confirmed as completed. Review the response
                status before retrying to avoid duplicate requests.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
function IntentBadge({
  intent,
}: {
  intent: AIRouterResult["intent"];
}) {
  const config: Record<
    AIRouterResult["intent"],
    { label: string; className: string }
  > = {
    policy: {
      label: "POLICY",
      className: "bg-blue-500/10 text-blue-300 border border-blue-400/20",
    },
    sql: {
      label: "SQL / HR INTELLIGENCE",
      className:
        "bg-purple-500/10 text-purple-300 border border-purple-400/20",
    },
    action: {
      label: "HR ACTION",
      className:
        "bg-amber-500/10 text-amber-300 border border-amber-400/20",
    },
    unknown: {
      label: "UNSUPPORTED",
      className: "bg-slate-500/10 text-slate-400 border border-slate-400/20",
    },
  };
  const current = config[intent];
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-[10px] font-semibold tracking-wide ${current.className}`}
    >
      {current.label}
    </span>
  );
}
function formatLabel(value: string): string {
  return value
    .replace(/\_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}
function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}
