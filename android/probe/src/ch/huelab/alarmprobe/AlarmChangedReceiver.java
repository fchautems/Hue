package ch.huelab.alarmprobe;

import android.app.AlarmManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class AlarmChangedReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (AlarmManager.ACTION_NEXT_ALARM_CLOCK_CHANGED.equals(intent.getAction())) {
            Probe.record(context, "diffusion statique (manifest)");
        }
    }
}
