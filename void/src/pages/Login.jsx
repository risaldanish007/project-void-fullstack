import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useDispatch } from "react-redux";
import { setCredentials } from "../store/authSlice";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { toast } from 'react-toastify'; // Added for official feedback

import { accountsClient, cartClient, ensureCsrfToken, setAccessToken, clearAccessToken } from "../api/apiClient";
import { fetchCurrentCart } from "../store/cartSlice";

const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();
    const dispatch = useDispatch();
    const location = useLocation();

const mutation = useMutation({
  mutationFn: async (credentials) => {
    await ensureCsrfToken();

    const tokenResponse = await accountsClient.post("/login/", credentials);
    setAccessToken(tokenResponse.data.access);

    const profileResponse = await accountsClient.get("/profile/");

    // Login should still succeed if guest-cart merging has a temporary problem.
    let cartMergeFailed = false;
    try {
      await cartClient.post("/merge/");
    } catch {
      cartMergeFailed = true;
    }

    return { user: profileResponse.data, cartMergeFailed };
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
    toast.error(error.response?.data?.detail || "Could not log in");
  },
});

    const handleSubmit = (e) => {
        e.preventDefault();
        mutation.mutate({ email, password });
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-black relative overflow-hidden">
            {/* subtle gradient glow */}
            <div className="absolute w-[600px] h-[600px] bg-white/5 blur-3xl rounded-full -top-40 -left-40" />
            <div className="absolute w-[500px] h-[500px] bg-white/5 blur-3xl rounded-full bottom-0 right-0" />
            
            <form
                onSubmit={handleSubmit}
                className="relative z-10 w-[350px] max-w-[calc(100vw-2rem)] p-6 sm:p-8 rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl flex flex-col gap-4"
            >
                <h2 className="text-white text-2xl font-semibold tracking-wide">Login</h2>

                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/40 outline-none focus:border-white/30 transition"
                    required
                />

                <input
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/40 outline-none focus:border-white/30 transition"
                    required
                />

                <button
                    type="submit"
                    disabled={mutation.isPending}
                    className="mt-2 bg-white/10 hover:bg-white/20 text-white py-3 rounded-lg border border-white/10 backdrop-blur-md transition active:scale-[0.98]"
                >
                    {mutation.isPending ? "Authenticating..." : "Login"}
                </button>

                <div className="mt-4 text-center">
                    <p className="text-white/40 text-[10px] uppercase tracking-[0.2em] font-mono">
                        New Operative?{' '}
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
