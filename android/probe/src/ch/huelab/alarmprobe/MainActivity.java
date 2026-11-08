package ch.huelab.alarmprobe;

import android.app.Activity;
import android.app.AlarmManager;
import android.app.job.JobInfo;
import android.app.job.JobScheduler;
import android.content.BroadcastReceiver;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

public final class MainActivity extends Activity {
    private static final int JOB_ID = 23081;
    private TextView output;
    private boolean receiverActive = false;
    private final BroadcastReceiver liveReceiver = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            Probe.record(context, "diffusion dynamique (app visible)");
            redraw();
        }
    };

    private Button button(LinearLayout panel, String title, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(title);
        panel.addView(button);
        button.setOnClickListener(listener);
        return button;
    }

    private JobScheduler scheduler() {
        return (JobScheduler) getSystemService(Context.JOB_SCHEDULER_SERVICE);
    }

    private static final int NOTIFICATION_PERMISSION_REQUEST = 1001;

    private void startMinuteTest() {
        // L'ancien contrôle 15 minutes serait trompeur dans ce test.
        scheduler().cancel(JOB_ID);
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                    != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{android.Manifest.permission.POST_NOTIFICATIONS},
                    NOTIFICATION_PERMISSION_REQUEST);
            return;
        }
        try {
            startForegroundService(new Intent(this, MinuteProbeService.class));
            Probe.record(this, "demande de démarrage du test 1 min");
        } catch (Exception e) {
            Probe.record(this, "ERREUR lancement du test 1 min : " + e.getClass().getSimpleName());
        }
        redraw();
    }

    private void stopMinuteTest() {
        stopService(new Intent(this, MinuteProbeService.class));
        Probe.record(this, "bouton arrêt test 1 min");
        redraw();
    }

    @Override public void onRequestPermissionsResult(int requestCode,
            String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == NOTIFICATION_PERMISSION_REQUEST) {
            if (grantResults.length > 0 &&
                    grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                startMinuteTest();
            } else {
                Probe.record(this, "permission notifications refusée : test non démarré");
                redraw();
            }
        }
    }

    private void redraw() {
        if (output == null) return;
        boolean active = MinuteProbeService.running;
        output.setText("Test chaque minute : " + (active ? "ACTIF (maximum 45 min)" : "arrêté")
                + "\n\n" + Probe.report(this));
    }

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        ScrollView scroll = new ScrollView(this);
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        panel.setPadding(pad, pad, pad, pad);
        scroll.addView(panel);
        TextView title = new TextView(this);
        title.setText("Hue Lab – test du prochain réveil");
        title.setTextSize(22f);
        panel.addView(title);
        TextView instructions = new TextView(this);
        instructions.setText("APK indépendante, aucune commande Hue ni connexion réseau. "
                + "Le bouton démarre un service au premier plan : lecture ~chaque minute "
                + "pendant 45 minutes maximum, même après swipe ou écran éteint. "
                + "Une notification permet de l'arrêter. "
                + "Ce test garde le processeur actif et utilise davantage la batterie. "
                + "Ne pas utiliser Forcer l'arrêt pour le test normal.");
        instructions.setTextSize(15f);
        panel.addView(instructions);
        button(panel, "Lire le prochain réveil", v -> {
            Probe.record(this, "bouton manuel");
            redraw();
        });
        button(panel, "Démarrer test 1 min (45 min)", v -> startMinuteTest());
        button(panel, "Arrêter test 1 min", v -> stopMinuteTest());
        button(panel, "Copier le journal", v -> {
            ClipboardManager cb = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            cb.setPrimaryClip(ClipData.newPlainText("Test réveil Hue", Probe.report(this)));
        });
        button(panel, "Effacer le journal", v -> {
            Probe.clear(this);
            redraw();
        });
        output = new TextView(this);
        output.setTextIsSelectable(true);
        output.setTextSize(14f);
        panel.addView(output);
        setContentView(scroll);
        Probe.record(this, "ouverture de l'application");
        redraw();
    }

    @Override protected void onStart() {
        super.onStart();
        IntentFilter filter = new IntentFilter(AlarmManager.ACTION_NEXT_ALARM_CLOCK_CHANGED);
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(liveReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(liveReceiver, filter);
        }
        receiverActive = true;
        redraw();
    }

    @Override protected void onStop() {
        if (receiverActive) {
            unregisterReceiver(liveReceiver);
            receiverActive = false;
        }
        super.onStop();
    }

    @Override protected void onResume() {
        super.onResume();
        redraw();
    }
}
