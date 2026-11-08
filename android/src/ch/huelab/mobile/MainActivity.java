package ch.huelab.mobile;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.AlarmManager;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.Uri;
import android.os.Bundle;
import android.text.InputType;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import java.io.ByteArrayInputStream;

public final class MainActivity extends Activity {
    static final String DEFAULT_SERVER = "http://10.0.0.12:8765";
    private static final String SERVER_KEY = "server";
    private WebView web;
    private LinearLayout offline;
    private TextView offlineMessage;
    private volatile String server;
    private final AlarmChangedReceiver alarmReceiver = new AlarmChangedReceiver();

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        server = AlarmSync.preferences(this).getString(SERVER_KEY, DEFAULT_SERVER);
        FrameLayout root = new FrameLayout(this);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                    insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets.consumeSystemWindowInsets();
        });
        root.setBackgroundColor(0xff142337);
        web = new WebView(this);
        web.setBackgroundColor(0xff142337);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setUserAgentString(web.getSettings().getUserAgentString() + " HueLabAndroid/0.2");
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new LocalPageClient());
        web.setDownloadListener((url, agent, disposition, type, length) ->
                new AlertDialog.Builder(this).setMessage("Ouvre Hue Lab dans ton navigateur pour exporter ce fichier.")
                        .setPositiveButton("Ouvrir le navigateur", (dialog, which) -> openBrowser(Uri.parse(server)))
                        .setNegativeButton("Annuler", null).show());
        root.addView(web, new FrameLayout.LayoutParams(-1, -1));

        offline = new LinearLayout(this);
        offline.setOrientation(LinearLayout.VERTICAL);
        int padding = Math.round(24 * getResources().getDisplayMetrics().density);
        offline.setPadding(padding, padding, padding, padding);
        offline.setGravity(android.view.Gravity.CENTER_VERTICAL);
        offlineMessage = new TextView(this);
        offlineMessage.setTextSize(18);
        offline.addView(offlineMessage);
        Button retry = new Button(this);
        retry.setText("Réessayer");
        retry.setOnClickListener(view -> loadServer());
        offline.addView(retry);
        Button change = new Button(this);
        change.setText("Changer l’adresse");
        change.setOnClickListener(view -> editAddress());
        offline.addView(change);
        root.addView(offline, new FrameLayout.LayoutParams(-1, -1));
        setContentView(root);
        IntentFilter alarms = new IntentFilter(AlarmManager.ACTION_NEXT_ALARM_CLOCK_CHANGED);
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            registerReceiver(alarmReceiver, alarms, RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(alarmReceiver, alarms);
        }
        loadServer();
    }

    @Override
    protected void onResume() {
        super.onResume();
        syncAlarm(false);
    }

    private void syncAlarm(boolean feedback) {
        AlarmSync.request(this, succeeded -> {
            if (feedback) runOnUiThread(() -> {
                if (!isDestroyed()) {
                    web.evaluateJavascript("window.HueDawn?.checkSync(" + succeeded + ")", null);
                }
            });
        });
    }

    private void loadServer() {
        offline.setVisibility(View.GONE);
        web.setVisibility(View.VISIBLE);
        web.loadUrl(server + "/");
    }

    private void showOffline() {
        offlineMessage.setText("Serveur Hue Lab inaccessible à " + server
                + ". Vérifie le Wi-Fi et l’adresse du serveur.");
        web.setVisibility(View.GONE);
        offline.setVisibility(View.VISIBLE);
    }

    private boolean sameServer(Uri url) {
        Uri origin = Uri.parse(server);
        int port = url.getPort() == -1 ? 80 : url.getPort();
        return "http".equals(url.getScheme()) && url.getUserInfo() == null
                && origin.getHost().equals(url.getHost()) && origin.getPort() == port;
    }

    private void openBrowser(Uri url) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, url));
        } catch (ActivityNotFoundException error) {
            Toast.makeText(this, "Aucun navigateur disponible.", Toast.LENGTH_SHORT).show();
        }
    }

    private final class LocalPageClient extends WebViewClient {
        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            Uri url = request.getUrl();
            if (request.isForMainFrame() && "huelab://sync-alarm".equals(url.toString())
                    && view.getUrl() != null && sameServer(Uri.parse(view.getUrl()))) {
                syncAlarm(true);
                return true;
            }
            if (sameServer(url)) return false;
            if (request.isForMainFrame() && request.hasGesture() && "https".equals(url.getScheme())) {
                openBrowser(url);
            }
            return true;
        }

        @Override
        public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            if (sameServer(request.getUrl())) return null;
            return new WebResourceResponse("text/plain", "UTF-8", 403, "Forbidden",
                    java.util.Collections.emptyMap(), new ByteArrayInputStream(new byte[0]));
        }

        @Override
        public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
            if (request.isForMainFrame() && sameServer(request.getUrl())) showOffline();
        }

        @Override
        public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse error) {
            if (request.isForMainFrame() && sameServer(request.getUrl())) showOffline();
        }
    }

    private void editAddress() {
        EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setSingleLine();
        input.setText(server.substring("http://".length()));
        input.setSelectAllOnFocus(true);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Adresse du serveur Hue Lab")
                .setMessage("Indique l’adresse IP locale du Raspberry et son port.")
                .setView(input).setNegativeButton("Annuler", null)
                .setPositiveButton("Connecter", null).create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(view -> {
            String address = LocalServer.normalize(input.getText().toString());
            if (address == null) {
                input.setError("Exemple : 10.0.0.12:8765");
                return;
            }
            web.stopLoading();
            web.clearHistory();
            server = address;
            AlarmSync.preferences(this).edit().putString(SERVER_KEY, server).apply();
            dialog.dismiss();
            loadServer();
            syncAlarm(false);
        }));
        dialog.show();
    }

    @Override
    public void onBackPressed() {
        new AlertDialog.Builder(this).setTitle("Hue Lab")
                .setItems(new String[]{"Changer l’adresse du serveur", "Fermer l’application"}, (dialog, index) -> {
                    if (index == 0) editAddress();
                    else finish();
                }).setNegativeButton("Rester", null).show();
    }

    @Override
    protected void onDestroy() {
        unregisterReceiver(alarmReceiver);
        web.destroy();
        super.onDestroy();
    }
}
