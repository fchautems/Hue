package android.content;
import android.app.AlarmManager;
import java.util.concurrent.ConcurrentHashMap;
public class Context {
    public static final int MODE_PRIVATE = 0;
    public final AlarmManager alarms = new AlarmManager();
    private final ConcurrentHashMap<String, String> values = new ConcurrentHashMap<>();
    public Context getApplicationContext() { return this; }
    public <T> T getSystemService(Class<T> type) { return type.cast(alarms); }
    public SharedPreferences getSharedPreferences(String name, int mode) {
        return new SharedPreferences() {
            public String getString(String key, String fallback) { return values.getOrDefault(key, fallback); }
            public Editor edit() { return new Editor() {
                public Editor putString(String key, String value) { values.put(key, value); return this; }
                public void apply() {}
            }; }
        };
    }
}
