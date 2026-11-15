import { createServer } from "node:http";
const port = Number(process.env.PORT || 5000);
createServer((request, response) => {
  if (request.url === "/health" && request.method === "GET") {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ status: "ok" }));
    return;
  }
  response.writeHead(404, { "content-type": "application/json" });
  response.end(JSON.stringify({ detail: "Not found." }));
}).listen(port, "0.0.0.0", () => {
  console.log("VOID health server listening on port " + port);
});
