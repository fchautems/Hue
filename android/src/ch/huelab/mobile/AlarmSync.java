package ch.huelab.mobile;

import android.app.AlarmManager;
import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.content.ComponentName;
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
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.function.Consumer;
import org.json.JSONObject;

final class AlarmSync {
    private static final int JOB_ID = 271;
    private static final String ENABLED = "dawn-enabled";
    private static final ExecutorService QUEUE = Executors.newSingleThreadExecutor();

    private AlarmSync() {}

    static SharedPreferences preferences(Context context) {
        return context.getSharedPreferences("MainActivity", Context.MODE_PRIVATE);
    }

    static boolean enabled(Context context) {
        return preferences(context).getBoolean(ENABLED, false);
    }

    static Future<?> request(Context context, Consumer<Boolean> complete) {
        Context app = context.getApplicationContext();
        return QUEUE.submit(() -> {
            boolean succeeded = false;
            try {
                sync(app);
                succeeded = true;
            } catch (Exception failure) {
                android.util.Log.d("HueDawn", "Synchronisation indisponible", failure);
            } finally {
                complete.accept(succeeded);
            }
        });
    }

    private static void sync(Context context) throws Exception {
        SharedPreferences preferences = preferences(context);
        String server = LocalServer.normalize(preferences.getString("server", MainActivity.DEFAULT_SERVER));
        if (server == null) return;
        JSONObject config = send(server + "/api/dawn", null);
        boolean active = config.getBoolean("enabled");
        preferences.edit().putBoolean(ENABLED, active).apply();
        JobScheduler jobs = context.getSystemService(JobScheduler.class);
        if (!active) {
            jobs.cancel(JOB_ID);
            return;
        }
        if (jobs.getPendingJob(JOB_ID) == null) {
            jobs.schedule(new JobInfo.Builder(JOB_ID, new ComponentName(context, AlarmSyncJob.class))
                    .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                    .setPeriodic(15 * 60 * 1000L)
                    .setPersisted(true)
                    .build());
        }
        long observed = System.currentTimeMillis();
        AlarmManager.AlarmClockInfo alarm = context.getSystemService(AlarmManager.class).getNextAlarmClock();
        JSONObject report = new JSONObject();
        report.put("observed_at", observed);
        report.put("alarm_at", alarm == null ? JSONObject.NULL : alarm.getTriggerTime());
        if (server.equals(LocalServer.normalize(preferences.getString("server", MainActivity.DEFAULT_SERVER)))) {
            send(server + "/api/dawn/alarm", report);
        }
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
