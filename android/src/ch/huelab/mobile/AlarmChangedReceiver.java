package ch.huelab.mobile;

import android.app.AlarmManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public final class AlarmChangedReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context context, Intent intent) {
        if (!AlarmManager.ACTION_NEXT_ALARM_CLOCK_CHANGED.equals(intent.getAction())
                || !AlarmSync.enabled(context)) return;
        PendingResult pending = goAsync();
        AlarmSync.request(context, succeeded -> pending.finish());
    }
}
