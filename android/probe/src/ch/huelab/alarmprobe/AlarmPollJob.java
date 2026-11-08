package ch.huelab.alarmprobe;

import android.app.job.JobParameters;
import android.app.job.JobService;

public final class AlarmPollJob extends JobService {
    @Override public boolean onStartJob(JobParameters params) {
        Probe.record(this, "vérification périodique (JobScheduler)");
        return false;
    }
    @Override public boolean onStopJob(JobParameters params) { return false; }
}
