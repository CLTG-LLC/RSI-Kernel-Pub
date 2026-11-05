// Minimal Java 21 dev evaluator host for RSI-Kernel (issue #7, design §7 S6).
// JDK only: com.sun.net.httpserver.HttpServer, no framework, built with plain javac.
//
// POST /evaluate  {"candidate_id": str, "item_ids": [str, ...]}
//   -> 200 {"results": [{"item_id", "score", "feedback"}, ...]} in request order
// GET  /count     -> {"items": <item evaluations run so far>}  (test probe)
//
// Budget, split checks and loopback-only exposure stay in the kernel's
// DevEvaluatorServer; this host only evaluates what it is sent.

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

public final class EvaluatorHost {
    // Toy task: item d<i> passes when the candidate text contains its keyword.
    private static final Map<String, String> KEYWORDS =
            Map.of("d0", "alpha", "d1", "beta", "d2", "gamma", "d3", "delta");
    private static final AtomicLong ITEMS = new AtomicLong();
    // Explicit IPv4 loopback, same as the kernel's LOOPBACK (src/rsi_kernel/evaluator.py).
    // InetAddress.getLoopbackAddress() can return ::1 when the JVM prefers IPv6.
    private static final String LOOPBACK = "127.0.0.1";

    public static void main(String[] args) throws IOException {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 0;
        HttpServer server = HttpServer.create(new InetSocketAddress(LOOPBACK, port), 0);
        server.createContext("/evaluate", EvaluatorHost::evaluate);
        server.createContext("/count", ex -> send(ex, 200, "{\"items\":" + ITEMS.get() + "}"));
        server.start();
        System.out.println("LISTENING " + server.getAddress().getPort());
        System.out.flush();
    }

    private static void evaluate(HttpExchange ex) throws IOException {
        if (!"POST".equals(ex.getRequestMethod())) {
            send(ex, 405, "{\"error\":\"method not allowed\"}");
            return;
        }
        String candidate;
        List<String> items;
        try {
            Json json = new Json(new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8));
            Map<String, Object> req = json.object();
            candidate = (String) req.get("candidate_id");
            @SuppressWarnings("unchecked")
            List<String> ids = (List<String>) req.get("item_ids");
            items = ids;
            if (candidate == null || items == null) throw new IllegalArgumentException("missing field");
        } catch (RuntimeException e) {
            send(ex, 400, "{\"error\":\"bad request\"}");
            return;
        }
        StringBuilder out = new StringBuilder("{\"results\":[");
        for (int i = 0; i < items.size(); i++) {
            String id = items.get(i);
            String kw = KEYWORDS.getOrDefault(id, "");
            boolean hit = !kw.isEmpty() && candidate.contains(kw);
            if (i > 0) out.append(',');
            out.append("{\"item_id\":").append(quote(id))
               .append(",\"score\":").append(hit ? "1.0" : "0.0")
               .append(",\"feedback\":").append(quote((hit ? "found " : "missing ") + kw)).append('}');
            ITEMS.incrementAndGet();
        }
        send(ex, 200, out.append("]}").toString());
    }

    private static void send(HttpExchange ex, int status, String body) throws IOException {
        byte[] data = body.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json");
        ex.sendResponseHeaders(status, data.length);
        try (var os = ex.getResponseBody()) {
            os.write(data);
        }
    }

    private static String quote(String s) {
        StringBuilder b = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"' -> b.append("\\\"");
                case '\\' -> b.append("\\\\");
                case '\n' -> b.append("\\n");
                case '\r' -> b.append("\\r");
                case '\t' -> b.append("\\t");
                default -> {
                    if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
                    else b.append(c);
                }
            }
        }
        return b.append('"').toString();
    }

    // ponytail: hand-rolled parser for the fixed request shape only (object of
    // strings and arrays of strings, RFC 8259 string escapes). No numbers, nested
    // objects, booleans or null. Swap in a JSON library if the contract grows.
    private static final class Json {
        private final String s;
        private int i;

        Json(String s) { this.s = s; }

        Map<String, Object> object() {
            Map<String, Object> m = new java.util.HashMap<>();
            expect('{');
            if (peek() != '}') {
                do {
                    String k = string();
                    expect(':');
                    m.put(k, peek() == '[' ? array() : string());
                } while (consume(','));
            }
            expect('}');
            ws();
            if (i != s.length()) throw new IllegalArgumentException("trailing data");
            return m;
        }

        private List<String> array() {
            List<String> l = new ArrayList<>();
            expect('[');
            if (peek() != ']') {
                do { l.add(string()); } while (consume(','));
            }
            expect(']');
            return l;
        }

        private String string() {
            expect('"');
            StringBuilder b = new StringBuilder();
            while (true) {
                char c = s.charAt(i++);
                if (c == '"') return b.toString();
                if (c != '\\') { b.append(c); continue; }
                char e = s.charAt(i++);
                switch (e) {
                    case '"', '\\', '/' -> b.append(e);
                    case 'b' -> b.append('\b');
                    case 'f' -> b.append('\f');
                    case 'n' -> b.append('\n');
                    case 'r' -> b.append('\r');
                    case 't' -> b.append('\t');
                    case 'u' -> { b.append((char) Integer.parseInt(s.substring(i, i + 4), 16)); i += 4; }
                    default -> throw new IllegalArgumentException("bad escape");
                }
            }
        }

        private void ws() { while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++; }
        private char peek() { ws(); return s.charAt(i); }
        private boolean consume(char c) { if (peek() == c) { i++; return true; } return false; }
        private void expect(char c) { if (!consume(c)) throw new IllegalArgumentException("expected " + c); }
    }
}
