package android.app;
public class AlarmManager {
    public int reads;
    public AlarmClockInfo alarm = new AlarmClockInfo(System.currentTimeMillis() + 3600000);
    public AlarmClockInfo getNextAlarmClock() { reads++; return alarm; }
    public static class AlarmClockInfo {
        private final long time;
        public AlarmClockInfo(long time) { this.time = time; }
        public long getTriggerTime() { return time; }
    }
}
