// Minimal Java 21 dev evaluator host for RSI-Kernel (issue #7, design §7 S6).
// JDK only: com.sun.net.httpserver.HttpServer, no framework, built with plain javac.
//
// POST /evaluate  {"candidate_id": str, "item_ids": [str, ...], "components"?: {name: base64}}
//   -> 200 {"results": [{"item_id", "score", "feedback"}, ...]} in request order
//   With "components" (issue #52 host contract) the host recomputes the kernel's
//   content_id over the decoded bytes, answers 400 on mismatch, and scores the
//   artifact text. Without it (S6 evaluator seam) candidate_id itself is the text.
// GET  /artifact  -> {"media_type": "text/plain", "components": {name: base64}}  (champion)
// POST /apply     {"candidate_id": str} -> {"applied": [...]}  (record-only, as GDPevo)
// GET  /applied   -> {"applied": [candidate_id, ...]}  (test probe)
// GET  /count     -> {"items": <item evaluations run so far>}  (test probe)
//
// Budget, split checks and loopback-only exposure stay in the kernel's
// DevEvaluatorServer; this host only evaluates what it is sent.

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;

public final class EvaluatorHost {
    // Toy task: item d<i> passes when the candidate text contains its keyword.
    private static final Map<String, String> KEYWORDS =
            Map.of("d0", "alpha", "d1", "beta", "d2", "gamma", "d3", "delta", "a0", "beta", "a1", "gamma");
    // Champion artifact served by GET /artifact: one data-only text component.
    private static final Map<String, String> CHAMPION = Map.of("SKILL.md", "Use alpha.");
    private static final List<String> APPLIED = new CopyOnWriteArrayList<>();
    private static final AtomicLong ITEMS = new AtomicLong();
    // Explicit IPv4 loopback, same as the kernel's LOOPBACK (src/rsi_kernel/evaluator.py).
    // InetAddress.getLoopbackAddress() can return ::1 when the JVM prefers IPv6.
    private static final String LOOPBACK = "127.0.0.1";

    public static void main(String[] args) throws IOException {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 0;
        HttpServer server = HttpServer.create(new InetSocketAddress(LOOPBACK, port), 0);
        server.createContext("/evaluate", EvaluatorHost::evaluate);
        server.createContext("/artifact", ex -> send(ex, 200, artifactJson()));
        server.createContext("/apply", EvaluatorHost::apply);
        server.createContext("/applied", ex -> send(ex, 200, appliedJson()));
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
            @SuppressWarnings("unchecked")
            Map<String, String> components = (Map<String, String>) req.get("components");
            if (components != null) {
                Map<String, byte[]> bytes = new java.util.HashMap<>();
                components.forEach((k, v) -> bytes.put(k, Base64.getDecoder().decode(v)));
                if (!contentId(bytes).equals(candidate)) throw new IllegalArgumentException("hash mismatch");
                StringBuilder text = new StringBuilder();
                bytes.values().forEach(b -> text.append(new String(b, StandardCharsets.UTF_8)).append('\n'));
                candidate = text.toString();
            }
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

    private static void apply(HttpExchange ex) throws IOException {
        try {
            if (!"POST".equals(ex.getRequestMethod())) throw new IllegalArgumentException("method");
            String id = (String) new Json(new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8))
                    .object().get("candidate_id");
            if (id == null) throw new IllegalArgumentException("missing field");
            APPLIED.add(id);  // record-only: the champion bytes are not swapped
        } catch (RuntimeException e) {
            send(ex, 400, "{\"error\":\"bad request\"}");
            return;
        }
        send(ex, 200, appliedJson());
    }

    private static String artifactJson() {
        StringBuilder b = new StringBuilder("{\"media_type\":\"text/plain\",\"components\":{");
        int i = 0;
        for (var e : CHAMPION.entrySet()) {
            if (i++ > 0) b.append(',');
            b.append(quote(e.getKey())).append(':')
             .append(quote(Base64.getEncoder().encodeToString(e.getValue().getBytes(StandardCharsets.UTF_8))));
        }
        return b.append("}}").toString();
    }

    private static String appliedJson() {
        StringBuilder b = new StringBuilder("{\"applied\":[");
        for (int i = 0; i < APPLIED.size(); i++) b.append(i > 0 ? "," : "").append(quote(APPLIED.get(i)));
        return b.append("]}").toString();
    }

    // Same identity as src/rsi_kernel/candidate.py content_id: sha256 over components
    // sorted by name (code-point order = UTF-8 byte order), each name and value
    // prefixed with its 8-byte big-endian length.
    static String contentId(Map<String, byte[]> components) {
        try {
            MessageDigest h = MessageDigest.getInstance("SHA-256");
            List<byte[]> names = new ArrayList<>();
            components.keySet().forEach(k -> names.add(k.getBytes(StandardCharsets.UTF_8)));
            names.sort(Arrays::compareUnsigned);
            for (byte[] name : names) {
                byte[] value = components.get(new String(name, StandardCharsets.UTF_8));
                for (byte[] part : new byte[][] {name, value}) {
                    h.update(java.nio.ByteBuffer.allocate(8).putLong(part.length).array());
                    h.update(part);
                }
            }
            return HexFormat.of().formatHex(h.digest());
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
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

    // ponytail: hand-rolled parser for the fixed request shapes only (object of
    // strings, arrays of strings and one level of string-valued objects, RFC 8259
    // string escapes). No numbers, booleans or null. Swap in a JSON library if the
    // contract grows.
    private static final class Json {
        private final String s;
        private int i;

        Json(String s) { this.s = s; }

        Map<String, Object> object() {
            Map<String, Object> m = members(true);
            ws();
            if (i != s.length()) throw new IllegalArgumentException("trailing data");
            return m;
        }

        private Map<String, Object> members(boolean nested) {
            Map<String, Object> m = new java.util.HashMap<>();
            expect('{');
            if (peek() != '}') {
                do {
                    String k = string();
                    expect(':');
                    char c = peek();
                    m.put(k, c == '[' && nested ? array() : c == '{' && nested ? members(false) : string());
                } while (consume(','));
            }
            expect('}');
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
