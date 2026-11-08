package ch.huelab.alarmprobe;

import android.app.AlarmManager;
import android.content.Context;
import android.content.SharedPreferences;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

final class Probe {
    private static final String FILE = "observations";
    private Probe() {}

    private static String stamp(long ms) {
        return new SimpleDateFormat("EEE dd.MM.yyyy HH:mm:ss z", Locale.FRANCE).format(new Date(ms));
    }

    static synchronized void record(Context context, String source) {
        long now = System.currentTimeMillis();
        String alarm;
        try {
            AlarmManager manager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
            AlarmManager.AlarmClockInfo next = manager == null ? null : manager.getNextAlarmClock();
            alarm = next == null ? "Aucun réveil annoncé par Android" : stamp(next.getTriggerTime());
        } catch (Exception ex) {
            alarm = "Erreur lecture: " + ex.getClass().getSimpleName();
        }
        SharedPreferences prefs = context.getSharedPreferences(FILE, Context.MODE_PRIVATE);
        String previous = prefs.getString("alarm", "jamais lu");
        String delta = previous.equals(alarm) ? "identique" : "CHANGEMENT";
        String line = stamp(now) + " | " + source + " | " + delta + " | " + alarm;
        String prior = prefs.getString("log", "");
        String joined = line + "\n" + prior;
        if (joined.length() > 16000) joined = joined.substring(0, 16000);
        prefs.edit().putString("alarm", alarm).putLong("last", now)
                .putString("source", source).putString("log", joined).commit();
    }

    static String report(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(FILE, Context.MODE_PRIVATE);
        long ms = prefs.getLong("last", 0);
        String seen = ms == 0 ? "jamais" : stamp(ms);
        return "Dernière lecture : " + seen + "\n"
                + "Source : " + prefs.getString("source", "aucune") + "\n"
                + "Prochain réveil : " + prefs.getString("alarm", "inconnu")
                + "\n\nObservations (plus récentes d'abord) :\n"
                + prefs.getString("log", "(aucune)");
    }

    static void clear(Context context) {
        context.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit().clear().commit();
    }
}
