const PENDING_REGISTRATION_EMAIL_KEY = "void_pending_registration_email";

export function savePendingRegistrationEmail(email) {
  try {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(PENDING_REGISTRATION_EMAIL_KEY, email);
    }
  } catch {
    // Verification can still continue in router state for this tab.
  }
}

export function getPendingRegistrationEmail() {
  try {
    return typeof window === "undefined"
      ? ""
      : window.localStorage.getItem(PENDING_REGISTRATION_EMAIL_KEY) || "";
  } catch {
    return "";
  }
}

export function clearPendingRegistrationEmail() {
  try {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(PENDING_REGISTRATION_EMAIL_KEY);
    }
  } catch {
    // Storage may be disabled; this does not affect account verification.
  }
}
