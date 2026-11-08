package ch.huelab.alarmprobe;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.os.SystemClock;

public final class MinuteProbeService extends Service {
    static final String ACTION_STOP = "ch.huelab.alarmprobe.STOP_MINUTE_TEST";
    static final long PERIOD_MS = 60_000L;
    static final long DURATION_MS = 45L * 60L * 1000L;
    private static final int NOTIFICATION_ID = 10515;
    private static final String CHANNEL = "hue_alarm_test_minute";
    private final Handler handler = new Handler(Looper.getMainLooper());
    private PowerManager.WakeLock wakeLock;
    private long endElapsed;
    private boolean started;
    static volatile boolean running;

    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (!started) return;
            if (SystemClock.elapsedRealtime() >= endElapsed) {
                Probe.record(MinuteProbeService.this, "fin automatique test 1 min (45 min)");
                stopSelf();
                return;
            }
            Probe.record(MinuteProbeService.this, "vérification 1 min (service)");
            handler.postDelayed(this, PERIOD_MS);
        }
    };

    @Override public void onCreate() {
        super.onCreate();
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel channel = new NotificationChannel(CHANNEL,
                    "Hue – vérification réveil chaque minute", NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("Test temporaire, actif pendant 45 minutes maximum");
            nm.createNotificationChannel(channel);
        }
    }

    private Notification notification() {
        Intent show = new Intent(this, MainActivity.class);
        PendingIntent open = PendingIntent.getActivity(this, 0, show,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Intent stop = new Intent(this, MinuteProbeService.class).setAction(ACTION_STOP);
        PendingIntent stopAction = PendingIntent.getService(this, 1, stop,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
                .setContentTitle("Hue – test du réveil (1 min)")
                .setContentText("Test en cours (45 min max). Appuyer pour le journal.")
                .setContentIntent(open)
                .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Arrêter", stopAction)
                .setOngoing(true)
                .setOnlyAlertOnce(true)
                .build();
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            Probe.record(this, "arrêt demandé test 1 min");
            stopSelf();
            return START_NOT_STICKY;
        }
        if (started) return START_NOT_STICKY;
        try {
            if (Build.VERSION.SDK_INT >= 34) {
                startForeground(NOTIFICATION_ID, notification(),
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
            } else {
                startForeground(NOTIFICATION_ID, notification());
            }
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "HueAlarmProbe:minuteTest");
            wakeLock.setReferenceCounted(false);
            // Le test est volontairement limité pour ne pas garder le CPU éveillé toute la nuit.
            wakeLock.acquire(DURATION_MS + 60_000L);
            started = true;
            running = true;
            endElapsed = SystemClock.elapsedRealtime() + DURATION_MS;
            Probe.record(this, "test 1 min démarré (45 min max, écran éteint)");
            handler.post(tick);
        } catch (Exception e) {
            Probe.record(this, "ERREUR service 1 min : " + e.getClass().getSimpleName());
            stopSelf();
        }
        return START_NOT_STICKY;
    }

    @Override public void onTaskRemoved(Intent rootIntent) {
        Probe.record(this, "swipe applications récentes (service encore actif)");
        super.onTaskRemoved(rootIntent);
    }

    @Override public void onDestroy() {
        started = false;
        running = false;
        handler.removeCallbacks(tick);
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        Probe.record(this, "service 1 min arrêté");
        super.onDestroy();
    }

    @Override public IBinder onBind(Intent intent) { return null; }
}
