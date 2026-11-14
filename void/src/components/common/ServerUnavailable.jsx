const ServerUnavailable = ({ onRetry, isRetrying = false }) => (
  <main
    className="fixed inset-0 z-[9999] flex min-h-dvh flex-col items-center justify-center bg-[#050507] px-6 text-center text-white"
    role="alert"
  >
    <div className="max-w-lg">
      <p className="mb-4 font-mono text-[10px] uppercase tracking-[0.5em] text-red-400">
        Connection unavailable
      </p>
      <h1 className="text-3xl font-black uppercase italic tracking-tight sm:text-4xl">
        VOID is temporarily offline
      </h1>
      <p className="mt-4 text-sm leading-relaxed text-white/60">
        We can’t reach the service right now. Check your connection, then retry.
      </p>
      <button
        type="button"
        onClick={onRetry}
        disabled={isRetrying}
        className="mt-8 rounded-full border border-white/20 px-7 py-3 font-mono text-[10px] font-bold uppercase tracking-[0.25em] transition hover:border-white hover:bg-white hover:text-black disabled:cursor-wait disabled:opacity-50"
      >
        {isRetrying ? "Checking service…" : "Retry connection"}
      </button>
    </div>
  </main>
);

export default ServerUnavailable;
