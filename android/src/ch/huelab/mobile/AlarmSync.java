package ch.huelab.mobile;

import android.app.AlarmManager;
import android.content.Context;
import android.content.SharedPreferences;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.Proxy;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.function.Consumer;
import org.json.JSONObject;

final class AlarmSync {
    private static boolean running;
    private static long nextTapNanos;
    private static final String DIAGNOSTICS_KEY = "alarm-diagnostic-log";

    private AlarmSync() {}

    static SharedPreferences preferences(Context context) {
        return context.getSharedPreferences("MainActivity", Context.MODE_PRIVATE);
    }

    static synchronized void logEvent(Context context, String message) {
        String existing = preferences(context).getString(DIAGNOSTICS_KEY, "");
        String stamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS Z", Locale.ROOT)
                .format(new Date());
        String updated = existing + stamp + " | " + message + "\n";
        if (updated.length() > 10000) {
            int cut = updated.indexOf('\n', updated.length() - 8000);
            updated = updated.substring(cut + 1);
        }
        preferences(context).edit().putString(DIAGNOSTICS_KEY, updated).apply();
    }

    static synchronized String diagnosticLog(Context context) {
        String history = preferences(context).getString(DIAGNOSTICS_KEY, "");
        return history.isEmpty() ? "Aucun événement enregistré." : history;
    }

    static synchronized boolean request(Context context, Consumer<Boolean> complete) {
        Context app = context.getApplicationContext();
        if (running || System.nanoTime() < nextTapNanos) {
            logEvent(app, "Appui ignoré : synchronisation en cours ou double appui");
            return false;
        }
        running = true;
        logEvent(app, "Appui sur Synchroniser : début");
        // A finite worker per accepted tap. No queue, idle executor, timer or retry.
        Thread worker = new Thread(() -> {
            boolean succeeded = false;
            try {
                sync(app);
                succeeded = true;
            } catch (Exception failure) {
                String detail = String.valueOf(failure.getMessage()).replace('\n', ' ').replace('\r', ' ');
                if (detail.length() > 200) detail = detail.substring(0, 200);
                logEvent(app, "Échec de synchronisation : " + failure.getClass().getSimpleName() + " : " + detail);
            } finally {
                logEvent(app, succeeded ? "Synchronisation confirmée par le Raspberry" :
                        "Synchronisation non confirmée ; aucun nouvel essai automatique");
                synchronized (AlarmSync.class) {
                    running = false;
                    nextTapNanos = System.nanoTime() + 1_000_000_000L;
                }
                complete.accept(succeeded);
            }
        }, "HueManualAlarmSync");
        try {
            worker.start();
        } catch (RuntimeException failure) {
            running = false;
            logEvent(app, "Impossible de démarrer la synchronisation manuelle");
            complete.accept(false);
        }
        return true;
    }

    private static void sync(Context context) throws Exception {
        SharedPreferences preferences = preferences(context);
        String server = LocalServer.normalize(preferences.getString("server", MainActivity.DEFAULT_SERVER));
        if (server == null) throw new IOException("Adresse serveur invalide");
        JSONObject config = send(context, server + "/api/dawn", null);
        // No background polling: only an explicit UI tap reaches this method.
        if (!config.getBoolean("enabled")) throw new IOException("Réveil désactivé");
        long observed = System.currentTimeMillis();
        logEvent(context, "Lecture ponctuelle de la prochaine alarme Android");
        AlarmManager.AlarmClockInfo alarm = context.getSystemService(AlarmManager.class).getNextAlarmClock();
        logEvent(context, alarm == null ? "Aucune alarme Android à venir" :
                "Prochaine alarme détectée : " + new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS Z", Locale.ROOT)
                        .format(new Date(alarm.getTriggerTime())));
        JSONObject report = new JSONObject();
        report.put("observed_at", observed);
        report.put("alarm_at", alarm == null ? JSONObject.NULL : alarm.getTriggerTime());
        if (!server.equals(LocalServer.normalize(preferences.getString("server", MainActivity.DEFAULT_SERVER)))) {
            throw new IOException("Adresse serveur modifiée");
        }
        logEvent(context, "Envoi au Raspberry : observed_at=" + observed + ", alarm_at=" + report.get("alarm_at"));
        JSONObject reply = send(context, server + "/api/dawn/alarm", report);
        logEvent(context, "État retourné : enabled=" + reply.getBoolean("enabled")
                + ", observed_at=" + reply.getLong("observed_at") + ", alarm_at=" + reply.get("alarm_at"));
        boolean sameAlarm = alarm == null ? reply.isNull("alarm_at") :
                !reply.isNull("alarm_at") && reply.getLong("alarm_at") == alarm.getTriggerTime();
        if (!reply.getBoolean("enabled") || reply.getLong("observed_at") != observed || !sameAlarm) {
            throw new IOException("Le Raspberry n’a pas conservé exactement le réveil envoyé");
        }
    }

    private static JSONObject send(Context context, String address, JSONObject payload) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(address).openConnection(Proxy.NO_PROXY);
        try {
            long deadline = System.nanoTime() + 5_000_000_000L;
            connection.setConnectTimeout(1600);
            connection.setReadTimeout(1600);
            connection.setInstanceFollowRedirects(false);
            connection.setUseCaches(false);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("Connection", "close");
            if (payload != null) {
                byte[] data = payload.toString().getBytes(StandardCharsets.UTF_8);
                connection.setRequestMethod("PUT");
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json");
                connection.setFixedLengthStreamingMode(data.length);
                try (OutputStream output = connection.getOutputStream()) {
                    output.write(data);
                }
            }
            int status = connection.getResponseCode();
            logEvent(context, (payload == null ? "Lecture configuration" : "Réponse à l’envoi") + " : HTTP " + status);
            if (status != 200) throw new IOException("HTTP " + status);
            try (InputStream input = connection.getInputStream();
                 ByteArrayOutputStream buffer = new ByteArrayOutputStream()) {
                byte[] chunk = new byte[1024];
                int read;
                while (true) {
                    long remaining = (deadline - System.nanoTime()) / 1_000_000L;
                    if (remaining <= 0) throw new java.net.SocketTimeoutException("Délai total de réponse dépassé");
                    connection.setReadTimeout((int) Math.min(1600, remaining));
                    read = input.read(chunk);
                    if (read == -1) break;
                    if (buffer.size() + read > 8192) throw new IOException("Réponse trop longue");
                    buffer.write(chunk, 0, read);
                }
                JSONObject body = new JSONObject(buffer.toString("UTF-8"));
                if (!body.getBoolean("ok")) throw new IOException("Réponse Hue Lab invalide");
                return body.getJSONObject("data");
            }
        } finally {
            connection.disconnect();
        }
    }
}
