import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useDispatch } from "react-redux";
import { setCredentials } from "../store/authSlice";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { toast } from "react-toastify";

import {
    accountsClient,
    cartClient,
    ensureCsrfToken,
    setAccessToken,
    clearAccessToken,
} from "../api/apiClient";

import { fetchCurrentCart } from "../store/cartSlice";
import { clearExplicitLogout } from "../store/authSlice";

const Login = () => {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);

    const navigate = useNavigate();
    const dispatch = useDispatch();
    const location = useLocation();

    const mutation = useMutation({
        mutationFn: async (credentials) => {
            await ensureCsrfToken();

            const tokenResponse = await accountsClient.post(
                "/login/",
                credentials
            );

            setAccessToken(tokenResponse.data.access);
            clearExplicitLogout();

            const profileResponse = await accountsClient.get("/profile/");

            let cartMergeFailed = false;

            try {
                await cartClient.post("/merge/");
            } catch {
                cartMergeFailed = true;
            }

            return {
                user: profileResponse.data,
                cartMergeFailed
            };
        },

        onSuccess: async ({ user, cartMergeFailed }) => {
            dispatch(setCredentials(user));

            try {
                await dispatch(fetchCurrentCart()).unwrap();

                toast.success(
                    cartMergeFailed
                        ? "Logged in, but guest cart could not be merged."
                        : "Login successful"
                );
            } catch {
                toast.error("Logged in, but could not load your cart");
            }

            const origin = location.state?.from?.pathname || "/";
            navigate(origin);
        },

        onError: (error) => {
            clearAccessToken();
            toast.error(
                error.response?.data?.detail || "Could not log in"
            );
        },
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        mutation.mutate({ email, password });
    };

    return (
        <div
            className="min-h-screen flex items-center justify-center relative overflow-hidden bg-black bg-cover bg-center bg-no-repeat px-4"
            style={{
                backgroundImage: "url('/images/login-bg.jpg')"
            }}
        >
            {/* Dark overlay */}
            <div className="absolute inset-0 bg-black/65 backdrop-blur-[2px]" />

            {/* Gradient effects */}
            <div className="absolute inset-0 bg-gradient-to-br from-black/50 via-transparent to-black/80" />

            {/* Ambient glow */}
            <div className="absolute w-[500px] h-[500px] bg-white/5 blur-3xl rounded-full -top-40 -left-40" />

            <div className="absolute w-[400px] h-[400px] bg-white/5 blur-3xl rounded-full bottom-0 right-0" />

            {/* Login form */}
            <form
                onSubmit={handleSubmit}
                className="relative z-10 w-[350px] max-w-full p-6 sm:p-8 rounded-2xl bg-black/40 backdrop-blur-2xl border border-white/10 shadow-2xl flex flex-col gap-4"
            >
                <h2 className="text-white text-2xl font-semibold tracking-wide">
                    Login
                </h2>

                {/* Email */}
                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/40 outline-none focus:border-white/40 transition"
                    required
                />

                {/* Password with visibility toggle */}
                <div className="relative">
                    <input
                        type={showPassword ? "text" : "password"}
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        autoComplete="current-password"
                        className="w-full bg-white/5 border border-white/10 rounded-lg pl-4 pr-12 py-3 text-white placeholder-white/40 outline-none focus:border-white/40 transition"
                        required
                    />

                    <button
                        type="button"
                        onClick={() => setShowPassword((prev) => !prev)}
                        aria-label={showPassword ? "Hide password" : "Show password"}
                        aria-pressed={showPassword}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white transition-colors focus:outline-none"
                    >
                        {showPassword ? (
                            // Eye-off icon
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
                                <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
                                <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c5 0 8.27 4.11 9 7-.29 1.18-.94 2.38-1.87 3.43" />
                                <path d="M6.61 6.61C3.91 8.1 2.38 10.36 2 12c.73 2.89 4 7 10 7a9.93 9.93 0 0 0 5.39-1.61" />
                                <path d="m2 2 20 20" />
                            </svg>
                        ) : (
                            // Eye icon
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
                                <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                                <circle cx="12" cy="12" r="3" />
                            </svg>
                        )}
                    </button>
                </div>

                {/* Submit */}
                <button
                    type="submit"
                    disabled={mutation.isPending}
                    className="mt-2 bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-lg border border-white/10 backdrop-blur-md transition active:scale-[0.98]"
                >
                    {mutation.isPending ? "Authenticating..." : "Login"}
                </button>

                {/* Register */}
                <div className="mt-4 text-center">
                    <p className="text-white/40 text-[10px] uppercase tracking-[0.2em] font-mono">
                        New Operative?{" "}

                        <Link
                            to="/register"
                            className="text-white hover:text-green-500 transition-colors underline underline-offset-4 decoration-white/10 hover:decoration-green-500/50"
                        >
                            Initialize Account
                        </Link>
                    </p>
                </div>
            </form>
        </div>
    );
};

export default Login;
