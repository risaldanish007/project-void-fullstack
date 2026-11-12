
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { accountsClient } from "../api/apiClient";

const Register = () => {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const navigate = useNavigate();

  const mutation = useMutation({
    mutationFn: async (registrationData) => {
      const response = await accountsClient.post(
        "/register/",
        registrationData
      );

      return response.data;
    },

    onSuccess: (_, variables) => {
      toast.success("Account created! Check your email for the OTP.");

      navigate("/verify-email", {
        state: { email: variables.email },
      });
    },

    onError: (error) => {
      const data = error.response?.data;

      if (data && typeof data === "object") {
        const messages = Object.entries(data)
          .map(([field, value]) => {
            const message = Array.isArray(value)
              ? value.join(" ")
              : value;

            return `${field}: ${message}`;
          })
          .join("\n");

        toast.error(messages || "Could not create your account.");
      } else {
        toast.error("Could not connect to the server. Please try again.");
      }
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

    mutation.mutate({
      first_name: cleanFirstName,
      last_name: cleanLastName,
      email: cleanEmail,
      password,
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black relative overflow-hidden">
      <div className="absolute w-[600px] h-[600px] bg-white/5 blur-3xl rounded-full -top-40 -left-40" />

      <div className="absolute w-[500px] h-[500px] bg-white/5 blur-3xl rounded-full bottom-0 right-0" />

      <form
        onSubmit={handleSubmit}
        className="relative z-10 w-[350px] max-w-[calc(100vw-2rem)] p-6 sm:p-8 rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl flex flex-col gap-4"
      >
        <h2 className="text-white text-2xl font-semibold tracking-wide">
          Register
        </h2>

        <input
          type="text"
          placeholder="First name"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          autoComplete="given-name"
          className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/40 outline-none focus:border-white/30 transition"
          required
        />

        <input
          type="text"
          placeholder="Last name"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          autoComplete="family-name"
          className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/40 outline-none focus:border-white/30 transition"
        />

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/40 outline-none focus:border-white/30 transition"
          required
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/40 outline-none focus:border-white/30 transition"
          required
        />

        <input
          type="password"
          placeholder="Confirm password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          autoComplete="new-password"
          className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/40 outline-none focus:border-white/30 transition"
          required
        />

        <button
          type="submit"
          disabled={mutation.isPending}
          className="mt-2 bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-lg border border-white/10 backdrop-blur-md transition active:scale-[0.98]"
        >
          {mutation.isPending ? "Creating account..." : "Register"}
        </button>

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
