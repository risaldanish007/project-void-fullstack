
import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { accountsClient } from "../api/apiClient";
import {
  clearPendingRegistrationEmail,
  getPendingRegistrationEmail,
  savePendingRegistrationEmail,
} from "../utils/pendingRegistration";

const VerifyEmail = () => {
  const [otp, setOtp] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);

  const location = useLocation();
  const navigate = useNavigate();

  const [email, setEmail] = useState(
    () => location.state?.email || getPendingRegistrationEmail()
  );
  const [isEmailEditable, setIsEmailEditable] = useState(
    () => !location.state?.email && !getPendingRegistrationEmail()
  );

  useEffect(() => {
    if (resendCooldown <= 0) return undefined;

    const timer = window.setTimeout(
      () => setResendCooldown((seconds) => Math.max(0, seconds - 1)),
      1000
    );
    return () => window.clearTimeout(timer);
  }, [resendCooldown]);

  const mutation = useMutation({
    mutationFn: async (verificationData) => {
      const response = await accountsClient.post(
        "/verify-email/",
        verificationData
      );

      return response.data;
    },

    onSuccess: (data) => {
      toast.success(data.detail || "Email verified successfully!");
      clearPendingRegistrationEmail();

      navigate("/login", { replace: true });
    },

    onError: (error) => {
      const responseMessage = error.response?.data?.detail;
      const message = !error.response
        ? "Connection failed. Check your internet and try again."
        : responseMessage === "OTP has expired."
          ? "That code has expired. Request a new verification code below."
          : responseMessage || "Verification failed. Please try again.";

      toast.error(message);
    },
  });

  const resendMutation = useMutation({
    mutationFn: async (emailAddress) => {
      const response = await accountsClient.post("/resend-otp/", {
        email: emailAddress,
      });
      return response.data;
    },
    onSuccess: (data) => {
      setResendCooldown(60);
      toast.success(data.detail || "If the account can be verified, a new code is on its way.");
    },
    onError: (error) => {
      if (error.response?.status === 429) {
        const retryAfter = Number(error.response.headers?.["retry-after"]);
        setResendCooldown(Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : 60);
        toast.error("Please wait before requesting another verification code.");
      } else if (!error.response) {
        toast.error("Connection failed. Restore your internet connection and retry.");
      } else {
        toast.error("We couldn't send a code right now. Please try again shortly.");
      }
    },
  });

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!email) {
      toast.error("Enter your email address to continue verification.");
      return;
    }

    if (!/^\d{6}$/.test(otp)) {
      toast.error("Enter a valid 6-digit OTP.");
      return;
    }

    mutation.mutate({
      email,
      otp,
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black relative overflow-hidden">
      <div className="absolute w-[600px] h-[600px] bg-white/5 blur-3xl rounded-full -top-40 -left-40" />

      <div className="absolute w-[500px] h-[500px] bg-white/5 blur-3xl rounded-full bottom-0 right-0" />

      <form
        onSubmit={handleSubmit}
        className="relative z-10 w-[350px] max-w-[calc(100vw-2rem)] p-6 sm:p-8 rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl flex flex-col gap-5"
      >
        <div className="text-center">
          <h2 className="text-white text-2xl font-semibold tracking-wide">
            Verify Email
          </h2>

          <p className="text-white/40 text-xs mt-3 leading-relaxed">
            Enter your email and the verification code we sent.
          </p>

          {!isEmailEditable && email ? (
            <>
              <p className="text-white text-sm mt-1 break-all">{email}</p>
              <button
                type="button"
                onClick={() => setIsEmailEditable(true)}
                className="mt-1 text-white/50 hover:text-white text-xs underline underline-offset-4"
              >
                Change email
              </button>
            </>
          ) : (
            <input
              type="email"
              autoComplete="email"
              placeholder="Email address"
              value={email}
              onChange={(event) => {
                const value = event.target.value.trim().toLowerCase();
                setEmail(value);
                savePendingRegistrationEmail(value);
              }}
              className="mt-3 w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-white/30 outline-none focus:border-white/30 transition"
              required
            />
          )}
        </div>

        <input
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          placeholder="Enter 6-digit OTP"
          value={otp}
          onChange={(event) =>
            setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
          }
          className="bg-white/5 border border-white/10 rounded-lg px-4 py-4 text-white text-center text-2xl tracking-[0.5em] placeholder:text-white/30 placeholder:text-sm placeholder:tracking-normal outline-none focus:border-white/30 transition"
          required
        />

        <button
          type="submit"
          disabled={mutation.isPending || !email || otp.length !== 6}
          className="bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-lg border border-white/10 transition active:scale-[0.98]"
        >
          {mutation.isPending ? "Verifying..." : "Verify Email"}
        </button>

        <button
          type="button"
          onClick={() => {
            const cleanEmail = email.trim().toLowerCase();
            if (!cleanEmail) {
              toast.error("Enter your email address first.");
              return;
            }
            setEmail(cleanEmail);
            savePendingRegistrationEmail(cleanEmail);
            resendMutation.mutate(cleanEmail);
          }}
          disabled={resendMutation.isPending || resendCooldown > 0}
          className="text-white/70 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed text-sm py-2 transition"
        >
          {resendMutation.isPending
            ? "Sending code..."
            : resendCooldown > 0
              ? `Resend available in ${resendCooldown}s`
              : "Resend verification code"}
        </button>

        <p className="text-center text-white/40 text-[10px] uppercase tracking-widest font-mono">
          Already verified?{" "}
          <Link
            to="/login"
            className="text-white hover:text-green-500 underline underline-offset-4"
          >
            Log in
          </Link>
        </p>

        <p className="text-center text-white/40 text-xs">
          Need to retry registration?{" "}
          <Link
            to="/register"
            className="text-white/70 hover:text-white underline underline-offset-4"
          >
            Return to registration
          </Link>
        </p>
      </form>
    </div>
  );
};

export default VerifyEmail;
