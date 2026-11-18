package ch.huelab.mobile;

import android.content.Context;
import java.io.*;
import java.lang.reflect.Field;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import org.json.JSONObject;

/** Executes the actual AlarmSync with in-memory Android services and fake HTTP. */
public final class ManualAlarmTest {
    static Context app;
    static int gets, puts, status;
    static String mode;
    static JSONObject report;
    static CountDownLatch entered, release;
    static int passed;
    static void check(boolean condition, String reason) {
        if (!condition) throw new AssertionError(reason);
    }
    static void reset(String scenario) throws Exception {
        app = new Context(); gets = puts = 0; status = 200; report = null; mode = scenario;
        entered = new CountDownLatch(1); release = new CountDownLatch(1);
        Field gate = AlarmSync.class.getDeclaredField("nextTapNanos");
        gate.setAccessible(true); gate.setLong(null, 0);
    }
    static boolean request() throws Exception {
        CountDownLatch done = new CountDownLatch(1);
        AtomicReference<Boolean> result = new AtomicReference<>();
        check(AlarmSync.request(app, success -> { result.set(success); done.countDown(); }), "tap accepted");
        check(done.await(8, TimeUnit.SECONDS), "finite operation");
        return result.get();
    }
    static void pass(String name) { passed++; System.out.println("PASS " + name); }
    static class FakeConnection extends HttpURLConnection {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        FakeConnection(URL url) { super(url); }
        public void connect() {}
        public void disconnect() {}
        public boolean usingProxy() { return false; }
        public OutputStream getOutputStream() { return output; }
        public int getResponseCode() throws IOException {
            boolean put = "PUT".equals(getRequestMethod());
            if (put) { puts++; report = new JSONObject(new String(output.toByteArray(), StandardCharsets.UTF_8)); }
            else gets++;
            check(getConnectTimeout() == 1600 && getReadTimeout() == 1600, "network timeouts");
            check(!getInstanceFollowRedirects() && !getUseCaches(), "no redirects or caching");
            check("close".equals(getRequestProperty("Connection")), "no pooled connection");
            if (mode.equals("blocked")) {
                entered.countDown();
                try { check(release.await(3, TimeUnit.SECONDS), "release worker"); }
                catch (InterruptedException e) { throw new IOException(e); }
            }
            if (mode.equals("wifi-off")) throw new ConnectException("Wi-Fi unavailable");
            if (mode.equals("timeout") || (put && mode.equals("lost-ack"))) throw new SocketTimeoutException("timeout");
            if (!put && mode.equals("changed-server")) AlarmSync.preferences(app).edit().putString("server", "10.0.0.13:8765").apply();
            return status;
        }
        public InputStream getInputStream() {
            JSONObject data = new JSONObject().put("enabled", !mode.equals("disabled"));
            if ("PUT".equals(getRequestMethod())) {
                data.put("enabled", !mode.equals("disabled-during-put"));
                data.put("observed_at", report.getLong("observed_at") + (mode.equals("stale") ? 1 : 0));
                data.put("alarm_at", mode.equals("mismatch") ? 42L : report.get("alarm_at"));
            }
            String response = new JSONObject().put("ok", !mode.equals("ok-false")).put("data", data).toString();
            if (mode.equals("malformed")) response = "not json";
            if (mode.equals("oversized")) response = new String(new char[9000]).replace('\0', 'x');
            return new ByteArrayInputStream(response.getBytes(StandardCharsets.UTF_8));
        }
    }
    public static void main(String[] args) throws Exception {
        URL.setURLStreamHandlerFactory(protocol -> "http".equals(protocol) ? new URLStreamHandler() {
            protected URLConnection openConnection(URL u) { return new FakeConnection(u); }
            protected URLConnection openConnection(URL u, Proxy p) { return openConnection(u); }
        } : null);
        reset("normal");
        AlarmSync.logEvent(app, "Ouverture de Hue Lab : aucune recherche automatique");
        AlarmSync.diagnosticLog(app);
        check(app.alarms.reads == 0 && gets == 0 && puts == 0, "no automatic alarm or HTTP read");
        pass("opening/log access never reads alarms");
        check(request(), "success");
        check(app.alarms.reads == 1 && gets == 1 && puts == 1, "one GET, one alarm read, one PUT");
        String log = AlarmSync.diagnosticLog(app);
        check(log.contains("Envoi au Raspberry") && log.contains("État retourné") && log.contains("HTTP 200"), "useful diagnostic");
        check(!AlarmSync.request(app, ignored -> { throw new AssertionError("duplicate callback"); }), "fast completed double tap ignored");
        check(puts == 1, "no duplicate PUT");
        pass("single tap, exact acknowledgment and fast double tap");

        reset("blocked");
        CountDownLatch done = new CountDownLatch(1);
        AlarmSync.request(app, success -> done.countDown());
        check(entered.await(2, TimeUnit.SECONDS), "first request started");
        for (int i = 0; i < 25; i++) check(!AlarmSync.request(app, ignored -> {}), "no queued request");
        release.countDown(); check(done.await(5, TimeUnit.SECONDS), "first request done");
        check(app.alarms.reads == 1 && gets == 1 && puts == 1, "25 duplicates produce no extra work");
        pass("concurrent taps rejected without a queue");

        reset("disabled"); check(!request(), "disabled fails");
        check(app.alarms.reads == 0 && puts == 0, "disabled never reads alarm");
        pass("disabled dawn");
        reset("normal"); app.alarms.alarm = null;
        check(request() && report.isNull("alarm_at"), "absence explicitly clears server alarm");
        pass("no Android alarm");
        for (String scenario : new String[]{"wifi-off", "timeout", "malformed", "oversized", "ok-false"}) {
            reset(scenario); check(!request(), scenario + " fails");
            check(app.alarms.reads == 0 && gets == 1 && puts == 0, "no alarm read/retry after failed GET");
            pass(scenario);
        }
        for (int http : new int[]{302, 400, 500}) {
            reset("normal"); status = http; check(!request(), "HTTP failure");
            check(gets == 1 && puts == 0 && app.alarms.reads == 0, "no followup");
            pass("HTTP " + http);
        }
        for (String scenario : new String[]{"stale", "mismatch", "disabled-during-put", "lost-ack"}) {
            reset(scenario); check(!request(), "no false success: " + scenario);
            check(app.alarms.reads == 1 && gets == 1 && puts == 1, "no retry of uncertain PUT");
            pass(scenario);
        }
        reset("changed-server"); check(!request(), "changed server rejected");
        check(puts == 0, "never sends to different server"); pass("address changed during request");
        reset("normal");
        for (int i = 0; i < 500; i++) AlarmSync.logEvent(app, "Diagnostic borné de test numéro " + i);
        check(AlarmSync.diagnosticLog(app).length() <= 10000, "bounded local log");
        Context separate = new Context();
        check(!AlarmSync.diagnosticLog(separate).contains("numéro"), "separate app data");
        pass("bounded local log and independent contexts");
        System.out.println(passed + " JVM scenarios passed (simulated Android/HTTP; not a Pixel test).");
    }
}
