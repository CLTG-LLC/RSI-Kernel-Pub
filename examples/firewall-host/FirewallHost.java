// Generic offline JDK evaluator, using examples/java-host and design.md §4.1.
// private-API reflection, offline copy only: the loader's own snapshot-test
// precedent (PolicySnapshotRuntimeFirewallViewTest.java:478–483) is
// getDeclaredMethod("load", InputStream.class, List.class), then
// setAccessible(true). No registry, runtime pipeline or champion is changed.

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.net.InetSocketAddress;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributeView;
import java.nio.file.attribute.FileTime;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.attribute.PosixFileAttributeView;
import java.nio.file.attribute.PosixFilePermission;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.function.Predicate;
import java.util.regex.PatternSyntaxException;

public final class FirewallHost {
    private final Properties config;
    private final Path configDir;
    private final ClassLoader classes;
    private final Map<String, Case> cases;
    private final Map<String, Case> guards;
    private final byte[] champion;
    private final String componentName;
    private final List<String> applied = new ArrayList<>();
    private final List<String> guardCommand;
    private final Path guardDirectory;
    private final Path guardResource;
    private final long guardTimeoutNanos;
    private final Map<String, String> guardResults = new java.util.HashMap<>();

    private record Case(String text, boolean mustMatch) { }
    private static final class GuardUnavailable extends Exception { }
    private static final class Ineligible extends Exception {
        final String reason;
        Ineligible(String reason) { this.reason = reason; }
    }

    private FirewallHost(Path configPath) throws Exception {
        configDir = configPath.toAbsolutePath().getParent();
        config = new Properties();
        try (var reader = Files.newBufferedReader(configPath, StandardCharsets.UTF_8)) {
            config.load(reader);
        }
        List<URL> urls = new ArrayList<>();
        for (String entry : required("classpath").split(java.io.File.pathSeparator)) {
            urls.add(configDir.resolve(entry).toUri().toURL());
        }
        classes = new URLClassLoader(urls.toArray(URL[]::new), FirewallHost.class.getClassLoader());
        required("loader_class");
        required("matcher_factory");
        required("evidence_path");
        champion = Files.readAllBytes(path("champion_path"));
        componentName = config.getProperty("component_name", "rules.yml");
        if (componentName.isBlank()) throw new IllegalArgumentException("empty component name");
        cases = readCases(path("cases_path"));
        guards = readCases(path("guard_cases_path"));
        if (config.containsKey("guard_command")) {
            Object command = new Json("{\"argv\":" + required("guard_command") + "}").object().get("argv");
            if (!(command instanceof List<?> argv) || argv.isEmpty()
                    || string(argv.get(0)).isBlank()
                    || argv.stream().anyMatch(value -> string(value).indexOf('\0') >= 0)) {
                throw new IllegalArgumentException("guard_command must be a nonempty argv list");
            }
            guardCommand = argv.stream().map(FirewallHost::string).toList();
            guardDirectory = path("guard_working_directory").toRealPath();
            guardResource = path("guard_resource_path").toRealPath();
            if (!Files.isDirectory(guardDirectory) || !Files.isRegularFile(guardResource)
                    || !guardResource.startsWith(guardDirectory)) {
                throw new IllegalArgumentException("guard resource must be inside the offline working directory");
            }
            double seconds = Double.parseDouble(required("guard_timeout_seconds"));
            double nanos = seconds * TimeUnit.SECONDS.toNanos(1);
            if (!Double.isFinite(nanos) || nanos < 1 || nanos >= Long.MAX_VALUE) {
                throw new IllegalArgumentException("guard_timeout_seconds must be positive and representable");
            }
            guardTimeoutNanos = (long) nanos;
        } else {
            guardCommand = List.of();
            guardDirectory = null;
            guardResource = null;
            guardTimeoutNanos = 0;
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 1 || args.length > 2) {
            throw new IllegalArgumentException("usage: FirewallHost config.properties [port]");
        }
        FirewallHost host = new FirewallHost(Path.of(args[0]));
        int port = args.length == 2 ? Integer.parseInt(args[1]) : 0;
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        // ponytail: single JDK dispatcher serializes evaluations and JSONL appends;
        // add a bounded executor plus explicit log locking only if throughput matters.
        server.createContext("/artifact", ex -> host.artifact(ex));
        server.createContext("/evaluate", ex -> host.evaluate(ex));
        server.createContext("/apply", ex -> host.apply(ex));
        server.start();
        System.out.println("LISTENING " + server.getAddress().getPort());
        System.out.flush();
    }

    private String required(String key) {
        String value = config.getProperty(key);
        if (value == null || value.isBlank()) throw new IllegalArgumentException("missing " + key);
        return value;
    }

    private Path path(String key) { return configDir.resolve(required(key)); }

    private static Map<String, Case> readCases(Path path) throws IOException {
        Map<String, Object> raw = new Json(Files.readString(path, StandardCharsets.UTF_8)).object();
        Map<String, Case> result = new java.util.LinkedHashMap<>();
        for (var entry : raw.entrySet()) {
            if (!(entry.getValue() instanceof Map<?, ?> row)
                    || !row.keySet().equals(java.util.Set.of("text", "expectation"))
                    || !(row.get("text") instanceof String text)
                    || !(row.get("expectation") instanceof String expectation)
                    || !(expectation.equals("must_match") || expectation.equals("must_not_match"))) {
                throw new IllegalArgumentException("invalid case");
            }
            result.put(entry.getKey(), new Case(text, expectation.equals("must_match")));
        }
        return java.util.Collections.unmodifiableMap(result);
    }

    private static boolean route(HttpExchange ex, String path, String method) throws IOException {
        if (!ex.getRequestURI().getPath().equals(path)) {
            send(ex, 404, "{\"error\":\"not found\"}");
            return false;
        }
        if (!ex.getRequestMethod().equals(method)) {
            send(ex, 405, "{\"error\":\"method not allowed\"}");
            return false;
        }
        return true;
    }

    private void artifact(HttpExchange ex) throws IOException {
        if (!route(ex, "/artifact", "GET")) return;
        send(ex, 200, "{\"media_type\":\"application/yaml\",\"components\":{" + quote(componentName)
                + ":" + quote(Base64.getEncoder().encodeToString(champion)) + "}}");
    }

    private void apply(HttpExchange ex) throws IOException {
        if (!route(ex, "/apply", "POST")) return;
        try {
            String id = string(request(ex).get("candidate_id"));
            if (!id.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("invalid content id");
            applied.add(id); // Record-only, as in examples/java-host: no activation or file write.
            send(ex, 200, "{\"applied\":[" + String.join(",", applied.stream().map(FirewallHost::quote).toList()) + "]}");
        } catch (RuntimeException e) {
            send(ex, 400, "{\"error\":\"bad request\"}");
        }
    }

    private void evaluate(HttpExchange ex) throws IOException {
        String contentId = "";
        String status = "operational";
        String reason = "IllegalArgumentException";
        String guardStatus = "not_run";
        int code = 400;
        String body;
        try {
            if (!ex.getRequestURI().getPath().equals("/evaluate")) {
                code = 404;
                throw new IllegalArgumentException("path");
            }
            if (!ex.getRequestMethod().equals("POST")) {
                code = 405;
                throw new IllegalArgumentException("method");
            }
            Map<String, Object> req = request(ex);
            Map<String, byte[]> components = components(req.get("components"));
            contentId = contentId(components);
            if (!contentId.equals(string(req.get("candidate_id")))
                    || !components.keySet().equals(java.util.Set.of(componentName))) {
                throw new IllegalArgumentException("candidate bytes mismatch");
            }
            List<String> items = items(req.get("item_ids"));
            code = 500; // From here failures are operational, except the explicit eligibility stages.
            if (!guardCommand.isEmpty()) {
                guardStatus = guard(contentId, components.get(componentName));
                if (guardStatus.equals("guard_failed")) throw new Ineligible("guard_failed");
                if (guardStatus.equals("guard_unavailable")) throw new GuardUnavailable();
            }
            List<Predicate<String>> predicates = load(components.get(componentName));
            for (Case guard : guards.values()) {
                if (!correct(predicates, guard)) throw new Ineligible("GoldenGuardFailure");
            }
            body = results(predicates, items);
            code = 200;
            status = "ok";
            reason = "none";
        } catch (Ineligible e) {
            code = 422;
            status = "ineligible";
            reason = e.reason;
            body = error(status, reason);
        } catch (GuardUnavailable e) {
            guardStatus = "guard_unavailable";
            reason = "guard_unavailable";
            body = error(status, reason);
        } catch (Exception e) {
            reason = reasonClass(e);
            body = error(status, reason);
        }
        try {
            evidence(contentId, status, reason, guardStatus);
        } catch (IOException e) {
            // No successful response without durable evidence. A broken evidence
            // destination cannot itself receive a JSONL line; repair it before rerun.
            code = 500;
            body = error("operational", "EvidenceWriteFailure");
        }
        send(ex, code, body);
    }

    private String guard(String id, byte[] candidate) {
        String cached = guardResults.get(id);
        if (cached != null) return cached;
        String result;
        try {
            // Capture source metadata before installation; restoration never reads
            // the destination, which the guard may delete or alter.
            BasicFileAttributes attributes = Files.readAttributes(guardResource, BasicFileAttributes.class);
            PosixFileAttributeView posix = Files.getFileAttributeView(guardResource, PosixFileAttributeView.class);
            java.util.Set<PosixFilePermission> permissions = posix == null ? null : posix.readAttributes().permissions();
            try {
                atomicReplace(guardResource, candidate);
                result = runGuard();
            } finally {
                Path restore = replacementFile(guardResource, champion, attributes, permissions);
                try {
                    Files.move(restore, guardResource, StandardCopyOption.ATOMIC_MOVE,
                            StandardCopyOption.REPLACE_EXISTING);
                } finally {
                    Files.deleteIfExists(restore);
                }
            }
        } catch (IOException e) {
            result = "guard_unavailable";
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            result = "guard_unavailable";
        }
        guardResults.put(id, result);
        return result;
    }

    private String runGuard() throws IOException, InterruptedException {
        Process process = new ProcessBuilder(guardCommand).directory(guardDirectory.toFile())
                .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                .redirectError(ProcessBuilder.Redirect.DISCARD).start();
        try {
            process.getOutputStream().close();
            if (!process.waitFor(guardTimeoutNanos, TimeUnit.NANOSECONDS)) return "guard_unavailable";
            return process.exitValue() == 0 ? "passed" : "guard_failed";
        } finally {
            if (process.isAlive()) {
                // Capture the tree while the root still owns its descendants.
                List<ProcessHandle> owned = new ArrayList<>(process.descendants().toList());
                owned.add(process.toHandle());
                owned.forEach(ProcessHandle::destroyForcibly);
                try {
                    CompletableFuture.allOf(owned.stream().map(ProcessHandle::onExit)
                            .toArray(CompletableFuture<?>[]::new))
                            .get(guardTimeoutNanos, TimeUnit.NANOSECONDS);
                } catch (ExecutionException | TimeoutException e) {
                    throw new IOException("guard termination unavailable", e);
                }
            }
        }
    }

    // Restoration keeps the original timestamps; candidate installation keeps the fresh
    // write time so timestamp-based build tools (e.g. GNU Make, incremental resource
    // copies) rebuild from the candidate rather than a stale champion copy.
    private static Path replacementFile(Path resource, byte[] bytes, BasicFileAttributes attributes,
                                        java.util.Set<PosixFilePermission> permissions) throws IOException {
        Path temp = Files.createTempFile(resource.getParent(), ".guard-", ".tmp");
        try {
            if (attributes == null) {
                Files.copy(resource, temp, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.COPY_ATTRIBUTES);
            }
            Files.write(temp, bytes);
            if (attributes != null) {
                if (permissions != null) Files.setPosixFilePermissions(temp, permissions);
                Files.getFileAttributeView(temp, BasicFileAttributeView.class).setTimes(
                        attributes.lastModifiedTime(), attributes.lastAccessTime(), attributes.creationTime());
            } else {
                Files.setLastModifiedTime(temp, FileTime.fromMillis(System.currentTimeMillis()));
            }
            return temp;
        } catch (IOException | RuntimeException e) {
            Files.deleteIfExists(temp);
            throw e;
        }
    }

    private static void atomicReplace(Path resource, byte[] bytes) throws IOException {
        Path temp = replacementFile(resource, bytes, null, null);
        try {
            Files.move(temp, resource, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } finally {
            Files.deleteIfExists(temp);
        }
    }

    private static Map<String, Object> request(HttpExchange ex) throws IOException {
        return new Json(new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8)).object();
    }

    private static String string(Object value) {
        if (!(value instanceof String text)) throw new IllegalArgumentException("expected string");
        return text;
    }

    private static Map<String, byte[]> components(Object raw) {
        if (!(raw instanceof Map<?, ?> values)) throw new IllegalArgumentException("expected components");
        Map<String, byte[]> decoded = new java.util.HashMap<>();
        values.forEach((key, value) -> decoded.put(string(key), Base64.getDecoder().decode(string(value))));
        return decoded;
    }

    private List<String> items(Object raw) {
        if (!(raw instanceof List<?> values)) throw new IllegalArgumentException("expected item ids");
        List<String> ids = values.stream().map(FirewallHost::string).toList();
        if (!cases.keySet().containsAll(ids)) throw new IllegalArgumentException("unknown item");
        return ids;
    }

    private List<Predicate<String>> load(byte[] candidate) throws Exception {
        String[] factory = required("matcher_factory").split("#", -1);
        if (factory.length != 2) throw new IllegalArgumentException("expected Class#method");
        Object matchers = Class.forName(factory[0], true, classes).getMethod(factory[1]).invoke(null);
        if (!(matchers instanceof List<?>)) throw new IllegalArgumentException("factory must return List");
        // private-API reflection, offline copy only. Invoke the existing loader
        // with the EXACT decoded component bytes, never a reserialized YAML document.
        Method loader = Class.forName(required("loader_class"), true, classes)
                .getDeclaredMethod("load", InputStream.class, List.class);
        loader.setAccessible(true);
        Object loaded;
        try {
            loaded = loader.invoke(null, new ByteArrayInputStream(candidate), matchers);
        } catch (InvocationTargetException e) {
            Throwable cause = e.getCause();
            if (cause instanceof IllegalStateException || cause instanceof PatternSyntaxException) {
                throw new Ineligible(cause.getClass().getSimpleName());
            }
            throw e;
        }
        if (!(loaded instanceof List<?> rules)) throw new IllegalStateException("loader must return List");
        List<Predicate<String>> predicates = new ArrayList<>();
        for (Object rule : rules) {
            Object matcher = rule.getClass().getMethod("matcher").invoke(rule);
            if (!(matcher instanceof Predicate<?>)) throw new IllegalStateException("rule must expose Predicate");
            @SuppressWarnings("unchecked")
            Predicate<String> predicate = (Predicate<String>) matcher;
            predicates.add(predicate);
        }
        return List.copyOf(predicates);
    }

    private static boolean correct(List<Predicate<String>> predicates, Case item) {
        return predicates.stream().anyMatch(p -> p.test(item.text())) == item.mustMatch();
    }

    private String results(List<Predicate<String>> predicates, List<String> items) {
        List<String> rows = new ArrayList<>();
        for (String id : items) {
            boolean pass = correct(predicates, cases.get(id));
            rows.add("{\"item_id\":" + quote(id) + ",\"score\":" + (pass ? "1" : "0")
                    + ",\"feedback\":" + quote(pass ? "correct" : "incorrect") + "}");
        }
        return "{\"results\":[" + String.join(",", rows) + "]}";
    }

    private void evidence(String id, String status, String reason, String guardStatus) throws IOException {
        String guardFields = guardCommand.isEmpty() ? "" : ",\"guard_status\":" + quote(guardStatus)
                + ",\"skipped_tests\":\"unknown\"";
        String line = "{\"content_id\":" + quote(id) + ",\"status\":" + quote(status)
                + ",\"reason_class\":" + quote(reason) + guardFields + "}\n";
        Files.writeString(path("evidence_path"), line, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    }

    private static String reasonClass(Exception e) {
        Throwable cause = e instanceof InvocationTargetException ? e.getCause() : e;
        return cause.getClass().getSimpleName();
    }

    private static String error(String status, String reason) {
        return "{\"error\":" + quote(status) + ",\"reason_class\":" + quote(reason) + "}";
    }

    // Ported unchanged from examples/java-host/EvaluatorHost.java and
    // src/rsi_kernel/candidate.py: sorted UTF-8 names and 8-byte BE lengths.
    static String contentId(Map<String, byte[]> components) {
        try {
            java.security.MessageDigest h = java.security.MessageDigest.getInstance("SHA-256");
            List<byte[]> names = new ArrayList<>();
            components.keySet().forEach(k -> names.add(k.getBytes(StandardCharsets.UTF_8)));
            names.sort(java.util.Arrays::compareUnsigned);
            for (byte[] name : names) {
                byte[] value = components.get(new String(name, StandardCharsets.UTF_8));
                for (byte[] part : new byte[][] {name, value}) {
                    h.update(java.nio.ByteBuffer.allocate(8).putLong(part.length).array());
                    h.update(part);
                }
            }
            return java.util.HexFormat.of().formatHex(h.digest());
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static void send(HttpExchange ex, int status, String body) throws IOException {
        byte[] data = body.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().set("Content-Type", "application/json");
        ex.sendResponseHeaders(status, data.length);
        try (var os = ex.getResponseBody()) { os.write(data); }
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

    // Reuse the Java host's fixed-shape parser (strings, string arrays, one
    // nested object). No dependency or generalized JSON framework is needed.
    // ponytail: trusted offline inputs, unbounded request bodies as in §4.1;
    // use a vetted bounded JSON transport before exposing this as a service.
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
            Map<String, Object> m = new java.util.LinkedHashMap<>();
            expect('{');
            if (peek() != '}') {
                do {
                    String k = string();
                    expect(':');
                    char c = peek();
                    if (m.containsKey(k)) throw new IllegalArgumentException("duplicate key");
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
                if (c < 0x20) throw new IllegalArgumentException("control character");
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

        private void ws() {
            while (i < s.length() && " \t\r\n".indexOf(s.charAt(i)) >= 0) i++;
        }
        private char peek() { ws(); return s.charAt(i); }
        private boolean consume(char c) { if (peek() == c) { i++; return true; } return false; }
        private void expect(char c) { if (!consume(c)) throw new IllegalArgumentException("expected " + c); }
    }
}
