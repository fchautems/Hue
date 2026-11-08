package ch.huelab.mobile;

import android.app.job.JobParameters;
import android.app.job.JobService;
import java.util.concurrent.Future;

public final class AlarmSyncJob extends JobService {
    private Future<?> task;

    @Override public boolean onStartJob(JobParameters parameters) {
        task = AlarmSync.request(this, succeeded -> jobFinished(parameters, false));
        return true;
    }

    @Override public boolean onStopJob(JobParameters parameters) {
        if (task != null) task.cancel(true);
        return true;
    }
}
