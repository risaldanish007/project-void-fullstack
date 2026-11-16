import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { accountsClient } from "../api/apiClient";
import {
  clearPendingRegistrationEmail,
  savePendingRegistrationEmail,
} from "../utils/pendingRegistration";

const REGISTER_REQUEST_TIMEOUT_MS = 30000;

const EyeIcon = ({ visible }) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.7"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    {visible ? (
      <>
        <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
        <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c5 0 8.27 4.11 9 7-.29 1.18-.94 2.38-1.87 3.43" />
        <path d="M6.61 6.61C3.91 8.1 2.38 10.36 2 12c.73 2.89 4 7 10 7a9.93 9.93 0 0 0 5.39-1.61" />
        <path d="m2 2 20 20" />
      </>
    ) : (
      <>
        <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    )}
  </svg>
);

const Register = () => {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: async (registrationData) => {
      const response = await accountsClient.post(
        "/register/",
        registrationData,
        { timeout: REGISTER_REQUEST_TIMEOUT_MS }
      );

      return response.data;
    },

    onSuccess: (_, variables) => {
      savePendingRegistrationEmail(variables.email);
      toast.success("Check your email for a verification code, or request a new one.");

      navigate("/verify-email", {
        state: { email: variables.email },
      });
    },

    onError: (error, variables) => {
      const submittedEmail = variables?.email;

      if (!error.response || error.response.status >= 500) {
        if (submittedEmail) {
          savePendingRegistrationEmail(submittedEmail);
          navigate("/verify-email", {
            state: { email: submittedEmail, registrationOutcomeUnknown: true },
          });
        }
        toast.info(
          "We couldn't confirm the registration result. You can request a verification code here, or retry registration if no account was created."
        );
        return;
      }

      if (error.response.status === 429) {
        toast.error("Too many registration attempts. Please wait and try again.");
        return;
      }

      if (error.response.data?.code === "account_already_active") {
        clearPendingRegistrationEmail();
        toast.error("An account with this email already exists. Please log in.");
        return;
      }

      const data = error.response.data;
      const message =
        data?.detail ||
        data?.email?.[0] ||
        data?.password?.[0] ||
        "Could not create your account. Check your details and try again.";
      toast.error(message);
    },
  });

  const handleSubmit = (event) => {
    event.preventDefault();

    const cleanFirstName = firstName.trim();
    const cleanLastName = lastName.trim();
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanFirstName) {
      toast.error("Enter your first name.");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    savePendingRegistrationEmail(cleanEmail);
    mutation.mutate({
      first_name: cleanFirstName,
      last_name: cleanLastName,
      email: cleanEmail,
      password,
    });
  };

  const inputClass =
    "w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/40 outline-none focus:border-white/40 transition";

  const passwordClass =
    "w-full bg-white/5 border border-white/10 rounded-lg pl-4 pr-12 py-3 text-white placeholder-white/40 outline-none focus:border-white/40 transition";

  return (
    <div
      className="min-h-screen flex items-center justify-center relative overflow-hidden bg-black bg-cover bg-center bg-no-repeat px-4 py-8"
      style={{
        backgroundImage: "url('/images/login-bg.jpg')",
      }}
    >
      {/* Dark overlay */}
      <div className="absolute inset-0 bg-black/65 backdrop-blur-[2px]" />

      {/* Gradient effects */}
      <div className="absolute inset-0 bg-gradient-to-br from-black/50 via-transparent to-black/80" />

      {/* Ambient glow */}
      <div className="absolute w-[500px] h-[500px] bg-white/5 blur-3xl rounded-full -top-40 -left-40" />

      <div className="absolute w-[400px] h-[400px] bg-white/5 blur-3xl rounded-full bottom-0 right-0" />

      {/* Register form */}
      <form
        onSubmit={handleSubmit}
        className="relative z-10 w-[350px] max-w-full p-6 sm:p-8 rounded-2xl bg-black/40 backdrop-blur-2xl border border-white/10 shadow-2xl flex flex-col gap-4"
      >
        <h2 className="text-white text-2xl font-semibold tracking-wide">
          Register
        </h2>

        {/* First name */}
        <input
          type="text"
          placeholder="First name"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          autoComplete="given-name"
          className={inputClass}
          required
        />

        {/* Last name */}
        <input
          type="text"
          placeholder="Last name"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          autoComplete="family-name"
          className={inputClass}
        />

        {/* Email */}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          className={inputClass}
          required
        />

        {/* Password */}
        <div className="relative">
          <input
            type={showPassword ? "text" : "password"}
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            className={passwordClass}
            required
          />

          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            aria-pressed={showPassword}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white transition-colors focus:outline-none"
          >
            <EyeIcon visible={showPassword} />
          </button>
        </div>

        {/* Confirm password */}
        <div className="relative">
          <input
            type={showConfirmPassword ? "text" : "password"}
            placeholder="Confirm password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            className={passwordClass}
            required
          />

          <button
            type="button"
            onClick={() => setShowConfirmPassword((prev) => !prev)}
            aria-label={
              showConfirmPassword
                ? "Hide confirm password"
                : "Show confirm password"
            }
            aria-pressed={showConfirmPassword}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white transition-colors focus:outline-none"
          >
            <EyeIcon visible={showConfirmPassword} />
          </button>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={mutation.isPending}
          className="mt-2 bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-lg border border-white/10 backdrop-blur-md transition active:scale-[0.98]"
        >
          {mutation.isPending ? "Creating account..." : "Register"}
        </button>

        {/* Login link */}
        <div className="mt-4 text-center">
          <p className="text-white/40 text-[10px] uppercase tracking-[0.2em] font-mono">
            Already registered?{" "}

            <Link
              to="/login"
              className="text-white hover:text-green-500 transition-colors underline underline-offset-4 decoration-white/10 hover:decoration-green-500/50"
            >
              Log in
            </Link>
          </p>
        </div>
      </form>
    </div>
  );
};

export default Register;
