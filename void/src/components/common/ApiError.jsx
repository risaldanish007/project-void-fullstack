const ApiError = ({
  error,
  title = "Unable to load this page",
  onRetry,
  className = "",
}) => {
  const status = error?.response?.status;
  const message = !error?.response
    ? "The server could not be reached. Check your connection and try again."
    : status === 401
      ? "Your session may have expired. Please sign in and try again."
      : status === 403
        ? "You do not have permission to complete this request."
        : status === 404
          ? "The requested resource could not be found."
          : status >= 500
            ? "The server encountered an error while handling this request."
            : "The request could not be completed. Please try again.";

  return (
    <section
      className={`flex min-h-[35vh] flex-col items-center justify-center gap-3 px-6 text-center ${className}`}
      role="alert"
    >
      <h2 className="font-mono text-sm font-bold uppercase tracking-[0.25em] text-red-400">
        {title}
      </h2>
      <p className="max-w-md text-xs text-white/50">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={() => onRetry()}
          className="mt-2 rounded-full border border-white/20 px-5 py-2 font-mono text-[10px] font-bold uppercase tracking-widest text-white transition hover:border-white hover:bg-white hover:text-black"
        >
          Try again
        </button>
      )}
    </section>
  );
};

export default ApiError;
