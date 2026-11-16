const REQUEST_TIMEOUT_CODES = new Set(["ECONNABORTED", "ETIMEDOUT"]);
const REQUEST_CANCELED_CODES = new Set(["ERR_CANCELED"]);

export const isBackendUnavailable = (errorOrStatus) => {
  const status =
    typeof errorOrStatus === "object" && errorOrStatus !== null
      ? errorOrStatus.status ?? errorOrStatus.response?.status
      : errorOrStatus;
  const code = errorOrStatus?.code;

  if (
    REQUEST_TIMEOUT_CODES.has(code) ||
    REQUEST_CANCELED_CODES.has(code) ||
    errorOrStatus?.name === "CanceledError"
  ) {
    return false;
  }

  // HTTP responses mean the service was reached. A response-less timeout is
  // also distinct from a confirmed connection failure.
  return status == null && !errorOrStatus?.isTimeout;
};
