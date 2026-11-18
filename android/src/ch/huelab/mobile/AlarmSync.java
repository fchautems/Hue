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
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.function.Consumer;
import org.json.JSONObject;

final class AlarmSync {
    private static final ExecutorService QUEUE = Executors.newSingleThreadExecutor();
    private static final String DIAGNOSTICS_KEY = "alarm-diagnostic-log";

    private AlarmSync() {}

    static SharedPreferences preferences(Context context) {
        return context.getSharedPreferences("MainActivity", Context.MODE_PRIVATE);
    }

    static synchronized void logEvent(Context context, String message) {
        String existing = preferences(context).getString(DIAGNOSTICS_KEY, "");
        String stamp = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.ROOT)
                .format(new Date());
        String updated = existing + stamp + " | " + message + "\n";
        if (updated.length() > 10000) updated = updated.substring(updated.length() - 8000);
        preferences(context).edit().putString(DIAGNOSTICS_KEY, updated).apply();
    }

    static synchronized String diagnosticLog(Context context) {
        String history = preferences(context).getString(DIAGNOSTICS_KEY, "");
        return history.isEmpty() ? "Aucun événement enregistré." : history;
    }

    static Future<?> request(Context context, Consumer<Boolean> complete) {
        Context app = context.getApplicationContext();
        return QUEUE.submit(() -> {
            logEvent(app, "Appui sur Synchroniser : début");
            boolean succeeded = false;
            try {
                sync(app);
                succeeded = true;
            } catch (Exception failure) {
                logEvent(app, "Échec de synchronisation : " + failure.getClass().getSimpleName());
                android.util.Log.d("HueDawn", "Synchronisation indisponible", failure);
            } finally {
                logEvent(app, succeeded ? "Synchronisation confirmée par le Raspberry" : "Synchronisation non confirmée");
                complete.accept(succeeded);
            }
        });
    }

    private static void sync(Context context) throws Exception {
        SharedPreferences preferences = preferences(context);
        String server = LocalServer.normalize(preferences.getString("server", MainActivity.DEFAULT_SERVER));
        if (server == null) throw new IOException("Adresse serveur invalide");
        JSONObject config = send(server + "/api/dawn", null);
        // No background polling: only an explicit UI tap reaches this method.
        if (!config.getBoolean("enabled")) throw new IOException("Réveil désactivé");
        long observed = System.currentTimeMillis();
        logEvent(context, "Lecture ponctuelle de la prochaine alarme Android");
        AlarmManager.AlarmClockInfo alarm = context.getSystemService(AlarmManager.class).getNextAlarmClock();
        logEvent(context, alarm == null ? "Aucune alarme Android à venir" :
                "Prochaine alarme détectée : " + new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.ROOT)
                        .format(new Date(alarm.getTriggerTime())));
        JSONObject report = new JSONObject();
        report.put("observed_at", observed);
        report.put("alarm_at", alarm == null ? JSONObject.NULL : alarm.getTriggerTime());
        if (!server.equals(LocalServer.normalize(preferences.getString("server", MainActivity.DEFAULT_SERVER)))) {
            throw new IOException("Adresse serveur modifiée");
        }
        send(server + "/api/dawn/alarm", report);
    }

    private static JSONObject send(String address, JSONObject payload) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(address).openConnection(Proxy.NO_PROXY);
        try {
            connection.setConnectTimeout(1600);
            connection.setReadTimeout(1600);
            connection.setInstanceFollowRedirects(false);
            connection.setUseCaches(false);
            connection.setRequestProperty("Accept", "application/json");
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
            if (connection.getResponseCode() != 200) throw new IOException("HTTP " + connection.getResponseCode());
            try (InputStream input = connection.getInputStream();
                 ByteArrayOutputStream buffer = new ByteArrayOutputStream()) {
                byte[] chunk = new byte[1024];
                int read;
                while ((read = input.read(chunk)) != -1) {
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
