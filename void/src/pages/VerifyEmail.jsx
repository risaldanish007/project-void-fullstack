
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { accountsClient } from "../api/apiClient";

const VerifyEmail = () => {
  const [otp, setOtp] = useState("");

  const location = useLocation();
  const navigate = useNavigate();

  const email = location.state?.email;

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

      navigate("/login", { replace: true });
    },

    onError: (error) => {
      const message =
        error.response?.data?.detail ||
        "Verification failed. Please try again.";

      toast.error(message);
    },
  });

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!email) {
      toast.error("Email address is missing. Please register again.");
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

  if (!email) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-black text-white gap-4">
        <h2 className="text-xl font-semibold">Verification unavailable</h2>

        <p className="text-white/50 text-sm">
          Please register again to start email verification.
        </p>

        <Link
          to="/register"
          className="text-white underline underline-offset-4"
        >
          Back to Register
        </Link>
      </div>
    );
  }

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
            We've sent a verification code to
          </p>

          <p className="text-white text-sm mt-1 break-all">
            {email}
          </p>
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
          disabled={mutation.isPending || otp.length !== 6}
          className="bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-lg border border-white/10 transition active:scale-[0.98]"
        >
          {mutation.isPending ? "Verifying..." : "Verify Email"}
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
      </form>
    </div>
  );
};

export default VerifyEmail;
