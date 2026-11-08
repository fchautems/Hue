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

    private void startPolling() {
        JobInfo job = new JobInfo.Builder(JOB_ID,
                new ComponentName(this, AlarmPollJob.class))
                .setPeriodic(15L * 60L * 1000L).setPersisted(true).build();
        int code = scheduler().schedule(job);
        Probe.record(this, code == JobScheduler.RESULT_SUCCESS
                ? "surveillance périodique activée" : "ÉCHEC activation JobScheduler");
        redraw();
    }

    private void stopPolling() {
        scheduler().cancel(JOB_ID);
        Probe.record(this, "surveillance périodique désactivée");
        redraw();
    }

    private void redraw() {
        if (output == null) return;
        boolean active = scheduler().getPendingJob(JOB_ID) != null;
        output.setText("Vérification ~15 min : " + (active ? "programmée (horaire non garanti)" : "désactivée")
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
        instructions.setText("Test indépendant : aucune commande Hue ni transmission réseau. "
                + "La diffusion dynamique ne fonctionne que pendant l'ouverture. "
                + "L'événement statique et la vérification périodique sont à observer après un swipe. "
                + "Android peut retarder les tâches. Ne force pas l'arrêt pour le test normal.");
        instructions.setTextSize(15f);
        panel.addView(instructions);
        button(panel, "Lire le prochain réveil", v -> {
            Probe.record(this, "bouton manuel");
            redraw();
        });
        button(panel, "Activer une vérification ~15 min", v -> startPolling());
        button(panel, "Arrêter les vérifications", v -> stopPolling());
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
